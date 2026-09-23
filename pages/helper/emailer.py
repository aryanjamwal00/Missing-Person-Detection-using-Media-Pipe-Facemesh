"""
Email notification helper.

Reads SMTP config from environment variables or a local .env file:
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD

Recipient is the complainant_email stored on the case.
Falls back to NOTIFY_EMAIL env var if complainant email is not set.
"""

import os
import smtplib
from dataclasses import dataclass
from smtplib import SMTPAuthenticationError, SMTPResponseException
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


@dataclass
class EmailResult:
    sent: bool
    message: str
    recipient: str | None = None

    def __bool__(self) -> bool:
        return self.sent


def _load_dotenv() -> None:
    """Load simple KEY=VALUE pairs from .env."""
    env_path = ".env"
    if not os.path.exists(env_path):
        return

    with open(env_path, encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ[key] = value


def send_match_notification(case_id: str, case_details: tuple) -> EmailResult:
    """
    Send an email when a missing person case has been matched.

    Args:
        case_id: The registered case UUID.
        case_details: Tuple of (name, complainant_mobile, complainant_email, age, last_seen, birth_marks).

    Returns:
        EmailResult with send status and a user-facing message.
    """
    _load_dotenv()

    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = os.environ.get("SMTP_PORT", "587")
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    if smtp_password:
        smtp_password = "".join(smtp_password.split())

    missing = [
        key
        for key, value in {
            "SMTP_HOST": smtp_host,
            "SMTP_USER": smtp_user,
            "SMTP_PASSWORD": smtp_password,
        }.items()
        if not value
    ]
    if missing:
        message = "Missing email configuration: " + ", ".join(missing)
        print(f"[emailer] {message}")
        return EmailResult(False, message)

    name = case_details[0] if case_details else "Unknown"
    complainant_email = case_details[2] if len(case_details) > 2 else None
    age = case_details[3] if len(case_details) > 3 else "N/A"
    last_seen = case_details[4] if len(case_details) > 4 else "N/A"

    recipient = complainant_email or os.environ.get("NOTIFY_EMAIL")
    if not recipient:
        message = "No recipient email found. Add complainant email or NOTIFY_EMAIL."
        print(f"[emailer] {message}")
        return EmailResult(False, message)

    try:
        subject = f"Match Found - {name}"
        body = f"""\
Hello,

A match has been found for the following missing person case registered in the system.

Case Details:
  Name      : {name}
  Age       : {age}
  Last Seen : {last_seen}
  Case ID   : {case_id}

Please log in to the Missing Person Tracking System to review the match details.

--
This is an automated notification. Please do not reply to this email.
"""
        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        port = int(smtp_port)
        if port == 465:
            server = smtplib.SMTP_SSL(smtp_host, port, timeout=30)
        else:
            server = smtplib.SMTP(smtp_host, port, timeout=30)

        with server:
            if port != 465:
                server.ehlo()
                server.starttls()
                server.ehlo()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, recipient, msg.as_string())

        message = f"Notification sent to {recipient} for case {case_id}"
        print(f"[emailer] {message}")
        return EmailResult(True, message, recipient)

    except SMTPAuthenticationError:
        message = (
            "Gmail rejected the SMTP login. Create a fresh Gmail App Password "
            f"for {smtp_user}, then put that 16-character password in .env."
        )
        print(f"[emailer] {message}")
        return EmailResult(False, message, recipient)
    except SMTPResponseException as exc:
        if exc.smtp_code == 535:
            message = (
                "Gmail rejected the SMTP login. Make sure SMTP_USER is the same "
                "Google account that created the app password, then restart Streamlit."
            )
            print(f"[emailer] {message}")
            return EmailResult(False, message, recipient)
        message = f"SMTP error {exc.smtp_code}: {exc.smtp_error!r}"
        print(f"[emailer] {message}")
        return EmailResult(False, message, recipient)
    except Exception as exc:
        message = f"Failed to send email: {exc}"
        print(f"[emailer] {message}")
        return EmailResult(False, message, recipient)
