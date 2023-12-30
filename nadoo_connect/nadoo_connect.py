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
email_size_limit = 72 * 1024  # Email size limit in bytes (72 KB)


def setup_directories():
    if not os.path.exists(executions_dir):
        os.makedirs(executions_dir)


def load_or_request_config():
    load_dotenv()
    config = get_config_from_env_or_prompt()
    save_missing_config_to_env(config)
    return config


def get_config_from_env_or_prompt():
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
        config.update(request_missing_config(missing_configs))
    return config


def request_missing_config(missing_configs):
    root = Tk()
    root.withdraw()
    config_updates = {}
    for var in missing_configs:
        config_updates[var] = simpledialog.askstring(
            "Configuration", f"Enter your {var.lower()}:"
        )
    root.destroy()
    return config_updates


def save_missing_config_to_env(config):
    with open(".env", "a") as env_file:
        for var, value in config.items():
            if value is not None:
                env_file.write(f"{var}={value}\n")


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
    execution_data = get_execution_data(customer_program_uuid)
    save_execution_data(execution_data)

    start_sender_loop_if_not_running()


def get_execution_data(customer_program_uuid):
    execution_uuid = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    return {
        "execution_uuid": execution_uuid,
        "customer_program_uuid": customer_program_uuid,
        "timestamp": timestamp,
    }


def save_execution_data(execution_data):
    filepath = os.path.join(executions_dir, f"{execution_data['execution_uuid']}.json")
    with open(filepath, "w") as file:
        json.dump(execution_data, file)


def start_sender_loop_if_not_running():
    global sender_task
    if sender_task is None or sender_task.done():
        try:
            with portalocker.Lock(lockfile_path, mode="w", timeout=1):
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    # Create a new event loop if there isn't a running one
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                if loop.is_running():
                    sender_task = loop.create_task(sender_loop())
                else:
                    sender_task = loop.create_task(sender_loop())
                    loop.run_until_complete(sender_task)
        except portalocker.exceptions.LockException:
            pass  # Another process is already running the sender loop


async def sender_loop():
    wait_time = 10
    last_execution_time = time.time()
    while True:
        try:
            execution_files = [
                f for f in os.listdir(executions_dir) if f.endswith(".json")
            ]
            if not execution_files:
                if time.time() - last_execution_time > idle_time:
                    break
                await asyncio.sleep(wait_time)
                continue

            batched_execution_data = []
            for filename in execution_files:
                filepath = os.path.join(executions_dir, filename)
                with open(filepath, "r") as file:
                    execution_data = json.load(file)
                    batched_execution_data.append(execution_data)

                # Check if the combined size of the batched data is approaching the email size limit
                # (You will need to define 'email_size_limit')
                if calculate_size(batched_execution_data) > email_size_limit:
                    break

            email_content = json.dumps(batched_execution_data)
            email_sent = await send_async_email(
                "Batched Executions",
                email_content,
                config["DESTINATION_EMAIL"],
                config["SMTP_SERVER"],
                int(config["SMTP_PORT"]),
                config["EMAIL"],
                config["PASSWORD"],
            )

            if email_sent:
                for data in batched_execution_data:
                    os.remove(
                        os.path.join(executions_dir, f"{data['execution_uuid']}.json")
                    )
                    record_execution_in_db(
                        data["execution_uuid"],
                        data["customer_program_uuid"],
                        True,
                    )
                last_execution_time = time.time()
                wait_time = 10
            else:
                wait_time = min(wait_time * 2, max_wait_time)

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error in sender loop: {e}")


def calculate_size(data):
    return len(json.dumps(data))  # Returns the size of the data in bytes


def main():
    global config
    config = load_or_request_config()
    customer_program_uuid = "specific-uuid-from-database"
    for i in range(100):
        create_execution(customer_program_uuid)


if __name__ == "__main__":
    main()
