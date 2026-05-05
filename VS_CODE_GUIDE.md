# 🤖 EDITH-AI — VS Code Setup & Run Guide

> Complete step-by-step guide to install, configure, and run EDITH on your machine using VS Code.

---

## 📋 Prerequisites

| Tool | Minimum Version | Download |
|------|-----------------|----------|
| Python | 3.10+ | https://www.python.org/downloads/ |
| VS Code | Latest | https://code.visualstudio.com/ |
| Git | Any | https://git-scm.com/ |

---

## 🚀 Step 1 — Clone the Repository

Open VS Code's integrated terminal (`Ctrl + `` ` ``) and run:

```bash
git clone https://github.com/MathurSahabh/EDITH-AI.git
cd EDITH-AI/EDITH
```

Or open the folder:  
`File → Open Folder → select the EDITH-AI/EDITH folder`

---

## 🐍 Step 2 — Create a Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

> ✅ You should see `(venv)` in your terminal prompt after activation.

**Select the interpreter in VS Code:**  
`Ctrl + Shift + P` → `Python: Select Interpreter` → choose `venv`

---

## 📦 Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

> ⚠️ **PyAudio note (Windows):** If PyAudio fails, install the pre-built wheel:
> ```bash
> pip install pipwin
> pipwin install pyaudio
> ```

> ⚠️ **PyAudio note (Linux/macOS):**
> ```bash
> sudo apt install portaudio19-dev   # Ubuntu/Debian
> brew install portaudio              # macOS
> pip install pyaudio
> ```

---

## 🔑 Step 4 — Configure Environment Variables

Copy the example file and fill in your keys:

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Then open `.env` in VS Code and fill in:

```env
# REQUIRED
OPENROUTER_API_KEY=sk-or-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# OPTIONAL — for weather commands
OPENWEATHER_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# OPTIONAL — for Bing search boost
BING_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**How to get an OpenRouter API key:**
1. Go to https://openrouter.ai/keys
2. Sign up or log in
3. Create a new API key
4. Copy and paste into `.env`

---

## ▶️ Step 5 — Run EDITH

Make sure you are inside the `EDITH/` folder:

```bash
cd EDITH   # if not already there
```

### Option A — Tkinter GUI (Default, Recommended)
```bash
python main.py
```

### Option B — CLI (No GUI needed)
```bash
python main.py --cli
```

### Option C — Holographic HUD (PyQt6)
```bash
python run_holo.py
```

### Option D — Hub Overlay
```bash
python run_hub.py
```

---

## 🛠️ VS Code Launch Configuration (Optional)

Create `.vscode/launch.json` inside the `EDITH-AI` folder for one-click Run:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "EDITH — GUI",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/EDITH/main.py",
      "cwd": "${workspaceFolder}/EDITH",
      "console": "integratedTerminal",
      "env": {}
    },
    {
      "name": "EDITH — CLI",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/EDITH/main.py",
      "args": ["--cli"],
      "cwd": "${workspaceFolder}/EDITH",
      "console": "integratedTerminal"
    }
  ]
}
```

Then press **F5** to launch, or use the **Run & Debug** panel (`Ctrl + Shift + D`).

---

## ✨ New Features — Quick Reference

All new commands can be typed in the EDITH chat window or CLI:

### ⏰ Reminder System
```
remind me to take medicine in 30 minutes
remind me to call mom in 2 hours
remind me to drink water in 45 minutes
list reminders
clear reminders
```

### 📋 Clipboard Manager
```
copy Hello, World!
show clipboard
clipboard history
clear clipboard
```

### 🌍 Language Translator
```
translate hello to spanish
translate good morning to hindi
translate "bonjour tout le monde" from french to english
translate I love coding to japanese
```

### 📐 Unit Converter
```
convert 100 km to miles
convert 50 celsius to fahrenheit
convert 10 kg to pounds
convert 1 gallon to liters
convert 5 feet to meters
convert 1000 bytes to kb
convert 60 mph to km/h
```

### 🔐 Password Generator
```
generate password
generate password 24 characters
generate password no symbols
generate password with symbols
generate pin
generate pin 4
generate passphrase
generate passphrase 5
```

---

## 📁 Project Structure

```
EDITH-AI/
└── EDITH/
    ├── main.py                  ← Entry point
    ├── config.py                ← All config from .env
    ├── requirements.txt         ← Python dependencies
    ├── .env                     ← Your API keys (create from .env.example)
    ├── core/
    │   ├── orchestrator.py      ← Main routing brain
    │   ├── commands.py          ← Command dispatcher
    │   ├── developer_skills.py  ← Coding/git/docker commands
    │   ├── system_control.py    ← System power/volume/brightness
    │   ├── desktop_actions.py   ← Open apps, files, websites
    │   ├── memory.py            ← SQLite persistent memory
    │   ├── skills.py            ← Email, calendar, tasks
    │   ├── reminders.py         ← ⭐ NEW: Reminder system
    │   ├── clipboard_manager.py ← ⭐ NEW: Clipboard manager
    │   ├── translator.py        ← ⭐ NEW: Language translator
    │   ├── converter.py         ← ⭐ NEW: Unit converter
    │   └── password_gen.py      ← ⭐ NEW: Password generator
    ├── nlp/
    │   ├── openrouter_client.py ← OpenRouter LLM wrapper
    │   ├── stt.py               ← Speech-to-text
    │   └── tts.py               ← Text-to-speech
    ├── search/
    │   └── web.py               ← Web search (DDG + Bing + RSS)
    ├── integrations/
    │   ├── email_gmail.py       ← Gmail OAuth integration
    │   ├── email_outlook.py     ← Outlook MSAL integration
    │   ├── calendar_router.py   ← Google Calendar
    │   └── tasks_router.py      ← Google Tasks
    └── ui/
        └── app.py               ← customtkinter GUI
```

---

## ❓ Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: customtkinter` | `pip install customtkinter` |
| `ModuleNotFoundError: pyperclip` | `pip install pyperclip` |
| `PyAudio not found` | See Step 3 for platform-specific install |
| `Missing OPENROUTER_API_KEY` | Add key to `.env` file |
| GUI window doesn't open | Try CLI mode: `python main.py --cli` |
| Voice commands not working | Check microphone permissions and PyAudio install |
| Weather not working | Add `OPENWEATHER_API_KEY` to `.env` |

---

## 💡 Tips for VS Code

- **Auto-format on save:** Install the `Black Formatter` extension
- **Linting:** Install `Pylance` or `Pylint` extension  
- **Env file support:** Install `DotENV` extension for `.env` syntax highlighting
- **Python env selector:** `Ctrl+Shift+P` → `Python: Select Interpreter`

---

*Happy coding! 🚀 — EDITH AI*
