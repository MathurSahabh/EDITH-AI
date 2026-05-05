import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


@dataclass
class Config:
    # LLM
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    # Web
    BING_API_KEY: str = os.getenv("BING_API_KEY", "")
    BING_ENDPOINT: str = os.getenv("BING_ENDPOINT", "https://api.bing.microsoft.com/v7.0/search")
    OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")

    # Email integrations
    EMAIL_PROVIDER_DEFAULT: str = os.getenv("EMAIL_PROVIDER_DEFAULT", "gmail")
    GMAIL_CLIENT_SECRET_PATH: str = os.getenv("GMAIL_CLIENT_SECRET_PATH", "secrets/google_client_secret.json")
    GMAIL_TOKEN_PATH: str = os.getenv("GMAIL_TOKEN_PATH", "tokens/gmail_token.json")

    OUTLOOK_CLIENT_ID: str = os.getenv("OUTLOOK_CLIENT_ID", "")
    AZURE_TENANT_ID: str = os.getenv("AZURE_TENANT_ID", "common")
    OUTLOOK_TOKEN_PATH: str = os.getenv("OUTLOOK_TOKEN_PATH", "tokens/outlook_token.json")

    # App
    ENABLE_TTS: bool = os.getenv("ENABLE_TTS", "true").lower() in {"1", "true", "yes", "on"}
    DB_PATH: str = os.getenv("DB_PATH", str(Path("data/edith.db")))
    REQUEST_TIMEOUT_SEC: int = int(os.getenv("REQUEST_TIMEOUT_SEC", "25"))
    MAX_WEB_RESULTS: int = int(os.getenv("MAX_WEB_RESULTS", "8"))

    def validate(self):
        db_parent = Path(self.DB_PATH).parent
        db_parent.mkdir(parents=True, exist_ok=True)

        Path(self.GMAIL_CLIENT_SECRET_PATH).parent.mkdir(parents=True, exist_ok=True)
        Path(self.GMAIL_TOKEN_PATH).parent.mkdir(parents=True, exist_ok=True)
        Path(self.OUTLOOK_TOKEN_PATH).parent.mkdir(parents=True, exist_ok=True)

        if not self.GROQ_API_KEY:
            raise ValueError("Missing GROQ_API_KEY in environment (.env).")

        return True