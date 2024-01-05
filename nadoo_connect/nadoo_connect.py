import os
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
import logging
import asyncio
import aiofiles
import multiprocessing
from multiprocessing import Process, Queue
import aiofiles.os as async_os  # Correct import statement for async_os
import traceback

from nadoo_connect.email import send_email

# Configure logging to display level, process ID, and message
logging.basicConfig(
    level=logging.DEBUG,
    filename="nadoo_connect.log",  # Specify the filename here
    filemode="a",  # 'a' means append (add logs to the end of the file)
    format="%(asctime)s - %(process)d - %(levelname)s - %(message)s",  # Include timestamp, process ID, log level, and message
)

# Assuming that the logger has been configured globally
logger = logging.getLogger(__name__)

# Updated directory names
staged_dir = "rpc_staged"
awaiting_response_dir = "rpc_awaiting_response"
done_dir = "rpc_done"
executions_dir = "executions"
lockfile_path = os.path.join(executions_dir, "sender.lock")
idle_time = 120  # Idle time in seconds before shutting down the sender loop
max_wait_time = 120  # Maximum wait time in seconds between retries
email_size_limit = 72 * 1024  # Email size limit in bytes (72 KB)
sender_process = None  # To keep track of the sender process


async def print_all_stack_traces():
    for task in asyncio.all_tasks():
        task.print_stack()


# Call this function at points where you want to inspect the state of all tasks


# Remaining functions (load_or_request_config and get_config_from_env_or_prompt) will stay the same
async def load_or_request_config():
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


async def setup_directories_async():
    # Create directories if they do not exist
    for directory in [staged_dir, awaiting_response_dir, done_dir, executions_dir]:
        if not await async_os.path.exists(directory):
            await async_os.makedirs(directory)

    # Create the lock file if it does not exist
    if not await async_os.path.exists(lockfile_path):
        async with aiofiles.open(lockfile_path, "a"):
            pass  # Just opening and closing to create the file if it doesn't exist


def inject_config(async_func):
    async def wrapper(*args, **kwargs):
        if "config" not in kwargs or kwargs["config"] is None:
            kwargs["config"] = await load_or_request_config()
        return await async_func(*args, **kwargs)

    return wrapper


@inject_config
async def create_execution(customer_program_uuid, config=None):
    await setup_directories_async()
    execution_data = get_execution_data(customer_program_uuid)
    await save_execution_data_async(execution_data)
    start_sender_loop_if_not_running(config)


async def save_execution_data_async(execution_data):
    file_path = os.path.join(executions_dir, f"{execution_data['execution_uuid']}.json")
    try:
        async with aiofiles.open(file_path, "w") as file:
            await file.write(json.dumps(execution_data))
    except Exception as e:
        print(f"Error saving execution data: {e}")


async def get_xyz_for_xyz_remote(uuid, data, config):
    """
    Sends a request for a remote procedure call and handles the response.

    :param uuid: The unique identifier for the remote procedure.
    :param data: The data to be sent to the remote procedure.
    :param config: Configuration data containing SMTP details and other necessary information.
    :return: The result from the remote procedure call.
    """
    # Serialize the data along with the UUID to JSON
    request_body = json.dumps({"uuid": uuid, "data": data})

    # Extract SMTP configuration from the config dictionary
    smtp_server = config["SMTP_SERVER"]
    smtp_port = config["SMTP_PORT"]
    email = config["EMAIL"]
    password = config["PASSWORD"]
    to_email = config["DESTINATION_EMAIL"]

    # Send the request via email
    email_sent = await send_email(
        subject="RPC Request",
        message=request_body,
        to_email=to_email,
        smtp_server=smtp_server,
        smtp_port=smtp_port,
        email=email,
        password=password,
    )

    if not email_sent:
        return None  # or handle the failure as appropriate

    # TODO: Implement the logic to wait and retrieve the response
    # This depends on how your system handles receiving responses
    # It might involve checking an inbox, a database, etc.

    # For demonstration, here's a placeholder for the response
    response = None  # Replace with actual response retrieval logic

    return response


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


def start_sender_loop_if_not_running(config):
    global sender_process
    try:
        logger.debug("Attempting to acquire lock before starting process...")
        with portalocker.Lock(lockfile_path, mode="w", timeout=5):  # Increased timeout
            if sender_process is not None and sender_process.is_alive():
                logger.warning("A sender loop process is already running.")
                return
            logger.debug("Lock acquired. Starting sender loop process.")
            sender_process = Process(target=run_sender_loop_process, args=(config,))
            sender_process.start()
    except portalocker.exceptions.LockException:
        logger.warning("Unable to acquire lock, another process may be running.")


