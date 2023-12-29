import os
import asyncio
import json
import sqlite3
import uuid
import portalocker
import time
from datetime import datetime
from dotenv import load_dotenv
import aiosmtplib
from email.mime.text import MIMEText
from tkinter import simpledialog, Tk

executions_dir = "executions"
lockfile_path = os.path.join(executions_dir, "sender.lock")
config = None
idle_time = 120  # Idle time in seconds before shutting down the sender loop
max_wait_time = 120  # Maximum wait time in seconds between retries
sender_task = None  # Global variable to keep track of the sender task


def setup_directories():
    if not os.path.exists(executions_dir):
        os.makedirs(executions_dir)


def load_or_request_config():
    load_dotenv()
    required_vars = [
        "SMTP_SERVER",
        "SMTP_PORT",
        "EMAIL",
        "PASSWORD",
        "DESTINATION_EMAIL",
    ]
    config = {var: os.getenv(var) for var in required_vars}

    missing_configs = {var for var in required_vars if not config[var]}
    if missing_configs:
        root = Tk()
        root.withdraw()
        for var in missing_configs:
            config[var] = simpledialog.askstring(
                "Configuration", f"Enter your {var.lower()}:"
            )
        root.destroy()

        with open(".env", "a") as env_file:
            for var in missing_configs:
                env_file.write(f"{var}={config[var]}\n")

    return config


async def send_async_email(
    subject, message, to_email, smtp_server, smtp_port, email, password
):
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


def record_execution_in_db(execution_uuid, customer_program_uuid, is_sent):
    conn = sqlite3.connect("executions.db")
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS execution_records 
                      (execution_uuid TEXT, customer_program_uuid TEXT, is_sent BOOLEAN)"""
    )
    cursor.execute(
        "INSERT INTO execution_records VALUES (?, ?, ?)",
        (execution_uuid, customer_program_uuid, is_sent),
    )
    conn.commit()
    conn.close()


def create_execution(customer_program_uuid):
    global config, sender_task
    if config is None:
        config = load_or_request_config()

    setup_directories()
    execution_uuid = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    execution_data = {
        "execution_uuid": execution_uuid,
        "customer_program_uuid": customer_program_uuid,
        "timestamp": timestamp,
    }
    filepath = os.path.join(executions_dir, f"{execution_uuid}.json")
    with open(filepath, "w") as file:
        json.dump(execution_data, file)

    # Manage the sender loop as an asyncio task
    if sender_task is None or sender_task.done():
        try:
            with portalocker.Lock(lockfile_path, mode="w", timeout=1):
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    sender_task = loop.create_task(sender_loop())
                else:
                    asyncio.run(sender_loop())
        except portalocker.exceptions.LockException:
            pass  # Another process is already running the sender loop


async def sender_loop():
    wait_time = 10
    last_execution_time = time.time()
    while True:
        try:
            executions_exist = False
            print(f"Checking for executions. Current wait time: {wait_time} seconds.")
            for filename in os.listdir(executions_dir):
                filepath = os.path.join(executions_dir, filename)
                if filename.endswith(".json"):
                    executions_exist = True
                    print(f"Processing file: {filename}")
                    with open(filepath, "r") as file:
                        execution_data = json.load(file)

                    email_sent = await send_async_email(
                        "Execution Created",
                        json.dumps(execution_data),
                        config["DESTINATION_EMAIL"],
                        config["SMTP_SERVER"],
                        int(config["SMTP_PORT"]),
                        config["EMAIL"],
                        config["PASSWORD"],
                    )
                    if email_sent:
                        os.remove(filepath)
                        record_execution_in_db(
                            execution_data["execution_uuid"],
                            execution_data["customer_program_uuid"],
                            True,
                        )
                        last_execution_time = time.time()
                        wait_time = 10  # Reset wait time after successful send
                        print(f"Email sent, resetting wait time.")
                    else:
                        wait_time = min(
                            wait_time * 2, max_wait_time
                        )  # Exponential backoff
                        print(
                            f"Email sending failed, increasing wait time to {wait_time} seconds."
                        )

            if not executions_exist:
                remaining_idle_time = idle_time - (time.time() - last_execution_time)
                print(
                    f"No executions found. Remaining idle time before shutdown: {remaining_idle_time:.2f} seconds."
                )
                if remaining_idle_time <= 0:
                    print("Idle time exceeded, shutting down sender loop.")
                    break
            else:
                print("Executions exist, resetting idle timer.")
                last_execution_time = time.time()

            await asyncio.sleep(wait_time)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error in sender loop: {e}")


def main():
    global config
    config = load_or_request_config()
    customer_program_uuid = "specific-uuid-from-database"
    for i in range(10):
        create_execution(customer_program_uuid)


if __name__ == "__main__":
    main()
