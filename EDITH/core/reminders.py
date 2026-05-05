"""
Feature 1: Reminder System for EDITH-AI
========================================
Commands:
  remind me to <task> in <N> minutes
  remind me to <task> in <N> hours
  remind me to <task> in <N> seconds
  list reminders
  clear reminders
"""

import threading
import time
import re
from datetime import datetime
from typing import Callable, List, Dict, Optional


class ReminderManager:
    """Thread-based reminder system that calls a callback when a reminder fires."""

    def __init__(self, on_remind: Optional[Callable[[str], None]] = None):
        """
        on_remind: called with the reminder message when a reminder fires.
                   Defaults to printing to stdout if None.
        """
        self._on_remind = on_remind or (lambda msg: print(f"\n⏰ REMINDER: {msg}\n"))
        self._reminders: List[Dict] = []   # {id, task, fire_at, thread}
        self._lock = threading.Lock()
        self._id_counter = 0

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def handle(self, text: str) -> Optional[str]:
        """Return a response string if this module handles the command, else None."""
        raw = (text or "").strip()
        low = raw.lower()

        # --- Set reminder ---
        for prefix in ("remind me to ", "set reminder to ", "reminder ", "remind "):
            if low.startswith(prefix):
                payload = raw[len(prefix):].strip()
                return self._parse_and_set(payload)

        if low in {"list reminders", "show reminders", "my reminders"}:
            return self._list_reminders()

        if low in {"clear reminders", "cancel reminders", "delete reminders",
                   "remove all reminders"}:
            return self._clear_reminders()

        return None

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse_and_set(self, payload: str) -> str:
        """
        Parse:  '<task> in <N> minutes|hours|seconds'
        Or:     '<task> after <N> minutes|hours|seconds'
        """
        m = re.search(
            r"\bin\s+(\d+(?:\.\d+)?)\s*(second|seconds|sec|secs|minute|minutes|min|mins|hour|hours|hr|hrs)\b",
            payload,
            re.IGNORECASE,
        )
        if not m:
            m = re.search(
                r"\bafter\s+(\d+(?:\.\d+)?)\s*(second|seconds|sec|secs|minute|minutes|min|mins|hour|hours|hr|hrs)\b",
                payload,
                re.IGNORECASE,
            )

        if not m:
            return (
                "Could not parse reminder time. Try:\n"
                "  remind me to take medicine in 30 minutes\n"
                "  remind me to call mom in 2 hours"
            )

        value = float(m.group(1))
        unit = m.group(2).lower()

        if unit in {"second", "seconds", "sec", "secs"}:
            delay_sec = value
        elif unit in {"minute", "minutes", "min", "mins"}:
            delay_sec = value * 60
        else:
            delay_sec = value * 3600

        # The task description is everything before the 'in/after' keyword
        task = payload[: m.start()].strip()
        if not task:
            task = "your reminder"

        return self._set(task, delay_sec)

    # ------------------------------------------------------------------
    # Core helpers
    # ------------------------------------------------------------------

    def _set(self, task: str, delay_sec: float) -> str:
        with self._lock:
            self._id_counter += 1
            rid = self._id_counter

        fire_at = time.time() + delay_sec

        def _fire():
            time.sleep(delay_sec)
            now_str = datetime.now().strftime("%I:%M %p")
            self._on_remind(f"[{now_str}] {task}")
            with self._lock:
                self._reminders = [r for r in self._reminders if r["id"] != rid]

        t = threading.Thread(target=_fire, daemon=True)
        t.start()

        with self._lock:
            self._reminders.append({
                "id": rid,
                "task": task,
                "fire_at": fire_at,
                "thread": t,
            })

        mins = int(delay_sec // 60)
        secs = int(delay_sec % 60)
        if mins >= 60:
            hrs = mins // 60
            remaining_mins = mins % 60
            time_label = f"{hrs}h {remaining_mins}m" if remaining_mins else f"{hrs}h"
        elif mins > 0:
            time_label = f"{mins}m {secs}s" if secs else f"{mins}m"
        else:
            time_label = f"{secs}s"

        return f"⏰ Reminder set! I'll remind you to '{task}' in {time_label}."

    def _list_reminders(self) -> str:
        with self._lock:
            active = list(self._reminders)

        if not active:
            return "No active reminders."

        lines = ["Active reminders:"]
        now = time.time()
        for r in active:
            remaining = max(0, r["fire_at"] - now)
            mins = int(remaining // 60)
            secs = int(remaining % 60)
            if mins >= 60:
                hrs = mins // 60
                remaining_mins = mins % 60
                label = f"{hrs}h {remaining_mins}m" if remaining_mins else f"{hrs}h"
            elif mins > 0:
                label = f"{mins}m {secs}s"
            else:
                label = f"{secs}s"
            lines.append(f"  • [{r['id']}] {r['task']} — fires in {label}")

        return "\n".join(lines)

    def _clear_reminders(self) -> str:
        with self._lock:
            count = len(self._reminders)
            self._reminders.clear()
        return f"Cleared {count} reminder(s)." if count else "No reminders to clear."
