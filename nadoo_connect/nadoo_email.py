import os
import aiosmtplib
from email.mime.text import MIMEText
import logging
import traceback

from typing import Optional
import re
import aiosqlite
import tkinter as tk
from tkinter import simpledialog

# Create 'logs' directory if it doesn't exist
logs_dir = "logs"
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# Setup a dedicated error logger
error_logger = logging.getLogger("error_logger")
error_logger.setLevel(logging.ERROR)
error_handler = logging.FileHandler(os.path.join(logs_dir, "error_logs.log"))
error_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
error_logger.addHandler(error_handler)


# Decorator for enhanced error logging
def log_errors(func):
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            log_exception(func, args, kwargs, e)
            raise

    return async_wrapper


def log_exception(func, args, kwargs, e):
    arg_values = ", ".join(
        [repr(a) for a in args] + [f"{k}={v!r}" for k, v in kwargs.items()]
    )
    env_vars = {k: v for k, v in os.environ.items()}
    error_logger.error(
        f"Exception in {func.__name__} with args [{arg_values}] and env vars [{env_vars}]: {e}\n{traceback.format_exc()}"
    )


def get_execution_email_address():
    # Hardcoded email address
    return "executions@nadooit.de"


def get_rpc_email_address():
    # Hardcoded email address
    return "rpc@nadooit.de"


def get_email_account_db_name() -> str:
    return "email_account.db"


def email_account_db_name(func):
    async def wrapper(*args, **kwargs):
        if "email_account_db_name" not in kwargs:
            kwargs["email_account_db_name"] = get_email_account_db_name()
        return await func(*args, **kwargs)

    return wrapper


# Async function to setup database
@log_errors
@email_account_db_name
async def setup_database(email_account_db_name: str):
    async with aiosqlite.connect(email_account_db_name) as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS email_accounts (
                email TEXT PRIMARY KEY,
                pop_server TEXT,    # POP3 server address
                pop_port INTEGER,   # POP3 server port, typically 995 for SSL/TLS
                smtp_server TEXT,   # SMTP server address for sending emails
                smtp_port INTEGER,  # SMTP server port, typically 465 for SSL/TLS
                password TEXT,      # Password for the email account
                is_default BOOLEAN DEFAULT 0
            );
            """
        )
        await conn.commit()

# Helper function to get the email address from email account details
def get_email_address_from_email_account(email_account):
    return email_account.get("email")

# Helper function to get POP3 server from email account details
def get_pop_server_from_email_account(email_account):
    return email_account.get("pop_server")

# Helper function to get POP3 port from email account details
def get_pop_port_from_email_account(email_account):
    return email_account.get("pop_port")

# Helper function to get SMTP server from email account details
def get_smtp_server_from_email_account(email_account):
    return email_account.get("smtp_server")

# Helper function to get SMTP port from email account details
def get_smtp_port_from_email_account(email_account):
    return email_account.get("smtp_port")

# Helper function to get the password from email account details
def get_email_address_password_from_email_account(email_account):
    return email_account.get("password")


# Helper function to check if POP3 server is present in email account details
def check_pop_server_in_email_account(email_account):
    return get_pop_server_from_email_account(email_account) is not None


# Helper function to check if POP3 port is present in email account details
def check_pop_port_in_email_account(email_account):
    return get_pop_port_from_email_account(email_account) is not None


# Helper function to check if SMTP server is present in email account details
def check_smtp_server_in_email_account(email_account):
    return get_smtp_server_from_email_account(email_account) is not None


# Helper function to check if SMTP port is present in email account details
def check_smtp_port_in_email_account(email_account):
    return get_smtp_port_from_email_account(email_account) is not None


# Helper function to check if the password is present in email account details
def check_password_in_email_account(email_account):
    return get_email_address_password_from_email_account(email_account) is not None


# Async function to set default email address
@log_errors
@email_account_db_name
async def set_default_email_address(email_address: str, email_account_db_name: str):
    async with aiosqlite.connect(email_account_db_name) as conn:
        await conn.execute("UPDATE email_accounts SET is_default = 0")
        await conn.execute(
            "UPDATE email_accounts SET is_default = 1 WHERE email = ?", (email_address,)
        )
        await conn.commit()

@log_errors
@email_account_db_name
async def get_default_email_account(email_account_db_name: str):
    async with aiosqlite.connect(email_account_db_name) as conn:
        cursor = await conn.execute("SELECT * FROM email_accounts WHERE is_default = 1")
        result = await cursor.fetchone()
        await cursor.close()

        if result:
            keys = ["email", "pop_server", "pop_port", "smtp_server", "smtp_port", "password", "is_default"]
            return dict(zip(keys, result))
        
        email_account = await get_email_account_from_user({})
        if email_account:
            await save_email_account(email_account_db_name, email_account)
            email_account["is_default"] = 1  # Set as default
            return email_account
        return None




@log_errors
@email_account_db_name
async def get_email_account_for_email_address(email_account_db_name: str, email_address: Optional[str] = None):
    async with aiosqlite.connect(email_account_db_name) as conn:
        cursor = await conn.execute("SELECT * FROM email_accounts WHERE email = ?", (email_address,))
        result = await cursor.fetchone()
        await cursor.close()
        
        if result:
            keys = ["email", "pop_server", "pop_port", "smtp_server", "smtp_port", "password", "is_default"]
            return dict(zip(keys, result))
        return None



# Async function to save or update email account details in the database
@log_errors
@email_account_db_name
async def save_email_account(email_account_db_name: str, email_account):
    # Extract details using helper functions
    email_address = get_email_address_from_email_account(email_account)
    pop_server = get_pop_server_from_email_account(email_account)
    pop_port = get_pop_port_from_email_account(email_account)
    smtp_server = get_smtp_server_from_email_account(email_account)
    smtp_port = get_smtp_port_from_email_account(email_account)
    password = get_email_address_password_from_email_account(email_account)

    async with aiosqlite.connect(email_account_db_name) as conn:
        # Check if a record with the given email already exists
        async with conn.execute(
            "SELECT email FROM email_accounts WHERE email = ?", (email_address,)
        ) as cursor:
            existing_email = await cursor.fetchone()

        # If the email exists, update the record
        if existing_email:
            await conn.execute(
                """
                UPDATE email_accounts
                SET pop_server = ?, pop_port = ?, smtp_server = ?, smtp_port = ?, password = ?
                WHERE email = ?
                """,
                (pop_server, pop_port, smtp_server, smtp_port, password, email_address),
            )
        else:
            # Insert new record
            await conn.execute(
                """
                INSERT INTO email_accounts (email, pop_server, pop_port, smtp_server, smtp_port, password)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (email_address, pop_server, pop_port, smtp_server, smtp_port, password),
            )

        await conn.commit()


