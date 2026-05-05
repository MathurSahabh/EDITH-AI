"""
Feature 2: Clipboard Manager for EDITH-AI
==========================================
Commands:
  copy <text>              — copy text to clipboard
  show clipboard           — show current clipboard content
  what is in clipboard     — same as above
  clipboard history        — show last 10 clipboard items
  clear clipboard          — clear the clipboard and history
"""

import threading
from typing import List, Optional

try:
    import pyperclip
    _PYPERCLIP = True
except ImportError:
    _PYPERCLIP = False


class ClipboardManager:
    """
    Manages clipboard read/write and keeps a local history of the last 10
    items copied through EDITH.
    """

    MAX_HISTORY = 10

    def __init__(self):
        self._history: List[str] = []
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def handle(self, text: str) -> Optional[str]:
        """Return a response string if this module handles the command, else None."""
        raw = (text or "").strip()
        low = raw.lower()

        # --- Copy ---
        if low.startswith("copy "):
            content = raw[len("copy "):].strip()
            return self._copy(content)

        # --- Show clipboard ---
        if low in {
            "show clipboard", "clipboard", "what is in clipboard",
            "what's in clipboard", "clipboard content", "read clipboard",
            "paste clipboard", "show my clipboard",
        }:
            return self._show()

        # --- History ---
        if low in {"clipboard history", "show clipboard history", "my clipboard history"}:
            return self._history_view()

        # --- Clear ---
        if low in {"clear clipboard", "reset clipboard", "empty clipboard", "wipe clipboard"}:
            return self._clear()

        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _copy(self, content: str) -> str:
        if not content:
            return "Nothing to copy. Use: copy <your text>"

        if not _PYPERCLIP:
            return "pyperclip is not installed. Run: pip install pyperclip"

        try:
            pyperclip.copy(content)
        except Exception as e:
            return f"Clipboard write failed: {e}"

        with self._lock:
            if not self._history or self._history[-1] != content:
                self._history.append(content)
                if len(self._history) > self.MAX_HISTORY:
                    self._history.pop(0)

        preview = (content[:60] + "...") if len(content) > 60 else content
        return f"Copied to clipboard: \"{preview}\""

    def _show(self) -> str:
        if not _PYPERCLIP:
            return "pyperclip is not installed. Run: pip install pyperclip"

        try:
            content = pyperclip.paste()
        except Exception as e:
            return f"Clipboard read failed: {e}"

        if not content:
            return "Clipboard is empty."

        preview = content if len(content) <= 500 else content[:500] + "\n... (truncated)"
        return f"Clipboard content:\n{preview}"

    def _history_view(self) -> str:
        with self._lock:
            items = list(self._history)

        if not items:
            return "Clipboard history is empty."

        lines = ["Clipboard history (most recent last):"]
        for i, item in enumerate(reversed(items), 1):
            preview = (item[:80] + "...") if len(item) > 80 else item
            lines.append(f"  {i}. {preview}")

        return "\n".join(lines)

    def _clear(self) -> str:
        if _PYPERCLIP:
            try:
                pyperclip.copy("")
            except Exception:
                pass

        with self._lock:
            count = len(self._history)
            self._history.clear()

        return f"Clipboard cleared ({count} history item(s) removed)."
