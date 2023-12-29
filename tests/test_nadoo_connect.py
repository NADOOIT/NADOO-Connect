import os
import json
import sqlite3
from datetime import datetime
import pytest
from unittest.mock import AsyncMock, patch
from nadoo_connect import *

# Import the functions from your main script here, e.g.,
# from nadoo_connect import setup_directories, send_async_email, ...

executions_dir = (
    "executions"  # Ensure this matches with your main script's directory name
)


def test_setup_directories():
    # Ensure the directory is removed before the test, for a clean state
    if os.path.exists(executions_dir):
        os.rmdir(executions_dir)

    setup_directories()
    assert os.path.exists(executions_dir)


@pytest.mark.asyncio
async def test_send_async_email():
    with patch("aiosmtplib.SMTP", new_callable=AsyncMock) as mock_smtp:
        result = await send_async_email(
            "subject",
            "message",
            "to@example.com",
            "smtp.example.com",
            587,
            "user@example.com",
            "password",
        )
        assert result
        mock_smtp.assert_called()


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


def test_create_execution():
    # Setup before test
    setup_directories()
    create_execution("program_uuid")

    # Test
    files = os.listdir(executions_dir)
    assert len(files) > 0
    with open(os.path.join(executions_dir, files[0]), "r") as file:
        data = json.load(file)
        assert "execution_uuid" in data
        assert data["customer_program_uuid"] == "program_uuid"

    # Cleanup after test
    for f in files:
        os.remove(os.path.join(executions_dir, f))
    os.rmdir(executions_dir)