# Async function to send email
@log_errors
async def send_email(
    subject, message, to_email, smtp_server, smtp_port, email, password
) -> bool:
    try:
        msg = MIMEText(message, _subtype="plain", _charset="utf-8")
        msg["Subject"] = subject
        msg["From"] = email
        msg["To"] = to_email

        async with aiosmtplib.SMTP(
            hostname=smtp_server, port=smtp_port, use_tls=True
        ) as smtp:
            await smtp.login(email, password)
            await smtp.send_message(msg)

        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


# Function to validate email address format
def is_valid_email(email):
    pattern = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
    return re.match(pattern, email) is not None

import tkinter as tk
from tkinter import simpledialog, Label, Entry, Button, Checkbutton, IntVar

# Custom dialog class
class EmailAccountDialog(simpledialog.Dialog):
    def body(self, master):
        self.entries = {}

        Label(master, text="POP Server:").grid(row=0)
        self.entries["pop_server"] = Entry(master)
        self.entries["pop_server"].grid(row=0, column=1)

        Label(master, text="POP Port:").grid(row=1)
        self.entries["pop_port"] = Entry(master)
        self.entries["pop_port"].grid(row=1, column=1)

        Label(master, text="SMTP Server:").grid(row=2)
        self.entries["smtp_server"] = Entry(master)
        self.entries["smtp_server"].grid(row=2, column=1)

        Label(master, text="SMTP Port:").grid(row=3)
        self.entries["smtp_port"] = Entry(master)
        self.entries["smtp_port"].grid(row=3, column=1)

        Label(master, text="Password:").grid(row=4)
        self.entries["password"] = Entry(master, show="*")
        self.entries["password"].grid(row=4, column=1)

        Label(master, text="Email:").grid(row=5)
        self.entries["email"] = Entry(master)
        self.entries["email"].grid(row=5, column=1)

        self.save_var = IntVar()
        self.check_save = Checkbutton(master, text="Save Details", variable=self.save_var)
        self.check_save.grid(row=6, columnspan=2)

        return self.entries["pop_server"]  # Initial focus

    def apply(self):
        self.result = {key: entry.get() for key, entry in self.entries.items()}
        self.result["save_details"] = bool(self.save_var.get())

# Function to request email account details from user
async def get_email_account_from_user(email_account):
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    dialog = EmailAccountDialog(root, title="Enter Email Account Details")
    email_account_details = dialog.result
    root.destroy()

    if email_account_details and email_account_details.get("save_details"):
        await save_email_account(email_account_details)

    return email_account_details

# Replace 'save_email_account' with the appropriate function to save the account details


""" 
# Async function to get emails for an email address
@log_errors
@email_account_db_name
async def get_emails_for_email_address(email_address, email_account_db_name: str):
    if not is_valid_email(email_address):
        logging.error(f"Invalid email address: {email_address}")
        return []

    email_account = await get_email_account_for_email_address(
        email_address=email_address
    )

    # If some details are missing, request them from the user
    if not (
        check_pop_server_in_email_account(email_account)
        and check_pop_port_in_email_account(email_account)
        and check_password_in_email_account(email_account)
    ):
        email_account = await get_email_account_from_user(email_account)

    # Retrieve emails using the provided details
    emails = []
    try:
        async with aiopop3.POP3_SSL(
            host=email_account["pop_server"],
            port=email_account["pop_port"],
        ) as client:
            await client.login(email_address, email_account["password"])

            # Fetch emails. Adapt this part based on how the library works
            messages = await client.list_messages()  # This method might vary
            for msg_id in messages:
                email_content = await client.retrieve_message(msg_id)
                emails.append(email_content)

    except Exception as e:
        logging.error(f"Error retrieving emails: {e}")

    return emails
 """