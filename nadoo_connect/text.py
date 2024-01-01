from email.mime.text import MIMEText
import aiosmtplib

import traceback


async def print_all_stack_traces():
    for task in asyncio.all_tasks():
        task.print_stack()


async def send_async_email(
    subject, message, to_email, smtp_server, smtp_port, email, password
) -> bool:
    try:
        current_task = asyncio.current_task()
        print(f"Current task: {current_task}")
        print(f"Event loop is running: {asyncio.get_running_loop().is_running()}")
        print_all_stack_traces

        # Print out the parameters to verify their values
        print(
            f"Parameters:\nSubject: {subject}\nMessage: {message}\nTo: {to_email}\nSMTP Server: {smtp_server}\nPort: {smtp_port}\nEmail: {email}\nPassword: {password}"
        )

        msg = MIMEText(message, _subtype="plain", _charset="utf-8")
        msg["Subject"] = subject
        msg["From"] = email
        msg["To"] = to_email

        print("THIS SHOULD BE WORKING >:>")
        async with aiosmtplib.SMTP(
            hostname=smtp_server, port=smtp_port, use_tls=True
        ) as smtp:
            print("This is where I seem to fail :/")
            await smtp.login(email, password)
            print("Logged IN")
            await smtp.send_message(msg)
            print("should be sending...")

        print("Why is nothing happening???")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


"""async def send_async_email(
    subject, message, to_email, smtp_server, smtp_port, email, password
):
    try:
        print(
            f"Sending Email:\nSubject: {subject}\nTo: {to_email}\nServer: {smtp_server}\nPort: {smtp_port}"
        )

        msg = MIMEText(message, _subtype="plain", _charset="utf-8")
        msg["Subject"] = subject
        msg["From"] = email
        msg["To"] = to_email

        async with aiosmtplib.SMTP(
            hostname=smtp_server, port=smtp_port, use_tls=True
        ) as smtp:
            await smtp.login(email, password)
            await smtp.send_message(msg)

        print("Email sent successfully.")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
"""


# Example usage
async def main():
    await send_async_email(
        "Test Subject",
        "This is a test message.",
        "executions@nadooit.de",
        "smtp.ionos.de",
        465,
        "a6713ea1-6283-4fe6-a36b@nadooit.de",
        "aC8X7Yd.!J4bd9:gz8gz8zggi8ziuzb",  # Replace with actual password
    )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
