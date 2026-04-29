import re
import threading
import time
from typing import Callable, Optional

import speech_recognition as sr


class STT:
    def __init__(
        self,
        wake_word: str = "edith",
        wake_aliases=None,
        timeout: int = 6,
        phrase_time_limit: int = 10,
        ambient_duration: float = 0.6,
        followup_window_sec: float = 6.0,
        require_wake_word: bool = False,
    ):
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True

        self.wake_word = (wake_word or "edith").strip().lower()
        aliases = set(wake_aliases or [])
        aliases.add(self.wake_word)
        self.wake_aliases = {a.strip().lower() for a in aliases if a and a.strip()}

        self.timeout = timeout
        self.phrase_time_limit = phrase_time_limit
        self.ambient_duration = ambient_duration
        self.followup_window_sec = followup_window_sec
        self.require_wake_word = require_wake_word

        self._thread = None
        self._stop_event = threading.Event()
        self._running = False
        self._mic = None
        self._armed_until = 0.0

    def is_running(self) -> bool:
        return self._running

    def start(
        self,
        on_command: Callable[[str], None],
        on_status: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        on_heard: Optional[Callable[[str], None]] = None,
    ) -> bool:
        if self._running:
            if on_status:
                on_status("Already listening.")
            return False

        try:
            self._mic = sr.Microphone()
            with self._mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=self.ambient_duration)
        except Exception as e:
            if on_error:
                on_error(f"Mic error: {e}")
            return False

        self._stop_event.clear()
        self._running = True
        self._thread = threading.Thread(
            target=self._loop,
            args=(on_command, on_status, on_error, on_heard),
            daemon=True,
        )
        self._thread.start()

        if on_status:
            on_status("Listening... say 'edith <command>'")
        return True

    def stop(self):
        self._stop_event.set()
        self._running = False

    def _loop(self, on_command, on_status, on_error, on_heard):
        try:
            with self._mic as source:  # open once
                while not self._stop_event.is_set():
                    try:
                        audio = self.recognizer.listen(
                            source,
                            timeout=self.timeout,
                            phrase_time_limit=self.phrase_time_limit,
                        )

                        heard = self.recognizer.recognize_google(audio).strip()
                        if not heard:
                            continue

                        if on_heard:
                            on_heard(heard)

                        if not self.require_wake_word:
                            direct_cmd = self._normalize_direct_command(heard)
                            if direct_cmd:
                                on_command(direct_cmd)
                            continue

                        cmd = self.extract_wake_command(heard)
                        if cmd is None:
                            if time.time() < self._armed_until:
                                on_command(heard)
                            continue

                        if cmd == "":
                            self._armed_until = time.time() + self.followup_window_sec
                            if on_status:
                                on_status("Yes? say: 'edith <command>'")
                            continue

                        self._armed_until = 0.0
                        on_command(cmd)

                    except sr.WaitTimeoutError:
                        continue
                    except sr.UnknownValueError:
                        continue
                    except sr.RequestError as e:
                        if on_error:
                            on_error(f"Speech service request failed: {e}")
                    except Exception as e:
                        if on_error:
                            on_error(f"Voice error: {e}")
        finally:
            self._running = False
            if on_status:
                on_status("Voice loop ended.")

    def _normalize_direct_command(self, heard: str) -> str:
        normalized = re.sub(r"\s+", " ", (heard or "")).strip()
        if not normalized:
            return ""

        wake_cmd = self.extract_wake_command(normalized)
        if wake_cmd is None:
            return normalized
        return wake_cmd

    def extract_wake_command(self, heard: str):
        normalized = re.sub(r"[^a-z0-9\s]", " ", (heard or "").lower())
        normalized = re.sub(r"\s+", " ", normalized).strip()
        if not normalized:
            return None

        wake_variants = {
            "edith", "edit", "ed it", "aedith", "hey edith", "hey edit", "okay edith", "ok edith"
        }
        all_wakes = set(self.wake_aliases) | wake_variants

        for wake in all_wakes:
            if normalized == wake:
                return ""
            if normalized.startswith(wake + " "):
                return normalized[len(wake):].strip()
        return None


def listen_once(timeout: int = 5, phrase_time_limit: int = 10) -> str:
    """
    One-shot microphone capture for UI mic button.
    Returns recognized text or raises RuntimeError.
    """
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
    except sr.WaitTimeoutError as e:
        raise RuntimeError("No speech detected before timeout.") from e
    except Exception as e:
        raise RuntimeError(f"Microphone capture failed: {e}") from e

    try:
        text = recognizer.recognize_google(audio)
    except sr.UnknownValueError as e:
        raise RuntimeError("Speech was not understood.") from e
    except sr.RequestError as e:
        raise RuntimeError(f"Speech service request failed: {e}") from e

    return text.strip()