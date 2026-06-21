"""Lead Follow-Up Agent.

Generates personalized follow-up emails for sales leads using the Anthropic
Claude API and (optionally) sends them through the Gmail API.

Leads are read from a JSON file (``leads.json`` by default). Use ``--dry-run``
to preview generated emails without sending anything.
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

import anthropic
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()

logger = logging.getLogger("lead_followup_agent")

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

DEFAULT_LEADS_FILE = "leads.json"
DEFAULT_SENT_LOG = "sent.json"
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"

REQUIRED_LEAD_FIELDS = ("name", "business_name", "email", "inquiry")


@dataclass(frozen=True)
class Config:
    """Runtime configuration assembled from env vars and CLI arguments."""

    model: str
    max_tokens: int
    signature_name: str
    company_name: str
    send_delay_seconds: float
    leads_file: Path
    sent_log: Path
    dry_run: bool

    @property
    def system_prompt(self) -> str:
        return (
            "You are a professional sales assistant. Write short, warm, and polished "
            "follow-up emails for leads who have inquired about our services. "
            "Keep every email under 150 words. "
            "End the email with exactly this sign-off on its own line, nothing else after it:\n\n"
            f"Warm regards,\n{self.signature_name}\n\n"
            "Do not add any name, company name, phone number, email address, or any other "
            "placeholder or contact details after the sign-off. "
            "Write the complete email — no placeholders of any kind."
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate and send personalized follow-up emails for sales leads.",
    )
    parser.add_argument(
        "--leads",
        default=os.getenv("LEADS_FILE", DEFAULT_LEADS_FILE),
        help=f"Path to the leads JSON file (default: {DEFAULT_LEADS_FILE}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate and print emails without sending them.",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("MODEL", "claude-sonnet-4-6"),
        help="Claude model to use.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=float(os.getenv("SEND_DELAY_SECONDS", "1.0")),
        help="Seconds to wait between sends.",
    )
    parser.add_argument(
        "--sent-log",
        default=os.getenv("SENT_LOG", DEFAULT_SENT_LOG),
        help=f"Path to the sent-tracking JSON file (default: {DEFAULT_SENT_LOG}).",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity.",
    )
    return parser.parse_args(argv)


def build_config(args: argparse.Namespace) -> Config:
    """Build a :class:`Config` from parsed args and environment variables."""
    return Config(
        model=args.model,
        max_tokens=int(os.getenv("MAX_TOKENS", "512")),
        signature_name=os.getenv("SIGNATURE_NAME", "The Team"),
        company_name=os.getenv("COMPANY_NAME", ""),
        send_delay_seconds=args.delay,
        leads_file=Path(args.leads),
        sent_log=Path(args.sent_log),
        dry_run=args.dry_run,
    )


def load_leads(path: Path) -> list[dict[str, Any]]:
    """Load and validate leads from a JSON file.

    Raises:
        FileNotFoundError: if the leads file does not exist.
        ValueError: if the file is malformed or a lead is missing fields.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Leads file not found: {path}. Copy leads.example.json to {path} "
            "and add your leads."
        )

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Could not parse {path}: {exc}") from exc

    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array of lead objects.")

    for index, lead in enumerate(data):
        if not isinstance(lead, dict):
            raise ValueError(f"Lead #{index + 1} in {path} is not an object.")
        missing = [field for field in REQUIRED_LEAD_FIELDS if not lead.get(field)]
        if missing:
            raise ValueError(
                f"Lead #{index + 1} in {path} is missing required field(s): "
                f"{', '.join(missing)}."
            )

    return data


def load_sent_log(path: Path) -> set[str]:
    """Return the set of email addresses already contacted."""
    if not path.exists():
        return set()
    try:
        records = json.loads(path.read_text(encoding="utf-8"))
        return {record["email"] for record in records if "email" in record}
    except (json.JSONDecodeError, TypeError):
        logger.warning("Could not read sent log at %s; treating as empty.", path)
        return set()


