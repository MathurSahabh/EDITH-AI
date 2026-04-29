import base64
import json
from pathlib import Path
from typing import Optional, List

from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


class GmailIntegration:
    """
    Gmail send integration (OAuth desktop flow).

    Required files:
    - secrets/google_client_secret.json  (OAuth desktop credentials)
    - tokens/gmail_token.json            (auto-created after connect)

    Scopes:
    - gmail.send
    """

    SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

    def __init__(
        self,
        token_path: str = "tokens/gmail_token.json",
        client_secret_path: str = "secrets/google_client_secret.json",
    ):
        self.token_path = Path(token_path)
        self.client_secret_path = Path(client_secret_path)
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        self.client_secret_path.parent.mkdir(parents=True, exist_ok=True)

    def is_configured(self) -> bool:
        return self.client_secret_path.exists()

    def connect(self) -> str:
        if not self.client_secret_path.exists():
            return (
                "Gmail client secret missing.\n"
                "Place OAuth desktop JSON at: secrets/google_client_secret.json"
            )

        creds = self._load_or_refresh_creds(interactive=True)
        if not creds:
            return "Failed to connect Gmail."
        return "Gmail connected successfully."

    def send_email(self, to: str, subject: str, body: str, cc: Optional[List[str]] = None) -> str:
        if not to.strip():
            return "Recipient is required."

        creds = self._load_or_refresh_creds(interactive=False)
        if not creds:
            return "Gmail is not connected. Run: connect gmail"

        try:
            service = build("gmail", "v1", credentials=creds)

            msg = MIMEText(body or "")
            msg["to"] = to
            msg["subject"] = subject or "(No subject)"
            if cc:
                msg["cc"] = ", ".join([x for x in cc if x.strip()])

            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            service.users().messages().send(userId="me", body={"raw": raw}).execute()
            return "Email sent via Gmail."
        except Exception as e:
            return f"Gmail send failed: {e}"

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    def _load_or_refresh_creds(self, interactive: bool):
        creds = None

        if self.token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_path), self.SCOPES)
            except Exception:
                creds = None

        if creds and creds.valid:
            return creds

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                self._save_creds(creds)
                return creds
            except Exception:
                creds = None

        if interactive:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(str(self.client_secret_path), self.SCOPES)
                creds = flow.run_local_server(port=0)
                self._save_creds(creds)
                return creds
            except Exception:
                return None

        return None

    def _save_creds(self, creds: Credentials):
        self.token_path.write_text(creds.to_json(), encoding="utf-8")