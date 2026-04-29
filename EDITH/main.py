
import asyncio
import argparse
import sys

from config import Config
from core.orchestrator import Orchestrator


def run_tk_gui(config: Config):
    from ui.app import EdithApp
    orchestrator = Orchestrator(config)
    app = EdithApp(orchestrator)
    app.mainloop()


def run_pyqt_gui(config: Config):
    from PyQt6.QtWidgets import QApplication
    from gui.gui_app_pyqt_backup import EdithWindow

    app = QApplication(sys.argv)
    orchestrator = Orchestrator(config)
    window = EdithWindow(orchestrator)
    window.show()
    sys.exit(app.exec())


async def run_cli(config: Config):
    orchestrator = Orchestrator(config)
    print("🤖 EDITH started (CLI). Type 'help' or 'exit'.\n")

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            print("EDITH: Goodbye!")
            break

        response = await orchestrator.handle(user_input)
        print(f"EDITH: {response}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode")
    parser.add_argument("--pyqt", action="store_true", help="Run with PyQt GUI")
    # default = Tkinter GUI
    args = parser.parse_args()

    cfg = Config()
    cfg.validate()

    if args.cli:
        asyncio.run(run_cli(cfg))
        return

    if args.pyqt:
        run_pyqt_gui(cfg)
        return

    try:
        run_tk_gui(cfg)
    except Exception as e:
        print(f"GUI start failed: {e}")
        print("Falling back to CLI mode...")
        asyncio.run(run_cli(cfg))


if __name__ == "__main__":
    main()