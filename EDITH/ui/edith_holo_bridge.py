import os
import re
import time
import asyncio
import threading
from datetime import datetime, timedelta
from types import SimpleNamespace

import psutil
from PySide6.QtCore import QObject, Signal, Slot, QTimer
from dotenv import load_dotenv

from core.orchestrator import Orchestrator
from nlp.stt import listen_once

try:
    from plyer import notification
except Exception:
    notification = None

load_dotenv()


class EdithBackend(QObject):
    pushEvent = Signal(str)
    statusChanged = Signal(str)
    telemetry = Signal(int, int, int, str)
    bootLine = Signal(str)
    bootDone = Signal()

    def __init__(self):
        super().__init__()

        cfg = SimpleNamespace(
            DB_PATH="edith.db",
            OPENROUTER_API_KEY=os.getenv("OPENROUTER_API_KEY", ""),
            OPENWEATHER_API_KEY=os.getenv("OPENWEATHER_API_KEY", ""),
            BING_API_KEY=os.getenv("BING_API_KEY", ""),
            BING_ENDPOINT=os.getenv("BING_ENDPOINT", ""),
            ENABLE_TTS=True,
        )
        self.orchestrator = Orchestrator(cfg)

        self._last_clock = "--:--:--"
        self._voice_enabled = False
        self._mode = "wake"

        # pack-1
        self._wake_running = False
        self._wake_thread = None
        self._reminders = []  # [{"when": datetime, "text": str, "done": bool}]

        self._boot_lines = [
            "[CORE] Initializing EDITH neural kernel...",
            "[AUDIO] Microphone interface check...",
            "[NLP] Intent parser online...",
            "[NET] Secure channels established...",
            "[UI] Holographic pipeline stable...",
            "[OK] EDITH ready.",
        ]
        self._boot_idx = 0
        self._boot_timer = QTimer(self)
        self._boot_timer.timeout.connect(self._emit_boot)
        self._boot_timer.start(320)

        # real telemetry
        self._tele_timer = QTimer(self)
        self._tele_timer.timeout.connect(self._tick_telemetry)
        self._tele_timer.start(1000)

        # reminder checker
        self._rem_timer = QTimer(self)
        self._rem_timer.timeout.connect(self._check_reminders)
        self._rem_timer.start(1000)

        self.statusChanged.emit("booting")

    # ---------------- boot ----------------
    def _emit_boot(self):
        if self._boot_idx < len(self._boot_lines):
            self.bootLine.emit(self._boot_lines[self._boot_idx])
            self._boot_idx += 1
        else:
            self._boot_timer.stop()
            self.bootDone.emit()
            self.pushEvent.emit("EDITH: Holographic interface online.")
            self.statusChanged.emit("ready")

            # startup greeting
            greeting = "Hi, all systems are running good. EDITH is online and ready to assist you."
            self.pushEvent.emit(f"EDITH: {greeting}")
            self._speak_text(greeting)

    # ---------------- tts helper ----------------
    def _speak_text(self, text: str):
        try:
            if hasattr(self.orchestrator, "tts") and self.orchestrator.tts:
                if hasattr(self.orchestrator.tts, "speak"):
                    self.orchestrator.tts.speak(text)
                elif hasattr(self.orchestrator.tts, "say"):
                    self.orchestrator.tts.say(text)
        except Exception:
            pass

    # ---------------- telemetry (real) ----------------
    def _tick_telemetry(self):
        try:
            cpu = int(psutil.cpu_percent(interval=None))
            net_io = psutil.net_io_counters()
            # simple normalized net activity heuristic
            net = int(min(100, (net_io.bytes_sent + net_io.bytes_recv) % 100))
            mic = 0  # optional: wire real mic rms later
            self.telemetry.emit(cpu, net, mic, self._last_clock)
        except Exception:
            self.telemetry.emit(0, 0, 0, self._last_clock)

    # ---------------- reminder engine ----------------
    def _check_reminders(self):
        now = datetime.now()
        for r in self._reminders:
            if (not r["done"]) and now >= r["when"]:
                r["done"] = True
                msg = f"Reminder: {r['text']}"
                self.pushEvent.emit(f"EDITH: {msg}")
                self.statusChanged.emit("reminder")
                self._speak_text(msg)

                if notification:
                    try:
                        notification.notify(
                            title="EDITH Reminder",
                            message=r["text"],
                            app_name="EDITH",
                            timeout=8
                        )
                    except Exception:
                        pass

    def _try_parse_reminder(self, text: str):
        # examples:
        # "remind me in 10 minutes to drink water"
        # "remind me in 30 seconds to stand up"
        low = text.lower().strip()
        m = re.match(r"^remind me in (\d+)\s*(second|seconds|minute|minutes|hour|hours)\s+to\s+(.+)$", low)
        if not m:
            return None

        num = int(m.group(1))
        unit = m.group(2)
        what = m.group(3).strip()

        delta = timedelta(seconds=num)
        if "minute" in unit:
            delta = timedelta(minutes=num)
        elif "hour" in unit:
            delta = timedelta(hours=num)

        when = datetime.now() + delta
        self._reminders.append({"when": when, "text": what, "done": False})
        return f"Reminder set for {num} {unit}: {what}"

    # ---------------- wake listener ----------------
    def _wake_loop(self):
        self.pushEvent.emit("EDITH: Wake listener started. Say 'edith ...'")
        while self._wake_running:
            try:
                heard = (listen_once(timeout=4, phrase_time_limit=6) or "").strip()
                if not heard:
                    continue

                low = heard.lower()
                if not low.startswith("edith"):
                    continue

                cmd = heard[5:].strip(" ,.:;!-")
                if not cmd:
                    self.pushEvent.emit("EDITH: Yes?")
                    self._speak_text("Yes?")
                    continue

                self.pushEvent.emit(f"YOU (wake): {cmd}")
                self.statusChanged.emit("processing")
                out = asyncio.run(self.orchestrator.handle(cmd))
                self.pushEvent.emit(f"EDITH: {out}")
                self.statusChanged.emit("ready")

            except Exception:
                # keep loop alive
                time.sleep(0.3)

        self.pushEvent.emit("EDITH: Wake listener stopped.")

    @Slot()
    def toggleWake(self):
        self._wake_running = not self._wake_running
        if self._wake_running:
            self.statusChanged.emit("wake-on")
            self._wake_thread = threading.Thread(target=self._wake_loop, daemon=True)
            self._wake_thread.start()
        else:
            self.statusChanged.emit("wake-off")

    # ---------------- commands ----------------
    @Slot(str)
    def sendCommand(self, text: str):
        try:
            text = (text or "").strip()
            if not text:
                return

            self.pushEvent.emit(f"YOU: {text}")

            # reminder fast-path
            rem_msg = self._try_parse_reminder(text)
            if rem_msg:
                self.pushEvent.emit(f"EDITH: {rem_msg}")
                self.statusChanged.emit("ready")
                return

            self.statusChanged.emit("processing")
            threading.Thread(target=self._worker, args=(text,), daemon=True).start()
        except Exception as e:
            self.pushEvent.emit(f"EDITH UI ERROR: {e}")
            self.statusChanged.emit("error")

    def _worker(self, text: str):
        try:
            out = asyncio.run(self.orchestrator.handle(text))
            self.pushEvent.emit(f"EDITH: {out}")
            self.statusChanged.emit("ready")
        except Exception as e:
            self.pushEvent.emit(f"EDITH ERROR: {type(e).__name__}: {e}")
            self.statusChanged.emit("error")

    @Slot()
    def micOnce(self):
        self.statusChanged.emit("listening")
        self.pushEvent.emit("EDITH: Listening... speak now.")

        def _mic_worker():
            try:
                heard = (listen_once(timeout=12, phrase_time_limit=18) or "").strip()
                if not heard:
                    self.pushEvent.emit("EDITH: I didn't catch that. Try again.")
                    self.statusChanged.emit("ready")
                    return
                self.sendCommand(heard)
            except Exception as e:
                msg = str(e).lower()
                if "timeout" in msg or "no speech" in msg:
                    self.pushEvent.emit("EDITH: No speech detected. Mic ready.")
                    self.statusChanged.emit("ready")
                else:
                    self.pushEvent.emit(f"EDITH MIC ERROR: {e}")
                    self.statusChanged.emit("error")

        threading.Thread(target=_mic_worker, daemon=True).start()

    @Slot()
    def stopSpeech(self):
        try:
            if hasattr(self.orchestrator, "tts") and self.orchestrator.tts:
                self.orchestrator.tts.stop()
            self.pushEvent.emit("EDITH: Speech stopped.")
            self.statusChanged.emit("stopped")
        except Exception as e:
            self.pushEvent.emit(f"EDITH STOP ERROR: {e}")
            self.statusChanged.emit("error")

    @Slot()
    def toggleVoice(self):
        self._voice_enabled = not self._voice_enabled
        self.pushEvent.emit(f"EDITH: Voice {'enabled' if self._voice_enabled else 'disabled'}.")
        self.statusChanged.emit("ready")

    @Slot()
    def toggleMode(self):
        self._mode = "dictation" if self._mode == "wake" else "wake"
        self.pushEvent.emit(f"EDITH: Mode switched to {self._mode}.")
        self.statusChanged.emit("ready")

    @Slot()
    def clearChat(self):
        self.pushEvent.emit("##CLEAR##")

    @Slot(str)
    def pushClock(self, t: str):
        self._last_clock = t
