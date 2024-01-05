import os
import json
import sqlite3
from datetime import datetime
import pytest
from unittest.mock import AsyncMock, patch
from nadoo_connect import *

import os
import shutil
import tempfile


@pytest.mark.asyncio
async def test_setup_directories():
    # Temporary backup directory
    backup_dir = tempfile.mkdtemp()

    # Move contents to backup directory if executions_dir exists
    if os.path.exists(executions_dir):
        for filename in os.listdir(executions_dir):
            shutil.move(os.path.join(executions_dir, filename), backup_dir)

    # Call the function under test
    await setup_directories_async()

    # Assert the directory was created
    assert os.path.exists(executions_dir)

    # Move contents back from the backup directory, checking for conflicts
    for filename in os.listdir(backup_dir):
        file_path = os.path.join(backup_dir, filename)
        dest_path = os.path.join(executions_dir, filename)
        if os.path.exists(dest_path):
            os.remove(dest_path)
        shutil.move(file_path, executions_dir)

    # Remove the backup directory
    os.rmdir(backup_dir)


class MockSMTP:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        pass

    async def login(self, *args, **kwargs):
        pass

    async def send_message(self, *args, **kwargs):
        pass


@pytest.mark.asyncio
async def test_send_email():
    with patch("aiosmtplib.SMTP", new_callable=lambda: MockSMTP) as mock_smtp_class:
        # Execute the function under test
        result = await send_email(
            "subject",
            "message",
            "to@example.com",
            "smtp.example.com",
            587,
            "user@example.com",
            "password",
        )

        # Assertions
        assert result

        # You can add more assertions here to check if the methods of mock_smtp_class were called as expected


def test_record_execution_in_db():
    # Optionally, use an in-memory database for testing
    # conn = sqlite3.connect(":memory:")
    # cursor = conn.cursor()
    # Replace the connection line in the record_execution_in_db function with
    # cursor.execute("...") and pass the cursor instead of opening a new connection.

    record_execution_in_db("uuid", "program_uuid", True)
    conn = sqlite3.connect(
        "executions.db"
    )  # Consider using an in-memory database for testing
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM execution_records WHERE execution_uuid = 'uuid'")
    record = cursor.fetchone()
    assert record is not None
    assert record[0] == "uuid"
    conn.close()


@pytest.mark.asyncio
async def test_create_execution():
    # Setup before test
    await setup_directories_async()
    await create_execution("program_uuid")

    # Test
    files = os.listdir(executions_dir)
    assert len(files) > 0, "No files found in executions_dir"

    for filename in files:
        # Skip the lock file
        if filename == "sender.lock":
            continue

        file_path = os.path.join(executions_dir, filename)
        with open(file_path, "r") as file:
            file_content = file.read()
            assert file_content, f"File {file_path} is empty"


""" 
@pytest.mark.asyncio
async def test_get_xyz_for_xyz_remote():
    # Mock the external dependencies, like network calls or database interactions
    with patch(
        "nadoo_connect.function_or_class_being_called_by_get_xyz_for_xyz_remote"
    ) as mock_function:
        # Configure the mock to return a specific value or raise exceptions if needed
        mock_function.return_value = "expected_result"

        # Call the function with test data
        result = await get_xyz_for_xyz_remote("test_uuid", {"sample": "data"})

        # Assert that the result is as expected
        assert result == "expected_result"

        # Additional assertions can be made here, like checking if the mock was called with expected arguments
        mock_function.assert_called_with("test_uuid", {"sample": "data"})
 """
