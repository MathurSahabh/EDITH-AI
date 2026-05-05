import sys
import math
import asyncio
import threading
from datetime import datetime
from types import SimpleNamespace
import os

from PySide6.QtCore import Qt, QTimer, QRectF, Signal, QObject
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QFrame, QLabel, QTextEdit, QPushButton,
    QHBoxLayout, QVBoxLayout, QGridLayout, QProgressBar
)

from dotenv import load_dotenv
load_dotenv()

from core.orchestrator import Orchestrator


# -------------------- Bridge for thread-safe UI updates --------------------
class Bridge(QObject):
    assistant_text = Signal(str)
    user_text = Signal(str)
    status_text = Signal(str)
    telemetry = Signal(int, int, int)  # cpu, net, mic


# -------------------- Animated HUD Radar --------------------
class HudRadar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle = 0
        self.pulse = 0
        self.setMinimumSize(360, 360)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(33)

    def tick(self):
        self.angle = (self.angle + 2) % 360
        self.pulse = (self.pulse + 1) % 100
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.fillRect(self.rect(), QColor(6, 12, 22))

        w = self.width()
        h = self.height()
        cx, cy = w / 2, h / 2
        r = min(w, h) * 0.42

        # glow rings
        for i, a in enumerate([0.95, 0.65, 0.45, 0.28]):
            pen = QPen(QColor(80, 190, 255, int(255 * a)))
            pen.setWidth(2 if i == 0 else 1)
            p.setPen(pen)
            rr = r - i * 28
            p.drawEllipse(QRectF(cx - rr, cy - rr, rr * 2, rr * 2))

        # segmented ticks
        for i in range(72):
            ang = math.radians(i * 5)
            x1 = cx + (r - 8) * math.cos(ang)
            y1 = cy + (r - 8) * math.sin(ang)
            x2 = cx + (r + 2) * math.cos(ang)
            y2 = cy + (r + 2) * math.sin(ang)
            col = QColor(90, 210, 255, 180 if i % 3 == 0 else 90)
            p.setPen(QPen(col, 1))
            p.drawLine(int(x1), int(y1), int(x2), int(y2))

        # rotating sweep
        sweep_ang = math.radians(self.angle)
        x = cx + (r - 22) * math.cos(sweep_ang)
        y = cy + (r - 22) * math.sin(sweep_ang)
        p.setPen(QPen(QColor(130, 240, 255, 220), 3))
        p.drawLine(int(cx), int(cy), int(x), int(y))

        # pulse ring
        pr = 40 + (self.pulse % 60)
        alpha = max(0, 180 - self.pulse * 2)
        p.setPen(QPen(QColor(130, 220, 255, alpha), 2))
        p.drawEllipse(QRectF(cx - pr, cy - pr, pr * 2, pr * 2))

        # center core
        p.setPen(QPen(QColor(120, 220, 255), 2))
        p.setBrush(QColor(20, 70, 110))
        p.drawEllipse(QRectF(cx - 18, cy - 18, 36, 36))

        p.setPen(QColor(170, 235, 255))
        p.setFont(QFont("Consolas", 10, QFont.Bold))
        p.drawText(int(cx - 22), int(cy + r + 24), "EDITH CORE ONLINE")


