import aiosmtplib
from email.mime.text import MIMEText


async def send_async_email(
    subject, message, to_email, smtp_server, smtp_port, email, password
) -> bool:
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
