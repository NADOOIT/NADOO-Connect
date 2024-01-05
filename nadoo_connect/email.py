import json
import os
import aiosmtplib
from email.mime.text import MIMEText
import logging
import traceback
import sys
from typing import Optional
import re
import aiosqlite
import tkinter as tk
from tkinter import simpledialog

# Setup a dedicated error logger
error_logger = logging.getLogger("error_logger")
error_logger.setLevel(logging.ERROR)
error_handler = logging.FileHandler("error_logs.log")
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


# Async function to setup database
@log_errors
async def setup_database():
    async with aiosqlite.connect("email_credentials.db") as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS email_accounts (
                email TEXT PRIMARY KEY,
                smtp_server TEXT,
                smtp_port INTEGER,
                password TEXT,
                is_default BOOLEAN DEFAULT 0
            );
            """
        )
        await conn.commit()


def get_email_credentials_db_name() -> str:
    return "email_credentials.db"


def email_credentials_db_name(func):
    async def wrapper(*args, **kwargs):
        if "email_credentials_db_name" not in kwargs:
            kwargs["email_credentials_db_name"] = get_email_credentials_db_name()
        return await func(*args, **kwargs)

    return wrapper


# Async function to set default email address
@log_errors
@email_credentials_db_name
async def set_default_email_address(email_address: str, email_credentials_db_name: str):
    async with aiosqlite.connect(email_credentials_db_name) as conn:
        await conn.execute("UPDATE email_accounts SET is_default = 0")
        await conn.execute(
            "UPDATE email_accounts SET is_default = 1 WHERE email = ?", (email_address,)
        )
        await conn.commit()


# Async function to get default email account
@log_errors
@email_credentials_db_name
async def get_default_email_account(email_credentials_db_name: str):
    async with aiosqlite.connect(email_credentials_db_name) as conn:
        cursor = await conn.execute("SELECT * FROM email_accounts WHERE is_default = 1")
        result = await cursor.fetchone()
        await cursor.close()
        return result


# Async function to get email account for email address
@log_errors
@email_credentials_db_name
async def get_email_account_for_email_address(
    email_credentials_db_name: str, email_address: Optional[str] = None
):
    async with aiosqlite.connect(email_credentials_db_name) as conn:
        if email_address:
            async with conn.execute(
                "SELECT * FROM email_accounts WHERE email = ?", (email_address,)
            ) as cursor:
                return await cursor.fetchone()
        else:
            return await get_default_email_account(email_credentials_db_name)


# Async function to get email account details
@log_errors
@email_credentials_db_name
async def get_email_account_details(
    email_credentials_db_name: str, email_address: Optional[str] = None
):
    async with aiosqlite.connect(email_credentials_db_name) as conn:
        async with conn.execute(
            "SELECT * FROM email_accounts WHERE email = ?", (email_address,)
        ) as cursor:
            return await cursor.fetchone()


# Async function to save or update email account details in the database
@log_errors
@email_credentials_db_name
async def set_email_account_details_for_email_address(
    email_credentials_db_name: str,
    email_account_details,
    email_address: Optional[str] = None,
):
    async with aiosqlite.connect(email_credentials_db_name) as conn:
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
                SET details = ?
                WHERE email = ?
                """,
                (json.dumps(email_account_details), email_address),
            )
        else:
            # Insert new record
            await conn.execute(
                "INSERT INTO email_accounts (email, details) VALUES (?, ?)",
                (email_address, json.dumps(email_account_details)),
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


# Function to request email account details from user (Sync due to GUI operation)
async def get_email_account_details_from_user(email_address):
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    email_account_details = {}

    # TODO #5 pull all already exisiting info for the given email_address

    email_account_details["smtp_server"] = simpledialog.askstring(
        "SMTP Server", "Enter SMTP server:"
    )
    email_account_details["smtp_port"] = simpledialog.askstring(
        "SMTP Port", "Enter SMTP port:"
    )
    email_account_details["password"] = simpledialog.askstring(
        "Password", "Enter email password:", show="*"
    )
    save_email_account_details = simpledialog.askyesno(
        "Save Details", "Do you want to save these details?"
    )

    root.destroy()

    if save_email_account_details:
        await set_email_account_details_for_email_address(
            email_address, email_account_details
        )

    return email_account_details


# Async function to get emails for an email address
@log_errors
@email_credentials_db_name
async def get_emails_for_email_address(email_address, email_credentials_db_name: str):
    if not is_valid_email(email_address):
        logging.error(f"Invalid email address: {email_address}")
        return []

    email_account_details = await get_email_account_details(
        email_credentials_db_name=email_credentials_db_name, email_address=email_address
    )
    if not email_account_details:
        email_account_details = await get_email_account_details_from_user(email_address)

    # Placeholder for the function to retrieve emails
    return []  # Replace with actual email retrieval result
