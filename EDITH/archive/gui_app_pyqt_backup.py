import asyncio
import re

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QTextCursor, QColor, QDesktopServices
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel
)

URL_RE = re.compile(r"(https?://[^\s]+)")


class Worker(QThread):
    done = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, orchestrator, text: str):
        super().__init__()
        self.orchestrator = orchestrator
        self.text = text

    def run(self):
        try:
            res = asyncio.run(self.orchestrator.handle(self.text))
            self.done.emit(res)
        except Exception as e:
            self.failed.emit(str(e))


class EdithWindow(QMainWindow):
    def __init__(self, orchestrator):
        super().__init__()
        self.orchestrator = orchestrator
        self.worker = None

        self.setWindowTitle("EDITH Assistant (PyQt)")
        self.resize(980, 680)

        self._build_ui()
        self._refresh_status()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------
    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(8)

        # Top chips
        top = QHBoxLayout()
        self.title_lbl = QLabel("EDITH • Assistant")
        self.mode_lbl = QLabel("mode: assistant")
        self.voice_lbl = QLabel("voice: on")
        self.speaking_lbl = QLabel("speaking: idle")

        for w in [self.title_lbl, self.mode_lbl, self.voice_lbl, self.speaking_lbl]:
            w.setStyleSheet("padding:6px 10px; background:#1f2937; color:#e5e7eb; border-radius:8px;")
            top.addWidget(w)

        top.addStretch(1)
        outer.addLayout(top)

        # Chat box
        self.chat = QTextEdit()
        self.chat.setReadOnly(True)
        self.chat.setOpenExternalLinks(False)
        self.chat.setStyleSheet(
            "QTextEdit {background:#0f1115; color:#e5e7eb; font-size:14px; border:1px solid #1f2937;}"
        )
        self.chat.anchorClicked.connect(self._open_link)
        outer.addWidget(self.chat, stretch=1)

        # Input row
        row = QHBoxLayout()
        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Type your message...")
        self.entry.returnPressed.connect(self._on_send)
        self.entry.setStyleSheet(
            "QLineEdit {background:#111827; color:#f3f4f6; padding:10px; border:1px solid #374151;}"
        )

        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self._on_send)
        self.send_btn.setStyleSheet("QPushButton {padding:10px 14px;}")

        row.addWidget(self.entry, stretch=1)
        row.addWidget(self.send_btn)
        outer.addLayout(row)

        self.status_lbl = QLabel("Ready.")
        self.status_lbl.setStyleSheet("color:#9ca3af; padding:4px;")
        outer.addWidget(self.status_lbl)

    # ------------------------------------------------------------------
    # Chat render
    # ------------------------------------------------------------------
    def _append(self, prefix: str, text: str, color: str):
        self.chat.moveCursor(QTextCursor.MoveOperation.End)

        # Prefix
        self.chat.setTextColor(QColor(color))
        self.chat.insertPlainText(f"{prefix}: ")

        # Message (with URL link formatting via HTML)
        self.chat.setTextColor(QColor("#e5e7eb"))
        html = self._linkify(text).replace("\n", "<br>")
        self.chat.insertHtml(html)
        self.chat.insertPlainText("\n\n")

        self.chat.moveCursor(QTextCursor.MoveOperation.End)

    def _linkify(self, text: str) -> str:
        def repl(m):
            u = m.group(1)
            return f'<a href="{u}" style="color:#60a5fa;">{u}</a>'
        return URL_RE.sub(repl, text)

    def _open_link(self, url: QUrl):
        QDesktopServices.openUrl(url)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------
    def _on_send(self):
        text = self.entry.text().strip()
        if not text:
            return

        self.entry.clear()
        self._append("You", text, "#93c5fd")
        self.status_lbl.setText("Thinking...")
        self.send_btn.setEnabled(False)

        self.worker = Worker(self.orchestrator, text)
        self.worker.done.connect(self._on_done)
        self.worker.failed.connect(self._on_failed)
        self.worker.start()

    def _on_done(self, result: str):
        self._append("EDITH", result, "#86efac")
        self.status_lbl.setText("Ready.")
        self.send_btn.setEnabled(True)
        self._refresh_status()

    def _on_failed(self, err: str):
        self._append("EDITH", f"Error: {err}", "#fca5a5")
        self.status_lbl.setText("Ready.")
        self.send_btn.setEnabled(True)
        self._refresh_status()

    # ------------------------------------------------------------------
    # Status chips
    # ------------------------------------------------------------------
    def _refresh_status(self):
        mode = getattr(self.orchestrator, "mode", "assistant")
        tts_obj = getattr(self.orchestrator, "tts", None)
        voice_on = getattr(tts_obj, "enabled", True) if tts_obj else False
        speaking = tts_obj.is_speaking() if tts_obj else False

        self.mode_lbl.setText(f"mode: {mode}")
        self.voice_lbl.setText(f"voice: {'on' if voice_on else 'off'}")
        self.speaking_lbl.setText(f"speaking: {'live' if speaking else 'idle'}")