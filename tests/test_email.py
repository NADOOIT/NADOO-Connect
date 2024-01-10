import os
import json
import aiosqlite
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from nadoo_connect.nadoo_email import *

import aiosqlite
import pytest
import pytest
import glob
import os


@pytest.fixture(scope="session", autouse=True)
def cleanup_specific_files_after_tests():
    # Setup code (runs before any tests)
    yield

    # Cleanup code (runs after all tests)
    pattern = "<async_generator object setup_database_for_testing at *"  # Define your file naming pattern
    for filename in glob.glob(pattern):
        try:
            os.remove(filename)
            print(f"Deleted file: {filename}")
        except OSError as e:
            print(f"Error deleting file {filename}: {e}")


@pytest.fixture(scope="module")
async def setup_database_for_testing():
    test_db_name = "test_email_credentials.db"
    if os.path.exists(test_db_name):
        os.remove(test_db_name)

    async with aiosqlite.connect(test_db_name) as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS email_accounts (
                email TEXT PRIMARY KEY,
                pop_server TEXT,
                pop_port INTEGER,
                smtp_server TEXT,
                smtp_port INTEGER,
                password TEXT,
                is_default BOOLEAN DEFAULT 0
            );
            """
        )
        await conn.commit()

    yield test_db_name
    os.remove(test_db_name)


def test_is_valid_email():
    assert is_valid_email("test@example.com") == True
    assert is_valid_email("invalidemail") == False


@pytest.mark.asyncio
async def test_get_default_email_account(setup_database_for_testing):
    test_db_name = setup_database_for_testing
    # Your test code using test_db_name

    # Set up an in-memory SQLite database
    async with aiosqlite.connect(test_db_name) as conn:
        # Create the email_accounts table and insert test data
        await conn.execute(
            "CREATE TABLE email_accounts (email TEXT PRIMARY KEY, smtp_server TEXT, smtp_port INTEGER, password TEXT, is_default BOOLEAN DEFAULT 0);"
        )
        await conn.execute(
            "INSERT INTO email_accounts (email, smtp_server, smtp_port, password, is_default) VALUES (?, ?, ?, ?, ?)",
            ("default@example.com", "smtp.example.com", 587, "password", 1),
        )
        await conn.commit()

        # Call the function under test with in-memory database
        result = await get_default_email_account(email_account_db_name=test_db_name)

        # Assert the expected result
        assert result == ("default@example.com", "smtp.example.com", 587, "password", 1)


@pytest.mark.asyncio
async def test_get_email_account_for_email_address(setup_database_for_testing):
    async for test_db_name in setup_database_for_testing:
        # Insert test data into the test database
        async with aiosqlite.connect(test_db_name) as conn:
            await conn.execute(
                """
                INSERT INTO email_accounts (email, pop_server, pop_port, smtp_server, smtp_port, password, is_default)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "user@example.com",
                    "pop.example.com",
                    995,
                    "smtp.example.com",
                    587,
                    "password",
                    0,
                ),
            )
            await conn.commit()

        # Call the function under test with the in-memory database
        result = await get_email_account_for_email_address(
            email_address="user@example.com", email_account_db_name=test_db_name
        )

        # Assert the expected result
        assert result == (
            "user@example.com",
            "pop.example.com",
            995,
            "smtp.example.com",
            587,
            "password",
            0,
        )


@pytest.mark.asyncio
@patch("aiosmtplib.SMTP")
async def test_send_email(mock_smtp):
    mock_smtp.return_value = AsyncMock()
    result = await send_email(
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


@pytest.mark.asyncio
async def test_save_email_account(setup_database_for_testing):
    async for test_db_name in setup_database_for_testing:
        # Prepare email account details for test
        email_account = {
            "email": "user@example.com",
            "pop_server": "pop.example.com",
            "pop_port": 995,
            "smtp_server": "smtp.example.com",
            "smtp_port": 587,
            "password": "password",
        }

        # Save email account to database
        await save_email_account(
            email_account_db_name=test_db_name, email_account=email_account
        )

        # Verify that the data was inserted correctly
        async with aiosqlite.connect(test_db_name) as conn:
            cursor = await conn.execute(
                "SELECT * FROM email_accounts WHERE email = ?",
                (email_account["email"],),
            )
            result = await cursor.fetchone()

        # Assert the expected result using the helper functions
        assert result == (
            get_email_address_from_email_account(email_account),
            get_pop_server_from_email_account(email_account),
            get_pop_port_from_email_account(email_account),
            get_smtp_server_from_email_account(email_account),
            get_smtp_port_from_email_account(email_account),
            get_email_address_password_from_email_account(email_account),
            0,  # Assuming 'is_default' is false by default
        )


""" 

@pytest.mark.asyncio
async def test_get_emails_for_email_address(setup_database_for_testing):
    async for test_db_name in setup_database_for_testing:
        # Mock aiosqlite.connect to use the test database
        with patch("aiosqlite.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = AsyncMock()
            mock_connect.return_value.execute.return_value.fetchone.return_value = (
                "user@example.com",
                "smtp.example.com",
                587,
                "password",
                0,
            )
            result = await get_emails_for_email_address(
                "user@example.com", email_account_db_name=test_db_name
            )

        # Assert the expected behavior
        assert result == []
 """
