# email_service.py
import os.path
import base64

from email.mime.text        import MIMEText
from email.mime.multipart   import MIMEMultipart
from email.mime.application import MIMEApplication
from google.auth.transport.requests import Request
from google.oauth2.credentials      import Credentials
from google_auth_oauthlib.flow      import InstalledAppFlow
from googleapiclient.discovery      import build

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


class EmailService:
    def __init__(self):
        self.creds = None

        # Load saved token if it exists
        if os.path.exists("token.json"):
            self.creds = Credentials.from_authorized_user_file("token.json", SCOPES)

        # Refresh or create new credentials
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", SCOPES
                )
                self.creds = flow.run_local_server(port=0)

            # Save token for future runs
            with open("token.json", "w") as token:
                token.write(self.creds.to_json())

        self.service = build("gmail", "v1", credentials=self.creds)

    def send_email(self, to, subject, body):
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        sent_message = (
            self.service.users()
            .messages()
            .send(userId="me", body={"raw": raw_message})
            .execute()
        )

        return sent_message

    def send_email_with_attachment(
        self,
        to: str,
        subject: str,
        body: str,
        attachment_path: str,
        attachment_name: str | None = None,
    ):
        """Send an email with a single file attachment (e.g. a PDF report).

        Args:
            to:              Recipient email address.
            subject:         Email subject line.
            body:            Plain-text email body.
            attachment_path: Absolute or relative path to the file to attach.
            attachment_name: Filename shown to the recipient. Defaults to the
                             basename of attachment_path.
        """
        msg = MIMEMultipart()
        msg["to"]      = to
        msg["subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        name = attachment_name or os.path.basename(attachment_path)
        with open(attachment_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=name)
        part["Content-Disposition"] = f'attachment; filename="{name}"'
        msg.attach(part)

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        sent = (
            self.service.users()
            .messages()
            .send(userId="me", body={"raw": raw})
            .execute()
        )
        return sent
