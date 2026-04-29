import json
from pathlib import Path
from typing import Optional, List
import requests


class OutlookIntegration:
    """
    Outlook / Microsoft Graph email send.

    Uses device-code flow for native apps.
    Required env/config:
    - AZURE_TENANT_ID (default 'common')
    - OUTLOOK_CLIENT_ID

    Token file:
    - tokens/outlook_token.json
    """

    GRAPH_SCOPE = "https://graph.microsoft.com/Mail.Send offline_access openid profile"

    def __init__(
        self,
        client_id: str = "",
        tenant_id: str = "common",
        token_path: str = "tokens/outlook_token.json",
    ):
        self.client_id = client_id.strip()
        self.tenant_id = tenant_id.strip() or "common"
        self.token_path = Path(token_path)
        self.token_path.parent.mkdir(parents=True, exist_ok=True)

    def is_configured(self) -> bool:
        return bool(self.client_id)

    def connect(self) -> str:
        if not self.client_id:
            return "Outlook client ID missing. Set OUTLOOK_CLIENT_ID in .env/config."

        device_code_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/devicecode"
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"

        try:
            dc_resp = requests.post(
                device_code_url,
                data={"client_id": self.client_id, "scope": self.GRAPH_SCOPE},
                timeout=20,
            )
            if dc_resp.status_code != 200:
                return f"Outlook device-code init failed: {dc_resp.text[:300]}"

            dc = dc_resp.json()
            user_code = dc.get("user_code", "")
            verify_uri = dc.get("verification_uri", "")
            device_code = dc.get("device_code", "")
            interval = int(dc.get("interval", 5))
            expires_in = int(dc.get("expires_in", 900))

            if not device_code:
                return "Outlook device code missing in response."

            print("\n=== Outlook Connect ===")
            print(f"Go to: {verify_uri}")
            print(f"Enter code: {user_code}")
            print("=======================\n")

            elapsed = 0
            while elapsed < expires_in:
                tk_resp = requests.post(
                    token_url,
                    data={
                        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                        "client_id": self.client_id,
                        "device_code": device_code,
                    },
                    timeout=20,
                )

                if tk_resp.status_code == 200:
                    token_data = tk_resp.json()
                    self.token_path.write_text(json.dumps(token_data, indent=2), encoding="utf-8")
                    return "Outlook connected successfully."

                err = tk_resp.json().get("error", "")
                if err in {"authorization_pending", "slow_down"}:
                    import time
                    time.sleep(interval)
                    elapsed += interval
                    continue

                return f"Outlook connect failed: {tk_resp.text[:300]}"

            return "Outlook connect timed out."
        except Exception as e:
            return f"Outlook connect failed: {e}"

    def send_email(self, to: str, subject: str, body: str, cc: Optional[List[str]] = None) -> str:
        if not to.strip():
            return "Recipient is required."

        token = self._get_access_token()
        if not token:
            return "Outlook is not connected. Run: connect outlook"

        url = "https://graph.microsoft.com/v1.0/me/sendMail"
        payload = {
            "message": {
                "subject": subject or "(No subject)",
                "body": {
                    "contentType": "Text",
                    "content": body or "",
                },
                "toRecipients": [{"emailAddress": {"address": to.strip()}}],
            },
            "saveToSentItems": "true"
        }

        cc_list = [x.strip() for x in (cc or []) if x.strip()]
        if cc_list:
            payload["message"]["ccRecipients"] = [
                {"emailAddress": {"address": addr}} for addr in cc_list
            ]

        try:
            r = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=25,
            )

            if r.status_code in {200, 202}:
                return "Email sent via Outlook."
            if r.status_code == 401:
                return "Outlook token expired/invalid. Reconnect using: connect outlook"
            return f"Outlook send failed ({r.status_code}): {r.text[:300]}"
        except Exception as e:
            return f"Outlook send failed: {e}"

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    def _get_access_token(self) -> Optional[str]:
        if not self.token_path.exists():
            return None
        try:
            data = json.loads(self.token_path.read_text(encoding="utf-8"))
            return data.get("access_token")
        except Exception:
            return None