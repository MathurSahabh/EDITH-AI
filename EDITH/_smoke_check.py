import asyncio
import webbrowser
from config import Config
from core.orchestrator import Orchestrator

# Prevent browser popups during test
opened = []
def fake_open(url, *args, **kwargs):
    opened.append(url)
    return True
webbrowser.open = fake_open

async def main():
    cfg = Config()
    cfg.ENABLE_TTS = False
    o = Orchestrator(cfg)

    tests = [
        "search google for gpt-5",
        "search youtube for lofi music",
        "daily news",
        "open notepad",
        "send email to demo@example.com subject Test body Hello provider gmail",
        "confirm send",
    ]

    for t in tests:
        try:
            r = await o.handle(t)
            print("\\n>>", t)
            print(r[:500] if isinstance(r, str) else r)
        except Exception as e:
            print("\\n>>", t)
            print("ERROR:", type(e).__name__, e)

    print("\\nOpened URLs:")
    for u in opened:
        print("-", u)

asyncio.run(main())
