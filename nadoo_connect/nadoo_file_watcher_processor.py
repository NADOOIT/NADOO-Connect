import os
import json
import asyncio
import queue

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import time
from datetime import datetime
import logging


from .nadoo_email import send_email
from .nadoo_connect import *

# Define directories
staged_dir = "rpc_staged"
executions_dir = "executions"

# Global thread-safe queues
rpc_file_queue = queue.Queue()
execution_file_queue = queue.Queue()


def setup_logger(name, log_file, level=logging.DEBUG):
    """Function to setup as many loggers as you want"""

    # Create 'logs' directory if it doesn't exist
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    # Full path for log file
    log_file_path = os.path.join(logs_dir, log_file)

    # Create a logger
    handler = logging.FileHandler(log_file_path)
    formatter = logging.Formatter(
        "%(asctime)s - %(process)d - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger


# Set up logger specifically for file_watcher_processor
logger = setup_logger("file_watcher_processor_logger", "file_watcher_processor.log")


class RPCEventHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            rpc_file_queue.put(event.src_path)
            logger.debug(f"RPC file added to queue: {event.src_path}")


class ExecutionEventHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            execution_file_queue.put(event.src_path)
            logger.debug(f"Execution file added to queue: {event.src_path}")


async def process_rpc_files(config):
    while not rpc_file_queue.empty():
        file_path = rpc_file_queue.get()
        # Process the file
        # TODO: Implement the actual file processing logic here


async def process_execution_files(config, batch_size_limit=2000):
    batched_execution_data = []
    file_paths_to_requeue = []

    while (
        len(batched_execution_data) < batch_size_limit
        and not execution_file_queue.empty()
    ):
        file_path = execution_file_queue.get()

        try:
            with open(file_path, "r") as file:
                execution_data = json.load(file)
            batched_execution_data.append(execution_data)
            file_paths_to_requeue.append(file_path)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in file: {file_path}")

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

        if email_sent:
            for data in batched_execution_data:
                file_path = os.path.join(
                    executions_dir, f"{data['execution_uuid']}.json"
                )
                os.remove(file_path)
                record_execution_in_db(
                    data["execution_uuid"], data["customer_program_uuid"], True
                )
            logger.info(
                f"Batched email sent with {len(batched_execution_data)} execution files."
            )
        else:
            # Re-queue the files for future processing
            for file_path in file_paths_to_requeue:
                execution_file_queue.put(file_path)
            logger.warning(
                "Failed to send batched email, re-queued the execution files for later processing."
            )


async def processing_loop(config):
    while True:
        await process_rpc_files(config)
        await process_execution_files(config)
        await asyncio.sleep(1)  # Brief pause to prevent constant looping


def clear_rpc_directory():
    for filename in os.listdir(staged_dir):
        os.remove(os.path.join(staged_dir, filename))


def start_watchers():
    rpc_event_handler = RPCEventHandler()
    execution_event_handler = ExecutionEventHandler()
    observer = Observer()
    observer.schedule(rpc_event_handler, path=staged_dir, recursive=False)
    observer.schedule(execution_event_handler, path=executions_dir, recursive=False)
    observer.start()
    return observer


def queue_existing_execution_files():
    for filename in os.listdir(executions_dir):
        if filename.endswith(".json"):
            file_path = os.path.join(executions_dir, filename)
            execution_file_queue.put(file_path)


async def main():
    clear_rpc_directory()
    queue_existing_execution_files()  # Queue existing execution files
    config = await load_or_request_config()
    observer = start_watchers()
    processing_task = asyncio.create_task(processing_loop(config))

    try:
        await processing_task
    finally:
        observer.stop()
        observer.join()


if __name__ == "__main__":
    asyncio.run(main())
