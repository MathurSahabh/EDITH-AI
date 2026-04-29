import os
import sys
import subprocess
from pathlib import Path


class AppControl:
    def __init__(self):
        self.platform = sys.platform.lower()
        self.is_windows = self.platform.startswith("win")

        self.aliases = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "calc": "calc.exe",
            "paint": "mspaint.exe",
            "cmd": "cmd.exe",
            "powershell": "powershell.exe",
            "explorer": "explorer.exe",
            "chrome": "chrome.exe",
            "edge": "msedge.exe",
            "firefox": "firefox.exe",
            "vscode": "code",
            "vs code": "code",
            "outlook": "outlook.exe",
            "word": "winword.exe",
            "excel": "excel.exe",
            "powerpoint": "powerpnt.exe",
            "ppt": "powerpnt.exe",
            "whatsapp": "whatsapp:",
        }

        self.office_exe_map = {
            "outlook": "OUTLOOK.EXE",
            "word": "WINWORD.EXE",
            "excel": "EXCEL.EXE",
            "powerpoint": "POWERPNT.EXE",
            "ppt": "POWERPNT.EXE",
        }

        self.kill_map = {
            "notepad": "notepad.exe",
            "calculator": "CalculatorApp.exe",
            "calc": "CalculatorApp.exe",
            "paint": "mspaint.exe",
            "cmd": "cmd.exe",
            "powershell": "powershell.exe",
            "explorer": "explorer.exe",
            "chrome": "chrome.exe",
            "edge": "msedge.exe",
            "firefox": "firefox.exe",
            "vscode": "Code.exe",
            "vs code": "Code.exe",
            "outlook": "OUTLOOK.EXE",
            "word": "WINWORD.EXE",
            "excel": "EXCEL.EXE",
            "powerpoint": "POWERPNT.EXE",
            "ppt": "POWERPNT.EXE",
            "whatsapp": "WhatsApp.exe",
        }

    # ---------------- OPEN ----------------
    def _start_cmd(self, target: str) -> bool:
        try:
            rc = subprocess.run(["cmd", "/c", "start", "", target], timeout=8, shell=False)
            return rc.returncode == 0
        except Exception:
            return False

    def _ps_start(self, target: str) -> bool:
        try:
            cmd = [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy", "Bypass",
                "-Command",
                f"Start-Process -FilePath '{target}'"
            ]
            rc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return rc.returncode == 0
        except Exception:
            return False

    def _open_office_by_path(self, exe_name: str) -> bool:
        roots = [
            r"C:\Program Files\Microsoft Office\root\Office16",
            r"C:\Program Files (x86)\Microsoft Office\root\Office16",
            r"C:\Program Files\Microsoft Office\Office16",
            r"C:\Program Files (x86)\Microsoft Office\Office16",
        ]
        for root in roots:
            p = Path(root) / exe_name
            if p.exists():
                return self._ps_start(str(p)) or self._start_cmd(str(p))
        return False

    def open_app(self, app_name: str) -> str:
        raw = (app_name or "").strip().strip('"')
        if not raw:
            return "No app name provided."

        key = " ".join(raw.lower().replace("application", "").replace("app", "").split())
        target = self.aliases.get(key, raw)

        if self.is_windows:
            if self._start_cmd(target) or self._ps_start(target):
                return f"Opened app: {raw}"

            if key in self.office_exe_map and self._open_office_by_path(self.office_exe_map[key]):
                return f"Opened app: {raw}"

            try:
                chk = subprocess.run(["where", target], capture_output=True, text=True, timeout=8, shell=True)
                if chk.returncode == 0 and chk.stdout.strip():
                    first = chk.stdout.splitlines()[0].strip()
                    if self._start_cmd(first) or self._ps_start(first):
                        return f"Opened app: {raw}"
            except Exception:
                pass

            return f"Open failed: could not find installed app '{raw}'."

        # mac/linux
        try:
            if self.platform == "darwin":
                rc = subprocess.run(["open", "-a", raw], capture_output=True, text=True, timeout=8)
                if rc.returncode == 0:
                    return f"Opened app: {raw}"
            else:
                rc = subprocess.run([raw], capture_output=True, text=True, timeout=8)
                if rc.returncode == 0:
                    return f"Opened app: {raw}"
        except Exception:
            pass

        return f"Open failed: could not find installed app '{raw}'."

    # ---------------- CLOSE ----------------
    def close_app(self, app_name: str) -> str:
        raw = (app_name or "").strip().strip('"')
        if not raw:
            return "No app name provided."

        key = " ".join(raw.lower().replace("application", "").replace("app", "").split())

        if self.is_windows:
            image = self.kill_map.get(key)
            if image is None:
                # fallback: if user gave .exe or plain name
                image = raw if raw.lower().endswith(".exe") else f"{raw}.exe"

            try:
                rc = subprocess.run(
                    ["taskkill", "/F", "/IM", image],
                    capture_output=True,
                    text=True,
                    timeout=8
                )
                if rc.returncode == 0:
                    return f"Closed app: {raw}"
                return f"Close failed for '{raw}': {rc.stderr.strip() or rc.stdout.strip()}"
            except Exception as e:
                return f"Close failed for '{raw}': {e}"

        # mac
        if self.platform == "darwin":
            try:
                rc = subprocess.run(
                    ["osascript", "-e", f'tell application "{raw}" to quit'],
                    capture_output=True, text=True, timeout=8
                )
                return f"Closed app: {raw}" if rc.returncode == 0 else f"Close failed for '{raw}'."
            except Exception as e:
                return f"Close failed for '{raw}': {e}"

        # linux
        try:
            rc = subprocess.run(["pkill", "-f", raw], capture_output=True, text=True, timeout=8)
            return f"Closed app: {raw}" if rc.returncode == 0 else f"Close failed for '{raw}'."
        except Exception as e:
            return f"Close failed for '{raw}': {e}"