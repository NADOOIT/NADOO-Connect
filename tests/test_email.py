import os
import json
import aiosqlite
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from nadoo_connect.email import (
    get_default_email_account,
    get_email_account_for_email_address,
    get_emails_for_email_address,
    is_valid_email,
    send_email,
    set_email_account_details_for_email_address,
)

import aiosqlite
import pytest


@pytest.fixture(scope="module")
async def setup_database_for_testing():
    test_db_name = "test_email_credentials.db"

    # Ensure any existing test database file is removed
    if os.path.exists(test_db_name):
        os.remove(test_db_name)

    async with aiosqlite.connect(test_db_name) as conn:
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

    yield test_db_name  # This will pass the database name to the tests

    # Cleanup code after tests have run
    os.remove(test_db_name)  # This will delete the test database file


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
        result = await get_default_email_account(email_credentials_db_name=test_db_name)

        # Assert the expected result
        assert result == ("default@example.com", "smtp.example.com", 587, "password", 1)


@pytest.mark.asyncio
async def test_get_email_account_for_email_address(setup_database_for_testing):
    async for test_db_name in setup_database_for_testing:
        # Insert test data into the test database
        async with aiosqlite.connect(test_db_name) as conn:
            await conn.execute(
                """
                INSERT INTO email_accounts (email, smtp_server, smtp_port, password, is_default)
                VALUES (?, ?, ?, ?, ?)
            """,
                ("user@example.com", "smtp.example.com", 587, "password", 0),
            )
            await conn.commit()

        # Call the function under test with the in-memory database
        result = await get_email_account_for_email_address(
            email_address="user@example.com", email_credentials_db_name=test_db_name
        )
        assert result == ("user@example.com", "smtp.example.com", 587, "password", 0)


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
async def test_set_email_account_details_for_email_address(setup_database_for_testing):
    async for test_db_name in setup_database_for_testing:
        # Use the test database name provided by the fixture
        await set_email_account_details_for_email_address(
            email_credentials_db_name=test_db_name,
            email_account_details={
                "smtp_server": "smtp.example.com",
                "smtp_port": 587,
                "password": "password",
            },
            email_address="user@example.com",
        )

        # Verify that the data was inserted correctly
        async with aiosqlite.connect(test_db_name) as conn:
            cursor = await conn.execute(
                "SELECT * FROM email_accounts WHERE email = ?", ("user@example.com",)
            )
            result = await cursor.fetchone()

        # Assert the expected result
        expected_details = {
            "smtp_server": "smtp.example.com",
            "smtp_port": 587,
            "password": "password",
        }
        assert result and json.loads(result[1]) == expected_details


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
                "user@example.com", email_credentials_db_name=test_db_name
            )

        # Assert the expected behavior
        assert result == []
