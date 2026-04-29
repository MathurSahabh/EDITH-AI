from typing import Optional, List

from integrations.email_gmail import GmailIntegration
from integrations.email_outlook import OutlookIntegration


class EmailRouter:
    """
    Selects provider and sends via Gmail or Outlook.
    """

    def __init__(self, config):
        self.gmail = GmailIntegration(
            token_path=getattr(config, "GMAIL_TOKEN_PATH", "tokens/gmail_token.json"),
            client_secret_path=getattr(config, "GMAIL_CLIENT_SECRET_PATH", "secrets/google_client_secret.json"),
        )
        self.outlook = OutlookIntegration(
            client_id=getattr(config, "OUTLOOK_CLIENT_ID", ""),
            tenant_id=getattr(config, "AZURE_TENANT_ID", "common"),
            token_path=getattr(config, "OUTLOOK_TOKEN_PATH", "tokens/outlook_token.json"),
        )

        self.default_provider = getattr(config, "EMAIL_PROVIDER_DEFAULT", "gmail").lower().strip()

    def connect(self, provider: str) -> str:
        p = (provider or "").lower().strip()
        if p == "gmail":
            return self.gmail.connect()
        if p == "outlook":
            return self.outlook.connect()
        return "Unknown provider. Use: gmail or outlook"

    def send(
        self,
        to: str,
        subject: str,
        body: str,
        provider: Optional[str] = None,
        cc: Optional[List[str]] = None,
    ) -> str:
        p = (provider or self.default_provider).lower().strip()

        if p == "gmail":
            return self.gmail.send_email(to=to, subject=subject, body=body, cc=cc)
        if p == "outlook":
            return self.outlook.send_email(to=to, subject=subject, body=body, cc=cc)

        return "Unknown provider. Use provider gmail or outlook."