# -------------------- Main Window --------------------
class EdithHudWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EDITH • Futuristic HUD")
        self.resize(1400, 860)

        cfg = SimpleNamespace(
            DB_PATH="edith.db",
            OPENAI_API_KEY=os.getenv("OPENAI_API_KEY", ""),
            OPENWEATHER_API_KEY=os.getenv("OPENWEATHER_API_KEY", ""),
            BING_API_KEY=os.getenv("BING_API_KEY", ""),
            BING_ENDPOINT=os.getenv("BING_ENDPOINT", ""),
            ENABLE_TTS=True,
        )
        self.orchestrator = Orchestrator(cfg)

        self.bridge = Bridge()
        self.bridge.assistant_text.connect(self.add_assistant_text)
        self.bridge.user_text.connect(self.add_user_text)
        self.bridge.status_text.connect(self.set_status)
        self.bridge.telemetry.connect(self.update_telemetry)

        self._build_ui()
        self._start_fake_telemetry()

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)

        main = QGridLayout(root)
        main.setContentsMargins(10, 10, 10, 10)
        main.setHorizontalSpacing(10)
        main.setVerticalSpacing(10)

        # ---------- Left panel ----------
        left = QFrame()
        left.setObjectName("panel")
        left_l = QVBoxLayout(left)

        title = QLabel("EDITH")
        title.setObjectName("title")
        left_l.addWidget(title)

        sub = QLabel("TACTICAL TELEMETRY")
        sub.setObjectName("sub")
        left_l.addWidget(sub)

        self.cpu = self._bar("CPU")
        self.net = self._bar("NET")
        self.mic = self._bar("MIC")

        left_l.addLayout(self.cpu["layout"])
        left_l.addLayout(self.net["layout"])
        left_l.addLayout(self.mic["layout"])
        left_l.addStretch(1)

        # ---------- Center panel ----------
        center = QFrame()
        center.setObjectName("panel")
        center_l = QVBoxLayout(center)

        head = QLabel("EDITH // ADVANCED CONTROL MATRIX")
        head.setObjectName("head")
        center_l.addWidget(head)

        self.radar = HudRadar()
        center_l.addWidget(self.radar, 1)

        # ---------- Right panel ----------
        right = QFrame()
        right.setObjectName("panel")
        right_l = QVBoxLayout(right)

        logs_title = QLabel("EVENT STREAM")
        logs_title.setObjectName("sub")
        right_l.addWidget(logs_title)

        self.logs = QTextEdit()
        self.logs.setReadOnly(True)
        self.logs.setObjectName("logs")
        right_l.addWidget(self.logs, 1)

        # ---------- Bottom command ----------
        bottom = QFrame()
        bottom.setObjectName("panel")
        b = QHBoxLayout(bottom)

        self.input = QTextEdit()
        self.input.setObjectName("input")
        self.input.setFixedHeight(74)
        self.input.setPlaceholderText("Type command for EDITH...")
        b.addWidget(self.input, 1)

        btn_col = QVBoxLayout()
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.on_send)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.on_stop)
        btn_col.addWidget(self.send_btn)
        btn_col.addWidget(self.stop_btn)
        btn_col.addStretch(1)
        b.addLayout(btn_col)

        self.status = QLabel("READY")
        self.status.setObjectName("status")
        b.addWidget(self.status)

        # layout placement
        main.addWidget(left, 0, 0, 1, 1)
        main.addWidget(center, 0, 1, 1, 2)
        main.addWidget(right, 0, 3, 1, 1)
        main.addWidget(bottom, 1, 0, 1, 4)

        main.setColumnStretch(0, 1)
        main.setColumnStretch(1, 2)
        main.setColumnStretch(2, 2)
        main.setColumnStretch(3, 1)
        main.setRowStretch(0, 1)
        main.setRowStretch(1, 0)

        self.setStyleSheet("""
        QMainWindow { background: #070c16; }
        QFrame#panel {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #0a1222, stop:1 #0a182d);
            border: 1px solid #1d4361;
            border-radius: 12px;
        }
        QLabel#title { color: #9ddfff; font: 700 44px 'Segoe UI'; }
        QLabel#sub { color: #73c8f5; font: 700 12px 'Consolas'; letter-spacing: 1px; }
        QLabel#head { color: #c7edff; font: 700 26px 'Segoe UI'; padding: 4px 0 8px 4px; }
        QLabel#status { color: #9de2ff; font: 700 14px 'Consolas'; min-width: 110px; }
        QTextEdit#logs {
            background: #081224; color: #cfeeff; border: 1px solid #1f4f74;
            border-radius: 10px; font: 14px 'Consolas'; padding: 8px;
        }
        QTextEdit#input {
            background: #081224; color: #e6f7ff; border: 1px solid #2b5f84;
            border-radius: 10px; font: 15px 'Segoe UI'; padding: 8px;
        }
        QPushButton {
            background: #1c5d8f; color: white; border: 1px solid #4ea9df;
            border-radius: 9px; font: 700 14px 'Segoe UI'; padding: 8px 14px;
        }
        QPushButton:hover { background: #2878b6; }
        QProgressBar {
            background: #0a182d; border: 1px solid #1f4f74; border-radius: 7px; height: 14px;
        }
        QProgressBar::chunk { background: #4dbdff; border-radius: 7px; }
        """)

        self.add_assistant_text("EDITH HUD initialized.")
        self.add_assistant_text("Systems online. Awaiting command.")

    def _bar(self, name):
        wrap = QVBoxLayout()
        lbl = QLabel(name)
        lbl.setObjectName("sub")
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        wrap.addWidget(lbl)
        wrap.addWidget(bar)
        return {"layout": wrap, "bar": bar}

    def _start_fake_telemetry(self):
        self.tele_timer = QTimer(self)
        self.tele_timer.timeout.connect(self._tick_telemetry)
        self.tele_timer.start(850)

    def _tick_telemetry(self):
        # fake dynamic values (replace with psutil later)
        sec = datetime.now().second
        cpu = (sec * 3) % 100
        net = (sec * 5 + 20) % 100
        mic = (sec * 7 + 10) % 100
        self.bridge.telemetry.emit(cpu, net, mic)

    def update_telemetry(self, cpu, net, mic):
        self.cpu["bar"].setValue(cpu)
        self.net["bar"].setValue(net)
        self.mic["bar"].setValue(mic)

    def add_assistant_text(self, text: str):
        t = datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"[{t}] EDITH: {text}")

    def add_user_text(self, text: str):
        t = datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"[{t}] YOU: {text}")

    def set_status(self, txt: str):
        self.status.setText(txt.upper())

    def on_send(self):
        text = self.input.toPlainText().strip()
        if not text:
            return
        self.input.clear()
        self.bridge.user_text.emit(text)
        self.bridge.status_text.emit("processing")

        threading.Thread(target=self._worker, args=(text,), daemon=True).start()

    def _worker(self, text: str):
        try:
            out = asyncio.run(self.orchestrator.handle(text))
            self.bridge.assistant_text.emit(str(out))
            self.bridge.status_text.emit("ready")
        except Exception as e:
            self.bridge.assistant_text.emit(f"Error: {type(e).__name__}: {e}")
            self.bridge.status_text.emit("error")

    def on_stop(self):
        try:
            if hasattr(self.orchestrator, "tts") and self.orchestrator.tts:
                self.orchestrator.tts.stop()
            self.bridge.assistant_text.emit("Speech stopped.")
            self.bridge.status_text.emit("stopped")
        except Exception as e:
            self.bridge.assistant_text.emit(f"Stop error: {e}")
            self.bridge.status_text.emit("error")


def run():
    app = QApplication(sys.argv)
    win = EdithHudWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
