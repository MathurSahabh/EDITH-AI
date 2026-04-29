import os
import sys

from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from ui.edith_holo_bridge import EdithBackend


def run():
    app = QApplication(sys.argv)
    engine = QQmlApplicationEngine()

    backend = EdithBackend()
    engine.rootContext().setContextProperty("backend", backend)

    qml_path = os.path.join(os.path.dirname(__file__), "ui", "edith_holo.qml")
    engine.load(qml_path)

    if not engine.rootObjects():
        raise RuntimeError("Failed to load QML UI")

    sys.exit(app.exec())


if __name__ == "__main__":
    run()