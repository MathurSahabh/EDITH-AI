import asyncio
import threading
import queue
import os
from datetime import datetime
from types import SimpleNamespace

import customtkinter as ctk
from dotenv import load_dotenv

from core.orchestrator import Orchestrator
from nlp.stt import STT, listen_once

load_dotenv()


class ChatBubble(ctk.CTkFrame):
    def __init__(self, master, role: str, text: str, ts: str):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)

        is_user = role.lower() == "you"
        anchor = "e" if is_user else "w"
        bg = "#1e4f86" if is_user else "#1a2230"
        title_col = "#9ed7ff"
        text_col = "#eaf6ff"

        bubble = ctk.CTkFrame(
            self,
            fg_color=bg,
            corner_radius=14,
            border_width=1,
            border_color="#2a3d57",
        )
        bubble.grid(
            row=0,
            column=0,
            sticky=anchor,
            padx=(90 if is_user else 12, 12 if is_user else 90),
            pady=(6, 3),
        )

        ctk.CTkLabel(
            bubble,
            text=f"{role} · {ts}",
            text_color=title_col,
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(8, 2))

        ctk.CTkLabel(
            bubble,
            text=text,
            text_color=text_col,
            font=ctk.CTkFont(size=15),
            justify="left",
            wraplength=760,
        ).pack(anchor="w", padx=10, pady=(0, 10))


class EdithUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("EDITH • Control Center")
        self.geometry("1280x800")
        self.minsize(1080, 700)
        self.configure(fg_color="#0b1018")

        cfg = SimpleNamespace(
            DB_PATH="edith.db",
            OPENROUTER_API_KEY=os.getenv("OPENROUTER_API_KEY", ""),
            OPENWEATHER_API_KEY=os.getenv("OPENWEATHER_API_KEY", ""),
            BING_API_KEY=os.getenv("BING_API_KEY", ""),
            BING_ENDPOINT=os.getenv("BING_ENDPOINT", ""),
            ENABLE_TTS=True,
        )
        self.orchestrator = Orchestrator(cfg)

        self.q = queue.Queue()
        self.worker_busy = False
        self.stop_requested = False

        self.voice_mode = "wake"  # wake | dictation
        self.voice_enabled = False
        self.voice_assistant = STT(
            wake_word="edith",
            wake_aliases={"edith", "hey edith", "ok edith", "HEY EDITH","OK EDITH","EDITH"},
            require_wake_word=True,
            timeout=6,
            phrase_time_limit=8,
            followup_window_sec=6.0,
        )

        self._build_layout()
        self.after(100, self._poll_queue)
        self.after(700, self.start_wake_listener)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # --------------------- UI Build ---------------------
    def _btn(self, master, text, command, width=None, fg="#1b2533", hover="#27384f"):
        return ctk.CTkButton(
            master,
            text=text,
            command=command,
            width=width if width else 0,
            fg_color=fg,
            hover_color=hover,
            text_color="#e6f4ff",
            corner_radius=10,
            border_width=1,
            border_color="#2d425e",
            font=ctk.CTkFont(size=14),
        )

    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(
            self,
            width=270,
            corner_radius=0,
            fg_color="#0f1622",
            border_width=1,
            border_color="#243447",
        )
        self.sidebar.grid(row=0, column=0, rowspan=3, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.sidebar,
            text="EDITH",
            text_color="#a8ddff",
            font=ctk.CTkFont(size=42, weight="bold"),
        ).grid(row=0, column=0, padx=18, pady=(22, 4), sticky="w")

        ctk.CTkLabel(
            self.sidebar,
            text="Advanced Assistant Interface",
            text_color="#6e93b2",
            font=ctk.CTkFont(size=12),
        ).grid(row=1, column=0, padx=20, pady=(0, 14), sticky="w")

        self._btn(self.sidebar, "Clear Chat", lambda: self.safe_call(self.clear_chat)).grid(
            row=2, column=0, padx=16, pady=6, sticky="ew"
        )
        self.voice_toggle_btn = self._btn(
            self.sidebar, "Voice: ON", lambda: self.safe_call(self.toggle_wake_listener)
        )
        self.voice_toggle_btn.grid(row=3, column=0, padx=16, pady=6, sticky="ew")

        self.voice_mode_btn = self._btn(
            self.sidebar, "Mode: Wake", lambda: self.safe_call(self.toggle_voice_mode)
        )
        self.voice_mode_btn.grid(row=4, column=0, padx=16, pady=6, sticky="ew")

        ctk.CTkLabel(
            self.sidebar, text="Quick Commands", text_color="#8fbddb",
            font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=5, column=0, padx=16, pady=(14, 6), sticky="w")

        quicks = ["open notepad", "close notepad", "weather in delhi", "time in london", "latest tech news"]
        r = 6
        for cmd in quicks:
            self._btn(
                self.sidebar,
                cmd,
                lambda c=cmd: self.safe_call(self.inject_quick, c),
                fg="#141d2a",
                hover="#213044",
            ).grid(row=r, column=0, padx=16, pady=4, sticky="ew")
            r += 1

        ctk.CTkLabel(
            self.sidebar, text="Integrations", text_color="#8fbddb",
            font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=20, column=0, padx=16, pady=(14, 6), sticky="w")

        self._btn(self.sidebar, "Gmail", lambda: self.safe_call(self.run_integration, "gmail"), fg="#141d2a").grid(
            row=21, column=0, padx=16, pady=4, sticky="ew"
        )
        self._btn(self.sidebar, "Outlook", lambda: self.safe_call(self.run_integration, "outlook"), fg="#141d2a").grid(
            row=22, column=0, padx=16, pady=4, sticky="ew"
        )
        self._btn(self.sidebar, "Calendar", lambda: self.safe_call(self.run_integration, "calendar"), fg="#141d2a").grid(
            row=23, column=0, padx=16, pady=4, sticky="ew"
        )
        self._btn(self.sidebar, "Tasks", lambda: self.safe_call(self.run_integration, "tasks"), fg="#141d2a").grid(
            row=24, column=0, padx=16, pady=(4, 10), sticky="ew"
        )

        # Header
        self.header = ctk.CTkFrame(
            self,
            fg_color="#101827",
            corner_radius=12,
            border_width=1,
            border_color="#2a3d56",
            height=84,
        )
        self.header.grid(row=0, column=1, sticky="ew", padx=(8, 12), pady=(8, 8))
        self.header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self.header,
            text="◉",
            text_color="#7fd3ff",
            font=ctk.CTkFont(size=38, weight="bold"),
        ).grid(row=0, column=0, padx=(14, 10), pady=10, sticky="w")

        ctk.CTkLabel(
            self.header,
            text="EDITH CONTROL CENTER",
            text_color="#d5eeff",
            font=ctk.CTkFont(size=30, weight="bold"),
        ).grid(row=0, column=1, sticky="w")

        self.status_lbl = ctk.CTkLabel(
            self.header,
            text="Ready",
            text_color="#8fd5ff",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.status_lbl.grid(row=0, column=2, padx=14, sticky="e")

        # Chat wrap
        self.chat_wrap = ctk.CTkFrame(
            self,
            fg_color="#0d1522",
            corner_radius=12,
            border_width=1,
            border_color="#25374d",
        )
        self.chat_wrap.grid(row=1, column=1, sticky="nsew", padx=(8, 12), pady=(0, 8))
        self.chat_wrap.grid_rowconfigure(0, weight=1)
        self.chat_wrap.grid_columnconfigure(0, weight=1)

        self.chat_scroll = ctk.CTkScrollableFrame(self.chat_wrap, fg_color="#0d1522")
        self.chat_scroll.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 4))
        self.chat_scroll.grid_columnconfigure(0, weight=1)

        self.typing_lbl = ctk.CTkLabel(
            self.chat_wrap,
            text="",
            text_color="#89c4e8",
            font=ctk.CTkFont(size=12, slant="italic"),
        )
        self.typing_lbl.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 6))

        # Footer
        self.footer = ctk.CTkFrame(
            self,
            fg_color="#101827",
            corner_radius=12,
            border_width=1,
            border_color="#2a3d56",
        )
        self.footer.grid(row=2, column=1, sticky="ew", padx=(8, 12), pady=(0, 10))
        self.footer.grid_columnconfigure(0, weight=1)

        self.entry = ctk.CTkTextbox(
            self.footer,
            height=86,
            corner_radius=10,
            fg_color="#0c131f",
            text_color="#edf7ff",
            border_width=1,
            border_color="#26394f",
        )
        self.entry.grid(row=0, column=0, padx=(10, 8), pady=10, sticky="ew")
        self.entry.bind("<Return>", self._enter_send)

        btns = ctk.CTkFrame(self.footer, fg_color="transparent")
        btns.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="ns")

        self.send_btn = self._btn(btns, "Send", lambda: self.safe_call(self.on_send), width=98, fg="#245f95", hover="#2f79bc")
        self.send_btn.grid(row=0, column=0, pady=(0, 8))

        self.mic_btn = self._btn(btns, "Mic", lambda: self.safe_call(self.on_mic), width=98, fg="#1b3552", hover="#244c73")
        self.mic_btn.grid(row=1, column=0, pady=(0, 8))

        self.stop_btn = self._btn(btns, "Stop", lambda: self.safe_call(self.on_stop), width=98, fg="#5a2430", hover="#7a3040")
        self.stop_btn.grid(row=2, column=0)

        self.add_message("EDITH", "Systems online. How may I assist?")
        self.add_message("EDITH", "Wake listening enabled. Say: 'Edith'.")

    # --------------------- Safety wrapper ---------------------
    def safe_call(self, fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            try:
                self.add_message("EDITH", f"UI error: {type(e).__name__}: {e}")
                self.set_status("Error")
            except Exception:
                pass

    # --------------------- Helpers ---------------------
    def _now(self):
        return datetime.now().strftime("%H:%M")

    def set_status(self, text: str):
        self.status_lbl.configure(text=text)

    def set_typing(self, on: bool):
        self.typing_lbl.configure(text="EDITH is processing..." if on else "")

    def add_message(self, role: str, text: str):
        bubble = ChatBubble(self.chat_scroll, role, text, self._now())
        bubble.grid(sticky="ew")
        self.after(30, lambda: self.chat_scroll._parent_canvas.yview_moveto(1.0))

    def inject_quick(self, cmd: str):
        self.entry.delete("1.0", "end")
        self.entry.insert("1.0", cmd)
        self.on_send()

    def run_integration(self, name: str):
        mapping = {
            "gmail": "open gmail inbox",
            "outlook": "open outlook inbox",
            "calendar": "show my calendar events today",
            "tasks": "show my pending tasks",
        }
        cmd = mapping.get(name)
        if cmd:
            self.inject_quick(cmd)

    def _submit_voice_command(self, text: str):
        text = (text or "").strip()
        if text:
            self.after(0, lambda: self._handle_voice_command_on_ui(text))

    def _handle_voice_command_on_ui(self, text: str):
        if self.worker_busy:
            self.add_message("EDITH", f"Heard '{text}', currently busy.")
            return
        self.entry.delete("1.0", "end")
        self.entry.insert("1.0", text)
        self.on_send()

    # --------------------- Voice ---------------------
    def start_wake_listener(self):
        if self.voice_enabled:
            return

        def on_command(cmd):
            self._submit_voice_command(cmd)

        def on_status(msg):
            self.after(0, lambda: self.set_status(msg))

        def on_error(err):
            self.after(0, lambda: self.add_message("EDITH", f"Mic error: {err}"))

        started = self.voice_assistant.start(
            on_command=on_command,
            on_status=on_status,
            on_error=on_error,
            on_heard=None,
        )
        self.voice_enabled = bool(started)
        self.voice_toggle_btn.configure(text=f"Voice: {'ON' if self.voice_enabled else 'OFF'}")

    def stop_wake_listener(self):
        if self.voice_enabled:
            self.voice_assistant.stop()
            try:
                if getattr(self.voice_assistant, "_thread", None):
                    self.voice_assistant._thread.join(timeout=1.2)
            except Exception:
                pass
            self.voice_enabled = False
            self.voice_toggle_btn.configure(text="Voice: OFF")
            self.set_status("Voice paused")

    def toggle_wake_listener(self):
        if self.voice_enabled:
            self.stop_wake_listener()
        else:
            self.start_wake_listener()

    def toggle_voice_mode(self):
        if self.voice_mode == "wake":
            self.voice_mode = "dictation"
            self.voice_mode_btn.configure(text="Mode: Dictation")
            self.stop_wake_listener()
            self.voice_assistant.require_wake_word = False
            self.start_wake_listener()
            self.add_message("EDITH", "Dictation mode enabled.")
        else:
            self.voice_mode = "wake"
            self.voice_mode_btn.configure(text="Mode: Wake")
            self.stop_wake_listener()
            self.voice_assistant.require_wake_word = True
            self.start_wake_listener()
            self.add_message("EDITH", "Wake-word mode enabled.")

    # --------------------- Events ---------------------
    def _enter_send(self, event):
        if event.state & 0x0001:  # Shift+Enter newline
            return
        self.on_send()
        return "break"

    def on_send(self):
        if self.worker_busy:
            return

        text = self.entry.get("1.0", "end").strip()
        if not text:
            return

        self.entry.delete("1.0", "end")
        self.add_message("You", text)

        self.worker_busy = True
        self.stop_requested = False
        self.send_btn.configure(state="disabled")
        self.set_status("Thinking...")
        self.set_typing(True)

        threading.Thread(target=self._worker, args=(text,), daemon=True).start()

    def _worker(self, text: str):
        try:
            result = asyncio.run(self.orchestrator.handle(text))
            self.q.put(("ok", str(result)))
        except Exception as e:
            self.q.put(("err", f"LLM error: {type(e).__name__}: {e}"))

    def _poll_queue(self):
        try:
            try:
                kind, payload = self.q.get_nowait()
                if kind == "ok":
                    self.add_message("EDITH", "Response stopped." if self.stop_requested else payload)
                    self.set_status("Ready")
                else:
                    self.add_message("EDITH", payload)
                    self.set_status("Error")

                self.worker_busy = False
                self.send_btn.configure(state="normal")
                self.set_typing(False)
            except queue.Empty:
                pass
        except Exception as e:
            try:
                self.add_message("EDITH", f"Poll error: {e}")
                self.set_status("Error")
            except Exception:
                pass
        finally:
            self.after(100, self._poll_queue)

    def on_mic(self):
        heard = (listen_once(timeout=10, phrase_time_limit=15) or "").strip()
        if not heard:
            self.add_message("EDITH", "No speech captured.")
            return
        self.inject_quick(heard)

    def on_stop(self):
        self.stop_requested = True
        self.set_typing(False)
        self.set_status("Stopped")
        try:
            if hasattr(self.orchestrator, "tts") and self.orchestrator.tts:
                self.orchestrator.tts.stop()
        except Exception:
            pass

    def clear_chat(self):
        for w in self.chat_scroll.winfo_children():
            w.destroy()
        self.add_message("EDITH", "Chat cleared.")
        self.set_status("Ready")

    def _on_close(self):
        try:
            self.stop_wake_listener()
        except Exception:
            pass
        self.destroy()


def run():
    app = EdithUI()
    app.mainloop()


if __name__ == "__main__":
    run()
