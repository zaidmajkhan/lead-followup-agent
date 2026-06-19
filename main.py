from dotenv import load_dotenv
import anthropic
import os
import base64
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()

RECIPIENT_EMAIL = "zaidmajeedkhan@gmail.com"

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

lead = {
    "name": "Sarah Johnson",
    "business_name": "Bloom Bakery",
    "inquiry": "custom wedding cake packages and pricing",
}


def get_gmail_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", GMAIL_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", GMAIL_SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def send_email(service, to, subject, body):
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
    print(f"Email sent to {to}")


client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=512,
    system=(
        "You are a helpful sales assistant. Write short, warm, and professional "
        "follow-up emails for leads who have inquired about our services. "
        "Keep emails under 150 words. Do not use placeholders — write the full email."
    ),
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

email_text = response.content[0].text
print(email_text)

gmail = get_gmail_service()
send_email(gmail, RECIPIENT_EMAIL, f"Following up – {lead['business_name']}", email_text)
