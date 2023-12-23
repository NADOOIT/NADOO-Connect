import os
import asyncio
import json
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import aiosmtplib
from email.mime.text import MIMEText
from tkinter import simpledialog, Tk
import base64
from email.mime.text import MIMEText


def load_or_request_config():
    # Explicitly load .env file
    load_dotenv()

    required_vars = [
        "SMTP_SERVER",
        "SMTP_PORT",
        "EMAIL",
        "PASSWORD",
        "DESTINATION_EMAIL",
        "ENCRYPTION_KEY",
    ]

    # Load current config
    config = {var: os.getenv(var) for var in required_vars}
    print("Current config:", config)  # Debugging output

    # Determine which configurations are missing
    missing_configs = {var for var in required_vars if not config[var]}
    if missing_configs:
        print("Missing configurations:", missing_configs)  # Debugging output
        root = Tk()
        root.withdraw()  # Hide the main window
        for var in missing_configs:
            config[var] = simpledialog.askstring(
                "Configuration", f"Enter your {var.lower()}:"
            )
        root.destroy()

        # Update .env file with missing configurations
        with open(".env", "a") as env_file:
            for var in missing_configs:
                env_file.write(f"{var}={config[var]}\n")
                print(f"Writing to .env: {var}={config[var]}")  # Debugging output
    else:
        print(".env file is complete.")  # Debugging output

    return config


def encrypt_data(data, key):
    fernet = Fernet(key)
    encrypted_data = fernet.encrypt(json.dumps(data).encode())
    return encrypted_data


async def send_async_email(
    subject, message, to_email, smtp_server, smtp_port, email, password
):
    # Encode the message in base64 to convert bytes to a string
    encoded_message = base64.b64encode(message).decode()

    msg = MIMEText(encoded_message, _subtype="plain", _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = email
    msg["To"] = to_email

    async with aiosmtplib.SMTP(
        hostname=smtp_server, port=smtp_port, use_tls=True
    ) as smtp:
        await smtp.login(email, password)
        await smtp.send_message(msg)


def create_execution(execution_id, data, config):
    if not execution_id:
        raise ValueError("Execution ID is required.")

    encrypted_data = encrypt_data(data, config["ENCRYPTION_KEY"])
    asyncio.run(
        send_async_email(
            "Execution Created",
            encrypted_data,
            config["DESTINATION_EMAIL"],
            config["SMTP_SERVER"],
            int(config["SMTP_PORT"]),
            config["EMAIL"],
            config["PASSWORD"],
        )
    )


def main():
    config = load_or_request_config()

    # Example usage with specific data
    execution_id = "specific-uuid-from-database"
    data_to_send = {"example_key": "example_value"}
    create_execution(execution_id, data_to_send, config)


if __name__ == "__main__":
    main()