def record_sent(path: Path, lead: dict[str, Any], subject: str) -> None:
    """Append a sent record to the sent log."""
    records: list[dict[str, Any]] = []
    if path.exists():
        try:
            records = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            records = []
    records.append(
        {
            "email": lead["email"],
            "name": lead["name"],
            "business_name": lead["business_name"],
            "subject": subject,
            "sent_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }
    )
    path.write_text(json.dumps(records, indent=2), encoding="utf-8")


def get_gmail_service():  # noqa: ANN201 - googleapiclient resource has no stable type
    """Authenticate with Gmail and return a service client.

    Uses cached credentials in ``token.json`` when available, otherwise runs
    the OAuth installed-app flow against ``credentials.json``.
    """
    creds: Credentials | None = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, GMAIL_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"{CREDENTIALS_FILE} not found. Download your OAuth client "
                    "credentials from Google Cloud Console (see README)."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, GMAIL_SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w", encoding="utf-8") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def send_email(service: Any, to: str, subject: str, body: str) -> None:
    """Send a plain-text email through the Gmail API."""
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()


def generate_email(client: anthropic.Anthropic, config: Config, lead: dict[str, Any]) -> str:
    """Generate a follow-up email body for a single lead."""
    response = client.messages.create(
        model=config.model,
        max_tokens=config.max_tokens,
        system=config.system_prompt,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Write a follow-up email for this lead:\n"
                    f"Name: {lead['name']}\n"
                    f"Business: {lead['business_name']}\n"
                    f"They inquired about: {lead['inquiry']}"
                ),
            }
        ],
    )
    return response.content[0].text


def build_subject(config: Config, lead: dict[str, Any]) -> str:
    """Build the email subject line for a lead."""
    if config.company_name:
        return f"Following up – {lead['business_name']} × {config.company_name}"
    return f"Following up – {lead['business_name']}"


def configure_logging(level: str) -> None:
    """Configure root logging output."""
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s  %(levelname)-7s  %(message)s",
        datefmt="%H:%M:%S",
    )


def run(config: Config) -> int:
    """Execute the full generate/send pipeline. Returns a process exit code."""
    leads = load_leads(config.leads_file)
    already_sent = set() if config.dry_run else load_sent_log(config.sent_log)

    claude = anthropic.Anthropic()
    gmail = None if config.dry_run else get_gmail_service()

    sent_count = 0
    skipped_count = 0
    failed_count = 0

    mode = "DRY RUN — no emails will be sent" if config.dry_run else "LIVE"
    logger.info("Starting (%s). %d lead(s) loaded from %s.", mode, len(leads), config.leads_file)

    for lead in leads:
        label = f"{lead['name']} ({lead['business_name']})"

        if lead["email"] in already_sent:
            logger.info("Skipping %s — already contacted at %s.", label, lead["email"])
            skipped_count += 1
            continue

        try:
            logger.info("Generating email for %s.", label)
            body = generate_email(claude, config, lead)
            subject = build_subject(config, lead)
        except Exception:  # noqa: BLE001 - log and continue to next lead
            logger.exception("Failed to generate email for %s.", label)
            failed_count += 1
            continue

        if config.dry_run:
            print(f"\n{'=' * 70}\nTo: {lead['email']}\nSubject: {subject}\n{'-' * 70}")
            print(body)
            sent_count += 1
            continue

        try:
            send_email(gmail, lead["email"], subject, body)
            record_sent(config.sent_log, lead, subject)
            logger.info("Sent to %s.", lead["email"])
            sent_count += 1
        except Exception:  # noqa: BLE001 - log and continue to next lead
            logger.exception("Failed to send email to %s.", lead["email"])
            failed_count += 1
            continue

        if config.send_delay_seconds > 0:
            time.sleep(config.send_delay_seconds)

    verb = "previewed" if config.dry_run else "sent"
    logger.info(
        "Done — %d %s, %d skipped, %d failed.",
        sent_count,
        verb,
        skipped_count,
        failed_count,
    )
    return 1 if failed_count else 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    args = parse_args(argv)
    configure_logging(args.log_level)
    config = build_config(args)

    try:
        return run(config)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("%s", exc)
        return 1
    except KeyboardInterrupt:
        logger.warning("Interrupted by user.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
