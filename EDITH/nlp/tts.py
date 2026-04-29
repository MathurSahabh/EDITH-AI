import threading

try:
    import pyttsx3
except Exception:
    pyttsx3 = None


class TTS:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._speaking = False
        self._lock = threading.Lock()
        self._engine = None

        if pyttsx3 is not None:
            try:
                self._engine = pyttsx3.init()
                # optional defaults
                rate = self._engine.getProperty("rate")
                self._engine.setProperty("rate", max(120, min(220, rate)))
            except Exception:
                self._engine = None

    def set_enabled(self, enabled: bool):
        self.enabled = bool(enabled)

    def is_speaking(self) -> bool:
        with self._lock:
            return self._speaking

    def speak(self, text: str):
        if not self.enabled:
            return
        if not text or not text.strip():
            return
        if self._engine is None:
            return

        def _run():
            with self._lock:
                self._speaking = True
            try:
                self._engine.say(text)
                self._engine.runAndWait()
            except Exception:
                pass
            finally:
                with self._lock:
                    self._speaking = False

        threading.Thread(target=_run, daemon=True).start()

    def stop(self):
        if self._engine is None:
            return
        try:
            self._engine.stop()
        except Exception:
            pass
        finally:
            with self._lock:
                self._speaking = False