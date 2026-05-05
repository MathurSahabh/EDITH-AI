# EDITH-AI

**E**very **D**ay **I** **T**ackle **H**umankind — your personal AI assistant inspired by Iron Man's EDITH.

EDITH is a Python-powered desktop AI that combines an OpenRouter-backed LLM, live web search, email/calendar integrations, TTS/STT, and full desktop-automation skills into a single conversational interface.

---

## Features

| Category | Capabilities |
|---|---|
| **Conversation** | Context-aware chat via OpenRouter with persistent memory |
| **Web Search** | Live DuckDuckGo + optional Bing results with freshness labels |
| **Email** | Compose, draft, send via Gmail or Outlook (OAuth) |
| **Calendar / Tasks** | Google Calendar & Tasks integration |
| **Desktop Automation** | Open/close apps, type, click, screenshots, WhatsApp automation |
| **Developer Skills** | Generate/run/explain/fix code, Git & Docker helpers |
| **System Control** | Volume, brightness, power, process manager, system info |
| **Voice** | TTS output (pyttsx3) + STT input (SpeechRecognition / PyAudio) |
| **GUI** | Dark-themed Tkinter UI (`customtkinter`) or PyQt6 holographic HUD |

---

## Quick Start

### 1. Clone

```bash
git clone https://github.com/MathurSahabh/EDITH-AI.git
cd EDITH-AI/EDITH
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> **Windows only:** PyAudio may require a pre-built wheel.  
> Install with `pip install pipwin && pipwin install pyaudio` if the normal install fails.

### 3. Configure environment

```bash
cp .env.example .env
# Open .env and fill in at minimum OPENROUTER_API_KEY
```

Get an OpenRouter API key at <https://openrouter.ai/keys>.

### 4. Run

```bash
# Tkinter GUI (default)
python main.py

# CLI mode
python main.py --cli

# PyQt6 holographic HUD
python main.py --pyqt
```

---

## Environment Variables

See [`.env.example`](.env.example) for the full list with descriptions.  
Only `OPENROUTER_API_KEY` is required to run; all other keys unlock optional features.

---

## Project Structure

```
EDITH/
├── main.py               # Entry point (GUI / CLI launcher)
├── config.py             # All configuration via environment variables
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variable template
├── core/
│   ├── orchestrator.py   # Main request router
│   ├── commands.py       # Command dispatcher
│   ├── skills.py         # Email / Calendar / Tasks skills
│   ├── developer_skills.py  # Coding & Git skills
│   ├── system_control.py # Power, volume, brightness, etc.
│   ├── desktop_actions.py   # GUI automation
│   ├── app_control.py    # Open / close applications
│   ├── smart_open.py     # URL & search shortcuts
│   └── memory.py         # SQLite conversation memory
├── nlp/
│   ├── openai_client.py  # Async OpenRouter LLM wrapper
│   ├── tts.py            # Text-to-speech
│   └── stt.py            # Speech-to-text
├── search/
│   ├── web.py            # DuckDuckGo + Bing search
│   └── email_parse.py    # Email command parser
├── integrations/
│   ├── email_router.py   # Gmail / Outlook dispatcher
│   ├── email_gmail.py    # Gmail OAuth integration
│   ├── email_outlook.py  # Outlook OAuth integration
│   ├── calendar_router.py
│   └── tasks_router.py
└── ui/
    ├── app.py            # customtkinter GUI
    ├── edith_hub.py      # Hub overlay
    └── edith_holo.qml    # PyQt6 holographic HUD
```

---

## License

MIT