async def process_rpc_requests(config):
    batch_size_limit = 5  # Maximum number of requests to batch
    max_wait_time = 5  # Maximum time to wait in seconds
    min_wait_time = 1  # Minimum time to wait for additional requests
    last_rpc_time = time.time()

    batched_rpc_data = []
    while True:
        current_time = time.time()
        rpc_files = [f for f in os.listdir(staged_dir) if f.endswith(".json")]

        if not rpc_files:
            break

        for filename in rpc_files:
            filepath = os.path.join(staged_dir, filename)
            with open(filepath, "r") as file:
                rpc_data = json.load(file)
                batched_rpc_data.append(rpc_data)
                print(f"Added {filename} to batch.")

            if len(batched_rpc_data) >= batch_size_limit:
                print("Batch size limit reached.")
                break

        # Check if it's time to process the batch
        if len(batched_rpc_data) > 0 and (
            current_time - last_rpc_time >= max_wait_time
        ):
            print("Max wait time reached, processing batch.")
            break
        elif current_time - last_rpc_time >= min_wait_time and not rpc_files:
            print("Min wait time reached with no new RPCs, processing batch.")
            break

        await asyncio.sleep(0.1)

    # Process the batched RPC requests
    if batched_rpc_data:
        email_content = json.dumps(batched_rpc_data)
        email_sent = await send_email(
            "Batched RPC Requests",
            email_content,
            config["DESTINATION_EMAIL"],
            config["SMTP_SERVER"],
            int(config["SMTP_PORT"]),
            config["EMAIL"],
            config["PASSWORD"],
        )

        if email_sent:
            # Move processed files to awaiting_response
            for data in batched_rpc_data:
                source_path = os.path.join(staged_dir, f"{data['uuid']}.json")
                destination_path = os.path.join(
                    awaiting_response_dir, f"{data['uuid']}.json"
                )
                os.rename(source_path, destination_path)

    return len(batched_rpc_data) > 0  # Return True if any requests were processed


async def process_execution_requests(execution_files, config):
    batch_size_limit = 200  # Define a suitable batch size limit
    batched_execution_data = []

    for filename in execution_files[:batch_size_limit]:
        filepath = os.path.join(executions_dir, filename)
        with open(filepath, "r") as file:
            execution_data = json.load(file)
            batched_execution_data.append(execution_data)

        if len(batched_execution_data) >= batch_size_limit:
            break

    logger.debug("Processing batched execution requests")
    if batched_execution_data:
        email_content = json.dumps(batched_execution_data)
        email_sent = await send_email(
            "Batched Executions",
            email_content,
            config["DESTINATION_EMAIL"],
            config["SMTP_SERVER"],
            int(config["SMTP_PORT"]),
            config["EMAIL"],
            config["PASSWORD"],
        )

        logger.info(f"Email sent: {email_sent}")
        if email_sent:
            for data in batched_execution_data:
                os.remove(
                    os.path.join(executions_dir, f"{data['execution_uuid']}.json")
                )
                record_execution_in_db(
                    data["execution_uuid"], data["customer_program_uuid"], True
                )

    return len(batched_execution_data) > 0


def run_sender_loop_process(config):
    try:
        logger.debug("Process started, reacquiring lock...")
        with portalocker.Lock(lockfile_path, mode="w", timeout=5):  # Consistent timeout
            logger.debug("Lock reacquired by process. Running sender loop.")
            asyncio.run(sender_loop(config))
    except portalocker.exceptions.LockException:
        logger.warning("Unable to reacquire lock in process, exiting.")
    finally:
        logger.debug("Sender loop process ending, releasing lock.")


async def sender_loop(config):
    wait_time = 10  # Shorter wait time for quicker checks
    idle_timeout = 120  # Timeout duration in seconds
    last_activity_time = time.time()

    logger.info("Sender loop started.")

    while True:
        try:
            current_time = time.time()

            # Check if the idle timeout has been exceeded
            if current_time - last_activity_time > idle_timeout:
                logger.info("Idle timeout exceeded, stopping sender loop.")
                break

            rpc_requests_processed = await process_rpc_requests(config)
            execution_files_processed = False

            if not rpc_requests_processed:
                execution_files = [
                    f for f in os.listdir(executions_dir) if f.endswith(".json")
                ]
                if execution_files:
                    logger.debug("Processing execution requests.")
                    await process_execution_requests(execution_files, config)
                    execution_files_processed = True

            # Update last_activity_time if there was activity
            if rpc_requests_processed or execution_files_processed:
                last_activity_time = time.time()

            await asyncio.sleep(wait_time)

        except asyncio.CancelledError:
            logger.info("Sender loop cancelled, stopping.")
            break
        except Exception as e:
            logger.error(f"Error in sender loop: {e}\n{traceback.format_exc()}")

    logger.info("Sender loop stopped.")


def calculate_size(data):
    return len(json.dumps(data))  # Returns the size of the data in bytes


async def main():
    customer_program_uuid = "specific-uuid-from-database"
    for i in range(1000):
        await create_execution(customer_program_uuid)


if __name__ == "__main__":
    asyncio.run(main(), debug=True)
