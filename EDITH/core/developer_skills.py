"""
Developer & Coding Skills for EDITH-AI

Provides:
  - AI Coder      : generate code via LLM
  - VSCode Link   : open VS Code
  - Run Code      : execute a file or snippet
  - Fix Bugs      : LLM-assisted bug fixing
  - Format Code   : run black / prettier / etc.
  - Explain Code  : LLM-based code explanation
  - Git Commit    : stage + commit
  - Git Push      : push to remote
  - Git Pull      : pull from remote
  - Git Branch    : create & checkout a new branch
  - Docker Helper : run docker sub-commands safely
  - AWS Helper    : run aws CLI sub-commands
  - Linux Commands: run arbitrary shell commands with a safety blocklist
"""

import os
import platform
import subprocess
import shlex
import re
import webbrowser
from pathlib import Path
from typing import Optional


class DeveloperSkills:
    """Handles all Developer & Coding commands."""

    def __init__(self, groq_client, config=None):
        self.groq = groq_client
        self.config = config

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def handle(self, text: str) -> Optional[str]:
        """Return a response string if this module handles the command, else None."""
        raw = (text or "").strip()
        low = raw.lower()

        # --- AI Coder ---
        for prefix in ("write code for ", "code for ", "generate code for ", "write code ", "generate code "):
            if low.startswith(prefix):
                task = raw[len(prefix):].strip()
                return await self._ai_coder(task)

        # --- VSCode Link ---
        if low in {
            "open vscode", "vscode", "vscode open", "launch vscode",
            "open visual studio code", "vscode link",
        }:
            return self._open_vscode()

        # --- Run Code ---
        m = re.match(r"^run code\s+(.+)$", low)
        if m:
            return self._run_code(raw[len("run code "):].strip())

        m = re.match(r"^run (python3?|node|bash|sh|java|go|ruby|perl)\s+(.+)$", low)
        if m:
            lang = "python" if m.group(1) == "python3" else m.group(1)
            code_or_file = raw[len(m.group(0)) - len(m.group(2)):].strip()
            return self._run_with_lang(lang, code_or_file)

        # --- Fix Bugs ---
        m = re.match(r"^(fix bugs?|debug code|fix code)\s+(.+)$", raw, re.IGNORECASE)
        if m:
            return await self._fix_bugs(m.group(2).strip())

        if low in {"fix bugs", "fix bug", "debug code"}:
            return "Please provide the code or file path to fix. Example: fix bugs myfile.py"

        # --- Format Code ---
        m = re.match(r"^(format code|format file)\s+(.+)$", raw, re.IGNORECASE)
        if m:
            return self._format_code(m.group(2).strip())

        # --- Explain Code ---
        m = re.match(r"^(explain code|explain this code|explain file)\s+(.+)$", raw, re.IGNORECASE)
        if m:
            return await self._explain_code(m.group(2).strip())

        # --- Git commands ---
        if low.startswith("git commit"):
            return self._git_commit(raw)

        if low in {"git push", "push to github", "push code"}:
            return self._git_push()

        if low in {"git pull", "pull from github", "pull code"}:
            return self._git_pull()

        m = re.match(r"^(git branch|create branch|new branch|git new branch)\s+(.+)$", raw, re.IGNORECASE)
        if m:
            return self._git_branch(m.group(2).strip())

        if low in {"git status", "show git status"}:
            return self._git_run(["git", "status"])

        if low in {"git log", "show git log"}:
            return self._git_run(["git", "log", "--oneline", "-10"])

        if low in {"git diff", "show git diff"}:
            return self._git_run(["git", "diff", "--stat"])

        # --- Docker Helper ---
        if low.startswith("docker "):
            return self._docker_helper(raw)

        # --- AWS Helper ---
        if low.startswith("aws "):
            return self._aws_helper(raw)

        # --- Linux Commands ---
        for prefix in ("linux ", "terminal ", "shell "):
            if low.startswith(prefix):
                cmd = raw[len(prefix):].strip()
                return self._linux_command(cmd)

        return None

    # ------------------------------------------------------------------
    # AI Coder
    # ------------------------------------------------------------------

    async def _ai_coder(self, task: str) -> str:
        if not task:
            return "Please describe what code you want me to write."
        prompt = (
            "You are EDITH, an expert AI coding assistant. "
            "Write clean, well-commented, production-quality code for the task below. "
            "State the programming language at the top.\n\n"
            f"Task: {task}"
        )
        try:
            result = await self.groq.chat(prompt)
            return result or "I could not generate the code right now."
        except Exception as e:
            return f"Code generation failed: {e}"

    # ------------------------------------------------------------------
    # VSCode Link
    # ------------------------------------------------------------------

    def _open_vscode(self) -> str:
        # Try the 'code' CLI first (works on all platforms when in PATH)
        try:
            result = subprocess.run(
                ["code", "--version"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                subprocess.Popen(["code", "."])
                return "Opened VS Code in the current directory."
        except (FileNotFoundError, Exception):
            pass

        # Platform-specific fallbacks
        sys_name = platform.system().lower()
        candidate_paths = []
        if sys_name.startswith("win"):
            username = os.environ.get("USERNAME", "")
            candidate_paths = [
                rf"C:\Users\{username}\AppData\Local\Programs\Microsoft VS Code\Code.exe",
                r"C:\Program Files\Microsoft VS Code\Code.exe",
            ]
        elif sys_name == "darwin":
            candidate_paths = [
                "/Applications/Visual Studio Code.app/Contents/MacOS/Electron"
            ]
        else:
            candidate_paths = ["/usr/bin/code", "/usr/local/bin/code"]

        for path in candidate_paths:
            if Path(path).exists():
                subprocess.Popen([path, "."])
                return "Opened VS Code."

        # Final fallback: vscode.dev in browser
        ok = webbrowser.open("https://vscode.dev/", new=2)
        return (
            "Opened VS Code in browser (vscode.dev)." if ok
            else "VS Code not found. Install from https://code.visualstudio.com/"
        )

    # ------------------------------------------------------------------
    # Run Code
    # ------------------------------------------------------------------

    def _run_code(self, file_or_snippet: str) -> str:
        path = Path(file_or_snippet)
        if path.exists():
            ext = path.suffix.lower()
            lang_map = {
                ".py": "python", ".js": "node", ".sh": "bash",
                ".rb": "ruby", ".go": "go", ".java": "java",
            }
            lang = lang_map.get(ext)
            if lang:
                return self._run_with_lang(lang, str(path))
            return f"Unknown file type '{ext}'. Supported: .py .js .sh .rb .go .java"
        # Treat as a Python one-liner; pass snippet as a separate argument to avoid injection
        return self._run_with_lang_snippet(file_or_snippet)

    def _run_with_lang(self, lang: str, code_or_file: str) -> str:
        lang = lang.lower()
        interpreter_map = {
            "python": ["python3"],
            "node":   ["node"],
            "bash":   ["bash"],
            "sh":     ["sh"],
            "ruby":   ["ruby"],
            "go":     ["go", "run"],
            "java":   ["java"],
            "perl":   ["perl"],
        }
        base = interpreter_map.get(lang, [lang])
        try:
            args = base + shlex.split(code_or_file)
        except ValueError:
            args = base + [code_or_file]
        try:
            result = subprocess.run(
                args, capture_output=True, text=True, timeout=30
            )
            output = (result.stdout + result.stderr).strip()
            return (
                f"Exit {result.returncode}:\n{output[:3000]}"
                if output
                else f"Exit {result.returncode}: (no output)"
            )
        except FileNotFoundError:
            return f"'{base[0]}' interpreter not found. Please install it."
        except subprocess.TimeoutExpired:
            return "Code execution timed out (30 s limit)."
        except Exception as e:
            return f"Run failed: {e}"

    def _run_with_lang_snippet(self, snippet: str) -> str:
        """Run a Python one-liner safely by passing the snippet as a separate argument."""
        try:
            result = subprocess.run(
                ["python3", "-c", snippet],
                capture_output=True, text=True, timeout=30
            )
            output = (result.stdout + result.stderr).strip()
            return (
                f"Exit {result.returncode}:\n{output[:3000]}"
                if output
                else f"Exit {result.returncode}: (no output)"
            )
        except FileNotFoundError:
            return "python3 interpreter not found. Please install Python."
        except subprocess.TimeoutExpired:
            return "Code execution timed out (30 s limit)."
        except Exception as e:
            return f"Run failed: {e}"

    # ------------------------------------------------------------------
    # Fix Bugs
    # ------------------------------------------------------------------

    async def _fix_bugs(self, payload: str) -> str:
        if not payload:
            return "Please provide code or a file path to fix."
        path = Path(payload)
        if path.exists():
            try:
                code = path.read_text(encoding="utf-8")[:8000]
            except Exception as e:
                return f"Could not read file: {e}"
        else:
            code = payload

        prompt = (
            "You are EDITH, an expert code debugger. "
            "Identify and fix all bugs in the code below. "
            "Show the corrected code and briefly explain each fix.\n\n"
            f"```\n{code}\n```"
        )
        try:
            result = await self.groq.chat(prompt)
            return result or "Could not analyse the code right now."
        except Exception as e:
            return f"Bug fix failed: {e}"

    # ------------------------------------------------------------------
    # Format Code
    # ------------------------------------------------------------------

    def _format_code(self, payload: str) -> str:
        path = Path(payload)
        if not path.exists():
            return f"File not found: {payload}"
        ext = path.suffix.lower()

        # Python → black, then autopep8
        if ext == ".py":
            for fmt in (["black", str(path)], ["autopep8", "--in-place", str(path)]):
                try:
                    r = subprocess.run(fmt, capture_output=True, text=True, timeout=30)
                    if r.returncode == 0:
                        return f"Formatted {path} with {fmt[0]}."
                except FileNotFoundError:
                    continue
                except Exception as e:
                    return f"Format error: {e}"
            return "No Python formatter found. Install one: pip install black"

        # JS/TS/JSON → prettier
        if ext in {".js", ".ts", ".jsx", ".tsx", ".json"}:
            try:
                r = subprocess.run(
                    ["prettier", "--write", str(path)],
                    capture_output=True, text=True, timeout=30
                )
                if r.returncode == 0:
                    return f"Formatted {path} with prettier."
                return f"prettier error: {r.stderr.strip()}"
            except FileNotFoundError:
                return "prettier not found. Install: npm install -g prettier"

        # C/C++ → clang-format
        if ext in {".c", ".cpp", ".h", ".hpp"}:
            try:
                r = subprocess.run(
                    ["clang-format", "-i", str(path)],
                    capture_output=True, text=True, timeout=30
                )
                if r.returncode == 0:
                    return f"Formatted {path} with clang-format."
                return f"clang-format error: {r.stderr.strip()}"
            except FileNotFoundError:
                return "clang-format not found. Install LLVM tools."

        return f"No formatter configured for '{ext}' files."

    # ------------------------------------------------------------------
    # Explain Code
    # ------------------------------------------------------------------

    async def _explain_code(self, payload: str) -> str:
        path = Path(payload)
        if path.exists():
            try:
                code = path.read_text(encoding="utf-8")[:8000]
            except Exception as e:
                return f"Could not read file: {e}"
        else:
            code = payload

        if not code.strip():
            return "Please provide code or a file path to explain."

        prompt = (
            "You are EDITH, an expert coding assistant. "
            "Explain the following code clearly and concisely: "
            "what it does, key logic, and any potential issues.\n\n"
            f"```\n{code}\n```"
        )
        try:
            result = await self.groq.chat(prompt)
            return result or "Could not explain the code right now."
        except Exception as e:
            return f"Explain failed: {e}"

    # ------------------------------------------------------------------
    # Git helpers
    # ------------------------------------------------------------------

    def _git_run(self, args: list) -> str:
        try:
            r = subprocess.run(args, capture_output=True, text=True, timeout=30)
            out = (r.stdout + r.stderr).strip()
            return out[:3000] if out else f"Git exited with code {r.returncode}."
        except FileNotFoundError:
            return "git not found. Please install Git."
        except subprocess.TimeoutExpired:
            return "Git command timed out."
        except Exception as e:
            return f"Git error: {e}"

    def _git_commit(self, raw: str) -> str:
        # Parse: "git commit <message>" or "git commit -m <message>"
        m = re.match(r"^git commit(?:\s+-m)?\s+[\"']?(.+)[\"']?\s*$", raw, re.IGNORECASE)
        msg = m.group(1).strip() if m else "Auto-commit by EDITH"

        add_out = self._git_run(["git", "add", "-A"])
        commit_out = self._git_run(["git", "commit", "-m", msg])
        return f"{add_out}\n{commit_out}".strip()

    def _git_push(self) -> str:
        return self._git_run(["git", "push"])

    def _git_pull(self) -> str:
        return self._git_run(["git", "pull"])

    def _git_branch(self, name: str) -> str:
        if not name:
            return "Please provide a branch name."
        return self._git_run(["git", "checkout", "-b", name])

    # ------------------------------------------------------------------
    # Docker Helper
    # ------------------------------------------------------------------

    def _docker_helper(self, raw: str) -> str:
        try:
            args = shlex.split(raw)
        except ValueError:
            args = raw.split()

        # Safety: block forced-remove of all containers/images
        if len(args) >= 3 and args[1] in {"rm", "rmi"} and "-f" in args:
            return (
                "Forced Docker remove (-f) is blocked for safety. "
                "Remove the -f flag and re-run."
            )

        try:
            r = subprocess.run(args, capture_output=True, text=True, timeout=60)
            out = (r.stdout + r.stderr).strip()
            return out[:3000] if out else f"Docker exited with code {r.returncode}."
        except FileNotFoundError:
            return "Docker not found. Please install Docker."
        except subprocess.TimeoutExpired:
            return "Docker command timed out (60 s)."
        except Exception as e:
            return f"Docker error: {e}"

    # ------------------------------------------------------------------
    # AWS Helper
    # ------------------------------------------------------------------

    def _aws_helper(self, raw: str) -> str:
        try:
            args = shlex.split(raw)
        except ValueError:
            args = raw.split()

        try:
            r = subprocess.run(args, capture_output=True, text=True, timeout=60)
            out = (r.stdout + r.stderr).strip()
            return out[:3000] if out else f"AWS CLI exited with code {r.returncode}."
        except FileNotFoundError:
            return "AWS CLI not found. Install with: pip install awscli"
        except subprocess.TimeoutExpired:
            return "AWS command timed out (60 s)."
        except Exception as e:
            return f"AWS error: {e}"

    # ------------------------------------------------------------------
    # Linux Commands
    # ------------------------------------------------------------------

    # Commands that are always blocked regardless of context
    _BLOCKED_PATTERNS = [
        r"rm\s+-rf?\s+/",     # rm -rf /
        r":\(\)\{.*\}",        # fork bomb
        r"dd\s+if=/dev/zero",  # disk wipe
        r"mkfs",               # reformat
        r">\s*/dev/sda",       # overwrite disk
    ]

    def _linux_command(self, cmd: str) -> str:
        if not cmd:
            return "Please provide a command. Example: terminal ls -la"
        for pat in self._BLOCKED_PATTERNS:
            if re.search(pat, cmd, re.IGNORECASE):
                return f"That command is blocked for safety: `{cmd}`"
        try:
            args = shlex.split(cmd)
            r = subprocess.run(args, capture_output=True, text=True, timeout=30)
            out = (r.stdout + r.stderr).strip()
            return out[:3000] if out else f"Exit {r.returncode}: (no output)"
        except FileNotFoundError:
            return f"Command not found: {cmd.split()[0]}"
        except subprocess.TimeoutExpired:
            return "Command timed out (30 s)."
        except Exception as e:
            return f"Command failed: {e}"
