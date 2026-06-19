import base64
import os
from email.mime.text import MIMEText

import anthropic
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# Add or remove leads here — each email is generated and sent individually.
LEADS = [
    {
        "name": "Sarah Johnson",
        "business_name": "Bloom Bakery",
        "email": "zaidmajeedkhan@gmail.com",
        "inquiry": "custom wedding cake packages and pricing",
    },
    # {
    #     "name": "Marcus Lee",
    #     "business_name": "Pinnacle Events",
    #     "email": "example@example.com",
    #     "inquiry": "corporate catering options for quarterly offsite",
    # },
]

SYSTEM_PROMPT = (
    "You are a professional sales assistant. Write short, warm, and polished "
    "follow-up emails for leads who have inquired about our services. "
    "Keep every email under 150 words. "
    "End the email with exactly this sign-off on its own line, nothing else after it:\n\n"
    "Warm regards,\nThe Team\n\n"
    "Do not add any name, company name, phone number, email address, or any other "
    "placeholder or contact details after the sign-off. "
    "Write the complete email — no placeholders of any kind."
)


def get_gmail_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", GMAIL_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", GMAIL_SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def send_email(service, to: str, subject: str, body: str):
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
    print(f"  Sent to {to}")


def generate_email(client: anthropic.Anthropic, lead: dict) -> str:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=SYSTEM_PROMPT,
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


def main():
    claude = anthropic.Anthropic()
    gmail = get_gmail_service()

    for lead in LEADS:
        print(f"\nProcessing lead: {lead['name']} ({lead['business_name']})")
        email_body = generate_email(claude, lead)
        print(email_body)
        subject = f"Following up – {lead['business_name']}"
        send_email(gmail, lead["email"], subject, email_body)

    print(f"\nDone — {len(LEADS)} email(s) sent.")


if __name__ == "__main__":
    main()
