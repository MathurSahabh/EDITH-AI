import os
import platform
import subprocess
import shlex
import re
import webbrowser
import urllib.parse
import time
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

import psutil
import requests
import pyautogui
import pygetwindow as gw

from core.desktop_actions import DesktopActions
from core.skills import AgentSkills


class CommandRouter:
    """
    Unified CommandRouter (v6.4 final)
    """

    def __init__(self, groq_client, openweather_api_key: str = "", config=None):
        self.groq = groq_client
        self.openweather_api_key = openweather_api_key
        self.config = config
        self.desktop = DesktopActions()
        self._skills = None

        self.city_tz = {
            "london": "Europe/London",
            "new york": "America/New_York",
            "newyork": "America/New_York",
            "nyc": "America/New_York",
            "los angeles": "America/Los_Angeles",
            "la": "America/Los_Angeles",
            "chicago": "America/Chicago",
            "denver": "America/Denver",
            "phoenix": "America/Phoenix",
            "tokyo": "Asia/Tokyo",
            "dubai": "Asia/Dubai",
            "delhi": "Asia/Kolkata",
            "mumbai": "Asia/Kolkata",
            "kolkata": "Asia/Kolkata",
            "lucknow": "Asia/Kolkata",
            "paris": "Europe/Paris",
            "berlin": "Europe/Berlin",
            "sydney": "Australia/Sydney",
            "usa": "America/New_York",
            "us": "America/New_York",
            "india": "Asia/Kolkata",
            "uk": "Europe/London",
        }

    def _ensure_skills(self, memory, search):
        if self._skills is None:
            self._skills = AgentSkills(
                groq_client=self.groq,
                memory=memory,
                search=search,
                config=self.config
            )

    # ---------- NORMALIZATION ----------
    def _normalize_for_match(self, text: str) -> str:
        t = (text or "").lower().strip()
        t = t.replace("whats app", "whatsapp")
        t = t.replace("whatapp", "whatsapp")
        t = t.replace("whatsap", "whatsapp")
        t = t.replace("watsapp", "whatsapp")
        t = re.sub(r"\s+", " ", t)
        return t

    # ---------- CONTACT HELPERS ----------
    def _contact_key(self, name: str) -> str:
        return f"contact.{(name or '').strip().lower()}"

    def _get_contact_number(self, memory, name: str):
        if memory is None:
            return None
        return memory.get_preference(self._contact_key(name), None)

    def _set_contact_number(self, memory, name: str, number: str):
        if memory is None:
            return "Memory not available."
        n = re.sub(r"\D", "", number or "")
        if len(n) < 10:
            return "Please provide a valid phone number (at least 10 digits, include country code)."
        clean_name = (name or "").strip().lower()
        if not clean_name:
            return "Please provide a contact name."
        memory.set_preference(self._contact_key(clean_name), n)
        return f"Saved contact: {clean_name} -> {n}"

    def _delete_contact(self, memory, name: str):
        if memory is None:
            return "Memory not available."
        clean_name = (name or "").strip().lower()
        if not clean_name:
            return "Please provide a contact name."
        key = self._contact_key(clean_name)
        existing = memory.get_preference(key, None)
        if not existing:
            return f"Contact '{clean_name}' not found."
        memory.set_preference(key, None)
        return f"Deleted contact: {clean_name}"

    def _list_contacts(self, memory):
        if memory is None:
            return "Memory not available."

        data = None
        if hasattr(memory, "store") and isinstance(getattr(memory, "store"), dict):
            data = memory.store
        elif hasattr(memory, "preferences") and isinstance(getattr(memory, "preferences"), dict):
            data = memory.preferences

        if not isinstance(data, dict):
            return (
                "Cannot list contacts with current memory backend.\n"
                "You can still use: save contact <name> = <number> and send whatsapp to <name> that <message>."
            )

        contacts = []
        for k, v in data.items():
            if isinstance(k, str) and k.startswith("contact.") and v:
                name = k.split("contact.", 1)[1]
                contacts.append((name, str(v)))

        if not contacts:
            return "No saved contacts."

        contacts.sort(key=lambda x: x[0])
        lines = ["Saved WhatsApp contacts:"]
        for name, num in contacts:
            lines.append(f"- {name}: {num}")
        return "\n".join(lines)

    # ---------- FOCUS HELPERS ----------
    def _focus_whatsapp_window(self, timeout_sec: float = 8.0) -> bool:
        end = time.time() + timeout_sec
        needles = ["whatsapp", "chat", "meta ai"]

        while time.time() < end:
            try:
                wins = gw.getAllWindows()
                for w in wins:
                    title = (w.title or "").lower()
                    if any(k in title for k in needles):
                        try:
                            if w.isMinimized:
                                w.restore()
                            w.activate()
                            time.sleep(0.25)
                            return True
                        except Exception:
                            continue
            except Exception:
                pass
            time.sleep(0.25)

        return False

    def _focus_lock_send_enter(self, tries: int = 5, gap_sec: float = 0.6) -> bool:
        for _ in range(tries):
            focused = self._focus_whatsapp_window(timeout_sec=2.5)
            if not focused:
                time.sleep(gap_sec)
                continue

            try:
                active = gw.getActiveWindow()
                title = ((active.title if active else "") or "").lower()
                if "whatsapp" not in title and "chat" not in title:
                    time.sleep(gap_sec)
                    continue

                pyautogui.press("enter")
                time.sleep(0.25)

                pyautogui.hotkey("ctrl", "enter")
                time.sleep(0.25)

                sw, sh = pyautogui.size()
                pyautogui.click(int(sw * 0.965), int(sh * 0.945))
                time.sleep(0.15)
                pyautogui.press("enter")
                return True
            except Exception:
                time.sleep(gap_sec)

        return False

    # ---------- WHATSAPP ----------
    def _open_whatsapp_app_or_web(self) -> str:
        try:
            app_result = self.desktop.open_app("whatsapp")
            if isinstance(app_result, str) and "open failed" not in app_result.lower():
                return app_result
        except Exception:
            pass

        try:
            if platform.system().lower().startswith("win"):
                rc = subprocess.run(
                    ["cmd", "/c", "start", "", "whatsapp:"],
                    capture_output=True,
                    text=True,
                    timeout=8,
                    shell=False
                )
                if rc.returncode == 0:
                    return "Opened WhatsApp app."
        except Exception:
            pass

        try:
            if platform.system().lower().startswith("win"):
                rc = subprocess.run(
                    ["explorer.exe", r"shell:AppsFolder\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App"],
                    capture_output=True,
                    text=True,
                    timeout=8
                )
                if rc.returncode == 0:
                    return "Opened WhatsApp app."
        except Exception:
            pass

        ok = webbrowser.open("https://web.whatsapp.com/", new=2)
        return "Opened WhatsApp Web." if ok else "Couldn't open WhatsApp."

    def _open_whatsapp_to_number(self, number: str, message: str = "") -> str:
        n = re.sub(r"\D", "", number or "")
        if len(n) < 10:
            return "Invalid phone number."

        raw_msg = (message or "").strip()
        msg_q = urllib.parse.quote(raw_msg)

        opened = False
        deep_link = f"whatsapp://send?phone={n}&text={msg_q}"
        try:
            if platform.system().lower().startswith("win"):
                rc = subprocess.run(
                    ["cmd", "/c", "start", "", deep_link],
                    capture_output=True,
                    text=True,
                    timeout=8,
                    shell=False
                )
                opened = (rc.returncode == 0)
        except Exception:
            opened = False

        if not opened:
            try:
                res = self._open_whatsapp_app_or_web()
                opened = isinstance(res, str) and ("Opened WhatsApp" in res or "Opened WhatsApp app" in res)
            except Exception:
                opened = False

        if not opened:
            url = f"https://wa.me/{n}?text={msg_q}" if msg_q else f"https://wa.me/{n}"
            ok = webbrowser.open(url, new=2)
            if not ok:
                return "Couldn't open WhatsApp."
            time.sleep(3.0)
        else:
            time.sleep(2.8)

        try:
            self._focus_whatsapp_window(timeout_sec=6.0)
        except Exception:
            pass

        if raw_msg:
            try:
                pyautogui.write(raw_msg, interval=0.01)
                time.sleep(0.2)
            except Exception:
                pass

        try:
            sent = self._focus_lock_send_enter(tries=4, gap_sec=0.5)
            if sent:
                return "Opened WhatsApp chat and sent message."
        except Exception:
            pass

        return "Opened WhatsApp chat. Message typed; press Enter once if not sent."

    def _open_whatsapp_message(self, target_and_msg: str, memory=None) -> str:
        s = (target_and_msg or "").strip()
        if not s:
            return "Use: send whatsapp to <name/number> that <message>"

        msg = ""
        target = s

        low_s = s.lower()
        if " that " in low_s:
            i = low_s.find(" that ")
            target = s[:i].strip()
            msg = s[i + len(" that "):].strip()
        elif ":" in s:
            target, msg = [x.strip() for x in s.split(":", 1)]
        elif " - " in s:
            target, msg = [x.strip() for x in s.split(" - ", 1)]

        if not target:
            return "Missing contact name/number."

        digits = re.sub(r"\D", "", target)
        if len(digits) >= 10:
            return self._open_whatsapp_to_number(digits, msg)

        saved = self._get_contact_number(memory, target)
        if saved:
            return self._open_whatsapp_to_number(saved, msg)

        return (
            f"No number saved for '{target}'.\n"
            f"First run: save contact {target} = 91XXXXXXXXXX\n"
            f"Then run: send whatsapp to {target} that {msg or '<your message>'}"
        )

    # ---------- OPEN HELPERS ----------
    def _open_google_search(self, query: str) -> str:
        q = urllib.parse.quote_plus((query or "").strip())
        if not q:
            return "Please provide something to search."
        url = f"https://www.google.com/search?q={q}"
        ok = webbrowser.open(url, new=2)
        return "Opened Google search." if ok else "Couldn't open Google search."

    def _open_youtube_search(self, query: str = "") -> str:
        query = (query or "").strip()
        if query:
            q = urllib.parse.quote_plus(query)
            url = f"https://www.youtube.com/results?search_query={q}"
        else:
            url = "https://www.youtube.com/"
        ok = webbrowser.open(url, new=2)
        return "Opened YouTube." if ok else "Couldn't open YouTube."

    def _known_web_targets(self):
        return {
            "instagram": "https://www.instagram.com/",
            "facebook": "https://www.facebook.com/",
            "twitter": "https://x.com/",
            "x": "https://x.com/",
            "youtube": "https://www.youtube.com/",
            "gmail": "https://mail.google.com/",
            "google": "https://www.google.com/",
            "linkedin": "https://www.linkedin.com/",
            "whatsapp": "https://web.whatsapp.com/",
            "reddit": "https://www.reddit.com/",
            "github": "https://github.com/",
            "chatgpt": "https://chat.openai.com/",
            "netflix": "https://www.netflix.com/",
            "amazon": "https://www.amazon.in/",
        }

    def _open_known_web_target(self, name: str):
        key = self._normalize_for_match(name)
        url = self._known_web_targets().get(key)
        if not url:
            return None
        ok = webbrowser.open(url, new=2)
        return f"Opened {key} in browser." if ok else f"Couldn't open {key} in browser."

    def _open_app_or_web_fallback(self, name: str):
        name = (name or "").strip()
        if not name:
            return "Please provide app/site name."

        lname = self._normalize_for_match(name)

        if lname in {"whatsapp", "wa"}:
            return self._open_whatsapp_app_or_web()

        known = self._open_known_web_target(name)
        if known:
            return known

        app_result = self.desktop.open_app(name)
        if isinstance(app_result, str) and "open failed" not in app_result.lower():
            return app_result

        q = urllib.parse.quote_plus(name)
        url = f"https://www.google.com/search?q={q}"
        ok = webbrowser.open(url, new=2)
        if ok:
            return f"Couldn't open installed app '{name}', opened web search instead."
        return app_result if isinstance(app_result, str) else f"Couldn't open {name}."

    def _handle_open_intents(self, raw: str, low_norm: str, memory=None):
        if "whatsapp" in low_norm and "send message" in low_norm:
            m = re.search(r"send message(?:\s+to)?\s+(.+)$", raw, flags=re.IGNORECASE)
            if m:
                payload = m.group(1).strip()
                return self._open_whatsapp_message(payload, memory=memory)

        if low_norm in {"open whatsapp", "whatsapp open"}:
            return self._open_whatsapp_app_or_web()

        if low_norm.startswith("open google and search for "):
            query = raw[len("open google and search for "):].strip()
            return self._open_google_search(query)

        if low_norm.startswith("open google and search "):
            query = raw[len("open google and search "):].strip()
            return self._open_google_search(query)

        if low_norm.startswith("search google for "):
            query = raw[len("search google for "):].strip()
            return self._open_google_search(query)

        if low_norm.startswith("google search "):
            query = raw[len("google search "):].strip()
            return self._open_google_search(query)

        if low_norm.startswith("open youtube and search for "):
            query = raw[len("open youtube and search for "):].strip()
            return self._open_youtube_search(query)

        if low_norm.startswith("open youtube and search "):
            query = raw[len("open youtube and search "):].strip()
            return self._open_youtube_search(query)

        if low_norm.startswith("search youtube for "):
            query = raw[len("search youtube for "):].strip()
            return self._open_youtube_search(query)

        if low_norm in {"open youtube", "youtube open"}:
            return self._open_youtube_search("")

        if low_norm in {"open google", "google open"}:
            ok = webbrowser.open("https://www.google.com", new=2)
            return "Opened Google." if ok else "Couldn't open Google."

        return None

    async def try_execute(self, text: str, search, memory=None):
        raw = (text or "").strip()
        norm = self._normalize_for_match(raw)

        if not raw:
            return None

        # WhatsApp high priority
        if norm.startswith("send whatsapp to "):
            payload = raw[len("send whatsapp to "):].strip()
            return self._open_whatsapp_message(payload, memory=memory)

        m = re.search(r"^send message to (.+?) that (.+)$", raw, flags=re.IGNORECASE)
        if m:
            target = m.group(1).strip()
            msg = m.group(2).strip()
            return self._open_whatsapp_message(f"{target} that {msg}", memory=memory)

        if norm.startswith("send message to ") and "whatsapp" in norm:
            m2 = re.search(r"send message to (.+?) on whatsapp(?: that (.+))?$", raw, flags=re.IGNORECASE)
            if m2:
                target = (m2.group(1) or "").strip()
                msg = (m2.group(2) or "").strip()
                payload = f"{target} that {msg}" if msg else target
                return self._open_whatsapp_message(payload, memory=memory)

        m3 = re.search(r"^send .* to (.+?) on (?:my )?whatsapp(?: that (.+))?$", raw, flags=re.IGNORECASE)
        if m3:
            target = m3.group(1).strip()
            msg = (m3.group(2) or "").strip()
            payload = f"{target} that {msg}" if msg else target
            return self._open_whatsapp_message(payload, memory=memory)

        # Contact commands
        m = re.match(r"^save contact\s+(.+?)\s*=\s*(.+)$", raw, flags=re.IGNORECASE)
        if m:
            return self._set_contact_number(memory, m.group(1).strip(), m.group(2).strip())

        m = re.match(r"^remember\s+(.+?)\s+whatsapp\s+(.+)$", raw, flags=re.IGNORECASE)
        if m:
            return self._set_contact_number(memory, m.group(1).strip(), m.group(2).strip())

        m = re.match(r"^set whatsapp of\s+(.+?)\s+to\s+(.+)$", raw, flags=re.IGNORECASE)
        if m:
            return self._set_contact_number(memory, m.group(1).strip(), m.group(2).strip())

        m = re.match(r"^update contact\s+(.+?)\s*=\s*(.+)$", raw, flags=re.IGNORECASE)
        if m:
            return self._set_contact_number(memory, m.group(1).strip(), m.group(2).strip())

        if norm in {"list contacts", "list whatsapp contacts", "show contacts", "show whatsapp contacts"}:
            return self._list_contacts(memory)

        m = re.match(r"^delete contact\s+(.+)$", raw, flags=re.IGNORECASE)
        if m:
            return self._delete_contact(memory, m.group(1).strip())

        if norm in {"help", "commands"}:
            return self._help_text()

        tz_query = self._extract_time_location(norm)
        if tz_query is not None:
            return self._get_time_response(tz_query)

        if self._is_gold_query(norm):
            return self._get_gold_price_inr()

        city = self._extract_weather_city(raw)
        if city:
            return self._get_live_weather(city)

        if norm.startswith("search "):
            query = raw[7:].strip()
            results = await search.search(query, max_results=5)
            if not results:
                return "Search is temporarily unavailable right now. Please try again."
            lines = []
            for i, r in enumerate(results[:5], 1):
                lines.append(
                    f"{i}. {r.get('title', 'No title')}\n"
                    f"   {r.get('url', '')}\n"
                    f"   {r.get('snippet', '')}"
                )
            return "\n".join(lines)

        open_intent_result = self._handle_open_intents(raw, norm, memory=memory)
        if open_intent_result is not None:
            return open_intent_result

        if norm.startswith("open website "):
            return self.desktop.open_website(raw[len("open website "):].strip())

        if norm.startswith("open site "):
            return self.desktop.open_website(raw[len("open site "):].strip())

        if norm.startswith("go to "):
            return self.desktop.open_website(raw[len("go to "):].strip())

        if norm.startswith("open app "):
            target = raw[len("open app "):].strip()
            return self._open_app_or_web_fallback(target)

        if norm.startswith("open file "):
            return self.desktop.open_file(raw[len("open file "):].strip().strip('"'))

        if norm.startswith("open "):
            target = raw[len("open "):].strip()
            return self._open_app_or_web_fallback(target)

        if norm.startswith("type "):
            payload = raw[len("type "):]
            return {
                "requires_confirmation": True,
                "message": (
                    "About to type this text into the active window:\n\n"
                    f"{payload}\n\nProceed? (yes/no)"
                ),
                "pending_action": {"kind": "type_text", "payload": payload}
            }

        if norm.startswith("press "):
            hk = raw[len("press "):].strip()
            return {
                "requires_confirmation": True,
                "message": f"About to press hotkey: {hk}\nProceed? (yes/no)",
                "pending_action": {"kind": "press_hotkey", "payload": hk}
            }

        if norm.startswith("create file "):
            payload = raw[len("create file "):]
            if "|" not in payload:
                return "Use: create file <path> | <content>"
            path_str, content = [x.strip() for x in payload.split("|", 1)]
            path = Path(path_str)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return f"Created file: {path}"

        if norm.startswith("read file "):
            path = Path(raw[len("read file "):].strip())
            if not path.exists():
                return "File not found."
            return path.read_text(encoding="utf-8")[:4000]

        if norm.startswith("delete file "):
            target = raw[len("delete file "):].strip()
            return {
                "requires_confirmation": True,
                "message": f"Are you sure you want to delete '{target}'? (yes/no)",
                "pending_action": {"type": "delete_file", "target": target},
            }

        if norm.startswith("list files "):
            path = Path(raw[len("list files "):].strip())
            if not path.exists() or not path.is_dir():
                return "Directory not found."
            files = [p.name for p in path.iterdir()]
            return "\n".join(files[:300]) or "No files."

        if norm == "system status":
            vm = psutil.virtual_memory()
            du = psutil.disk_usage("/")
            batt = psutil.sensors_battery()
            batt_text = f"{batt.percent}%" if batt else "N/A"
            return (
                f"OS: {platform.system()} {platform.release()}\n"
                f"CPU: {psutil.cpu_percent()}%\n"
                f"RAM: {vm.percent}%\n"
                f"Disk: {du.percent}%\n"
                f"Battery: {batt_text}"
            )

        if norm.startswith("run "):
            cmd = raw[len("run "):].strip()
            return {
                "requires_confirmation": True,
                "message": f"Run system command '{cmd}' ? (yes/no)",
                "pending_action": {"type": "run_command", "target": cmd},
            }

        if memory is not None and self.config is not None:
            self._ensure_skills(memory, search)
            skill_res = await self._skills.handle(raw)
            if isinstance(skill_res, str):
                return skill_res

        return None

    async def execute_pending(self, pending_action, search):
        if not pending_action:
            return "No pending action."

        kind = pending_action.get("kind")
        payload = pending_action.get("payload", "")

        if kind == "type_text":
            return self.desktop.type_text(payload)

        if kind == "press_hotkey":
            keys = self.desktop.parse_hotkey(payload)
            if not keys:
                return "Invalid hotkey format. Example: ctrl+shift+t"
            return self.desktop.press_hotkey(*keys)

        atype = pending_action.get("type")
        target = pending_action.get("target", "")

        if atype == "delete_file":
            path = Path(target)
            if not path.exists():
                return "File not found."
            try:
                path.unlink()
                return f"Deleted: {path}"
            except Exception as e:
                return f"Delete failed: {e}"

        if atype == "run_command":
            try:
                try:
                    args = shlex.split(target)
                    result = subprocess.run(args, capture_output=True, text=True, timeout=20)
                except Exception:
                    result = subprocess.run(target, shell=True, capture_output=True, text=True, timeout=20)

                output = (result.stdout or result.stderr).strip()
                return f"Exit code: {result.returncode}\n{output[:3000]}"
            except Exception as e:
                return f"Command failed: {e}"

        return "Unknown pending action."

    # ---------- TIME ----------
    def _extract_time_location(self, t: str):
        local_keys = {"time", "what is the time", "what's the time", "current time", "time now", "local time"}
        if t in local_keys:
            return "LOCAL"

        m = re.search(r"\btime in ([a-zA-Z\s/_-]+)\b", t)
        if m:
            return m.group(1).strip()

        m2 = re.search(r"\bcurrent time in ([a-zA-Z\s/_-]+)\b", t)
        if m2:
            return m2.group(1).strip()

        return None

    def _get_time_response(self, location: str) -> str:
        try:
            if location == "LOCAL":
                now = datetime.now()
                return now.strftime("Local time: %Y-%m-%d %I:%M:%S %p")

            q = location.lower().strip()
            tz_name = location if "/" in location else self.city_tz.get(q)

            if not tz_name:
                return (
                    f"I don't know timezone mapping for '{location}' yet.\n"
                    "Try format: time in Europe/London or time in Asia/Kolkata."
                )

            now_tz = datetime.now(ZoneInfo(tz_name))
            return now_tz.strftime(f"Current time in {location.title()} ({tz_name}): %Y-%m-%d %I:%M:%S %p")
        except Exception as e:
            return f"Time lookup failed: {e}"

    # ---------- GOLD ----------
    def _is_gold_query(self, t: str) -> bool:
        keys = ["gold price", "price of gold", "gold rate", "live gold price", "today gold price"]
        return any(k in t for k in keys)

    def _get_gold_price_inr(self) -> str:
        try:
            g = requests.get("https://api.gold-api.com/price/XAU", timeout=12)
            if g.status_code != 200:
                return f"Gold API error ({g.status_code})."

            gd = g.json()
            usd_per_ounce = gd.get("price")
            if not usd_per_ounce:
                return "Gold price unavailable right now."

            inr_rate = None
            for url in [
                "https://open.er-api.com/v6/latest/USD",
                "https://api.exchangerate-api.com/v4/latest/USD",
                "https://api.frankfurter.app/latest?from=USD&to=INR",
            ]:
                try:
                    r = requests.get(url, timeout=10)
                    if r.status_code != 200:
                        continue
                    data = r.json()
                    rate = data.get("rates", {}).get("INR")
                    if rate:
                        inr_rate = float(rate)
                        break
                except Exception:
                    continue

            if not inr_rate:
                return f"Gold (USD/oz): ${float(usd_per_ounce):.2f}\nINR conversion rate unavailable."

            inr_per_ounce = float(usd_per_ounce) * inr_rate
            inr_per_gram = inr_per_ounce / 31.1034768

            return (
                "Live Gold (approx)\n"
                f"- XAU/USD (per troy ounce): ${float(usd_per_ounce):.2f}\n"
                f"- USD/INR: {inr_rate:.4f}\n"
                f"- Gold per gram (INR): Rs {inr_per_gram:,.2f}\n"
                f"- Gold per 10g (INR): Rs {(inr_per_gram * 10):,.2f}"
            )
        except Exception as e:
            return f"Gold price fetch failed: {e}"

    # ---------- WEATHER ----------
    def _extract_weather_city(self, text: str):
        t = text.lower().strip()
        t = re.sub(r"[?.,!]", "", t)

        patterns = [
            r"^weather in (.+)$",
            r"^what is the weather in (.+)$",
            r"^current weather in (.+)$",
            r"^temperature in (.+)$",
        ]
        for p in patterns:
            m = re.match(p, t)
            if m:
                return m.group(1).strip()
        return None

    def _get_live_weather(self, city: str) -> str:
        if not self.openweather_api_key:
            return "OPENWEATHER_API_KEY missing in .env"

        try:
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {"q": city, "appid": self.openweather_api_key, "units": "metric"}
            r = requests.get(url, params=params, timeout=10)

            if r.status_code == 404:
                return f"City '{city}' not found."
            if r.status_code != 200:
                return f"Weather API error ({r.status_code})."

            d = r.json()
            name = d.get("name", city.title())
            country = d.get("sys", {}).get("country", "")
            desc = d.get("weather", [{}])[0].get("description", "N/A")
            temp = d.get("main", {}).get("temp", "N/A")
            feels = d.get("main", {}).get("feels_like", "N/A")

            return (
                f"Weather in {name}, {country}\n"
                f"- Condition: {desc}\n"
                f"- Temperature: {temp} C\n"
                f"- Feels like: {feels} C"
            )
        except Exception as e:
            return f"Weather fetch failed: {e}"

    def _help_text(self):
        return (
            "EDITH commands:\n"
            "- help / commands\n"
            "- what is the time\n"
            "- time in <city> (e.g., time in london)\n"
            "- time in <Region/City> (e.g., time in Europe/London)\n"
            "- weather in <city>\n"
            "- gold price\n"
            "- search <query>\n"
            "- open google\n"
            "- open google and search for <query>\n"
            "- search google for <query>\n"
            "- open youtube\n"
            "- open youtube and search for <query>\n"
            "- search youtube for <query>\n"
            "- open whatsapp\n"
            "- save contact <name> = <number_with_country_code>\n"
            "- remember <name> whatsapp <number>\n"
            "- set whatsapp of <name> to <number>\n"
            "- update contact <name> = <number>\n"
            "- list contacts\n"
            "- delete contact <name>\n"
            "- send whatsapp to <name/number> that <message>\n"
            "- send message to <name> that <message>\n"
            "- send <anything> to <name> on my whatsapp [that <message>]\n"
            "- open whatsapp and send message to <name/number> that <message>\n"
            "- open instagram / facebook / twitter / linkedin ...\n"
            "- system status\n"
            "- open website <url>\n"
            "- open site <url>\n"
            "- go to <url>\n"
            "- open app <name>\n"
            "- open <name>\n"
            "- open file <path>\n"
            "- create file <path> | <content>\n"
            "- read file <path>\n"
            "- list files <dir>\n"
            "- delete file <path> (confirm)\n"
            "- run <command> (confirm)\n"
            "- type <text> (confirm)\n"
            "- press <hotkey> (confirm)\n"
            "- connect gmail\n"
            "- connect outlook\n"
            "- draft email to <person> about <topic>\n"
            "- send last draft\n"
            "- send email to <to> subject <sub> body <body> provider gmail|outlook\n"
            "- summarize meeting: <notes>\n"
            "- daily brief"
        )
    