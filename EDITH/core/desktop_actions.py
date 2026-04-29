import os
import sys
import re
import subprocess
import webbrowser
from pathlib import Path
from core.app_control import AppControl

try:
    import pyautogui
except Exception:
    pyautogui = None


class DesktopActions:
    def __init__(self):
        self.platform = sys.platform.lower()
        self.is_windows = self.platform.startswith("win")
        self.app_control = AppControl()  # ✅ inside class init

        self.app_candidates = {
            "youtube": ["youtube:", "YouTube.exe", "youtube.exe"],
            "whatsapp": [
                "whatsapp:",
                r"shell:AppsFolder\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App",
                "WhatsApp.exe",
                "whatsapp.exe",
            ],
            "email": ["outlook.exe", "thunderbird.exe"],
            "gmail": ["outlook.exe", "thunderbird.exe"],
            "calculator": ["calc.exe", "calc"],
            "notepad": ["notepad.exe", "notepad"],
            "paint": ["mspaint.exe", "mspaint"],
            "cmd": ["cmd.exe", "cmd"],
            "powershell": ["powershell.exe", "powershell"],
            "explorer": ["explorer.exe", "explorer"],
            "chrome": ["chrome.exe", "chrome"],
            "edge": ["msedge.exe", "msedge"],
            "firefox": ["firefox.exe", "firefox"],
            "vscode": ["Code.exe", "code"],
            "vs code": ["Code.exe", "code"],
            "telegram": ["Telegram.exe", "telegram"],
            "spotify": ["Spotify.exe", "spotify"],
            "outlook": ["outlook.exe", "outlook"],
            "word": ["winword.exe", "winword"],
            "excel": ["excel.exe", "excel"],
            "powerpoint": ["powerpnt.exe", "powerpnt"],
            "ppt": ["powerpnt.exe", "powerpnt"],
        }

        self.web_fallback = {
            "youtube": "https://www.youtube.com",
            "whatsapp": "https://web.whatsapp.com",
            "email": "https://mail.google.com",
            "gmail": "https://mail.google.com",
            "github": "https://github.com",
            "google": "https://www.google.com",
            "instagram": "https://www.instagram.com",
            "facebook": "https://www.facebook.com",
            "twitter": "https://x.com",
            "x": "https://x.com",
            "linkedin": "https://www.linkedin.com",
            "reddit": "https://www.reddit.com",
            "chatgpt": "https://chat.openai.com",
            "netflix": "https://www.netflix.com",
            "amazon": "https://www.amazon.in",
        }

    # ------------------- delegated app control -------------------
    def open_app(self, app_name: str) -> str:
        return self.app_control.open_app(app_name)

    def close_app(self, app_name: str) -> str:
        return self.app_control.close_app(app_name)

    # ------------------------------------------------------------------
    # website
    # ------------------------------------------------------------------
    def open_website(self, url: str) -> str:
        u = (url or "").strip()
        if not u:
            return "No URL provided."
        if not (u.startswith("http://") or u.startswith("https://")):
            u = "https://" + u
        try:
            ok = webbrowser.open(u, new=2)
            return f"Opened website: {u}" if ok else f"Tried opening website: {u}"
        except Exception as e:
            return f"Failed to open website: {e}"

    # ------------------------------------------------------------------
    # open file
    # ------------------------------------------------------------------
    def open_file(self, path: str) -> str:
        raw = (path or "").strip().strip('"')
        if not raw:
            return "No file path provided."

        p = Path(raw).expanduser()
        if not p.exists():
            return f"File not found: {p}"

        try:
            if self.is_windows:
                os.startfile(str(p))  # type: ignore[attr-defined]
            elif self.platform == "darwin":
                subprocess.Popen(["open", str(p)])
            else:
                subprocess.Popen(["xdg-open", str(p)])
            return f"Opened file: {p}"
        except Exception as e:
            return f"Failed to open file: {e}"

    # ------------------------------------------------------------------
    # typing/hotkeys
    # ------------------------------------------------------------------
    def type_text(self, text: str, interval: float = 0.01) -> str:
        if pyautogui is None:
            return "pyautogui is not installed. Run: pip install pyautogui"
        if not text:
            return "No text provided to type."
        try:
            pyautogui.write(text, interval=interval)
            return "Typed text."
        except Exception as e:
            return f"Failed to type text: {e}"

    def parse_hotkey(self, hotkey_text: str):
        parts = [p.strip().lower() for p in (hotkey_text or "").split("+") if p.strip()]
        return tuple(parts)

    def press_hotkey(self, *keys: str) -> str:
        if pyautogui is None:
            return "pyautogui is not installed. Run: pip install pyautogui"
        if not keys:
            return "No hotkey provided."
        try:
            pyautogui.hotkey(*keys)
            return f"Pressed hotkey: {' + '.join(keys)}"
        except Exception as e:
            return f"Failed to press hotkey: {e}"