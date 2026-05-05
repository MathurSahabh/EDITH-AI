"""
Feature 3: Language Translator for EDITH-AI
=============================================
Uses the free MyMemory API — no API key required.

Commands:
  translate <text> to <language>
  translate <text> from <lang> to <lang>
  translate hello to spanish
  translate "bonjour tout le monde" from french to english
"""

import re
from typing import Optional

import requests


# Map of common language names → ISO 639-1 codes
LANG_MAP = {
    "afrikaans": "af", "albanian": "sq", "arabic": "ar", "bengali": "bn",
    "bulgarian": "bg", "catalan": "ca", "chinese": "zh", "mandarin": "zh",
    "croatian": "hr", "czech": "cs", "danish": "da", "dutch": "nl",
    "english": "en", "estonian": "et", "finnish": "fi", "french": "fr",
    "german": "de", "greek": "el", "gujarati": "gu", "hebrew": "he",
    "hindi": "hi", "hungarian": "hu", "icelandic": "is", "indonesian": "id",
    "italian": "it", "japanese": "ja", "kannada": "kn", "korean": "ko",
    "latvian": "lv", "lithuanian": "lt", "malay": "ms", "malayalam": "ml",
    "marathi": "mr", "nepali": "ne", "norwegian": "no", "persian": "fa",
    "farsi": "fa", "polish": "pl", "portuguese": "pt", "punjabi": "pa",
    "romanian": "ro", "russian": "ru", "serbian": "sr", "sinhalese": "si",
    "slovak": "sk", "slovenian": "sl", "spanish": "es", "swahili": "sw",
    "swedish": "sv", "tamil": "ta", "telugu": "te", "thai": "th",
    "turkish": "tr", "ukrainian": "uk", "urdu": "ur", "vietnamese": "vi",
    "welsh": "cy",
}


class Translator:
    """Translates text using the free MyMemory public API."""

    API_URL = "https://api.mymemory.translated.net/get"
    TIMEOUT = 10

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def handle(self, text: str) -> Optional[str]:
        """Return a response string if this module handles the command, else None."""
        raw = (text or "").strip()
        low = raw.lower()

        if not low.startswith("translate "):
            return None

        payload = raw[len("translate "):].strip()
        return self._parse_and_translate(payload)

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse_and_translate(self, payload: str) -> str:
        """
        Patterns supported:
          <text> to <lang>
          <text> from <lang> to <lang>
          "<text>" to <lang>
        """
        low = payload.lower()

        # Pattern: <text> from <src_lang> to <tgt_lang>
        m = re.search(r"\bfrom\s+([a-z]+)\s+to\s+([a-z]+)\s*$", low)
        if m:
            src_name = m.group(1)
            tgt_name = m.group(2)
            text_part = payload[: low.rfind(" from " + src_name)].strip().strip('"').strip("'")
            src_code = LANG_MAP.get(src_name, src_name[:2])
            tgt_code = LANG_MAP.get(tgt_name)
            if not tgt_code:
                return f"Unknown target language: '{tgt_name}'. Try 'spanish', 'french', 'hindi', etc."
            return self._translate(text_part, f"{src_code}|{tgt_code}", tgt_name)

        # Pattern: <text> to <tgt_lang>
        m = re.search(r"\bto\s+([a-z]+)\s*$", low)
        if m:
            tgt_name = m.group(1)
            # everything before " to <lang>"
            text_part = payload[: low.rfind(" to " + tgt_name)].strip().strip('"').strip("'")
            tgt_code = LANG_MAP.get(tgt_name)
            if not tgt_code:
                return f"Unknown target language: '{tgt_name}'. Try 'spanish', 'french', 'hindi', etc."
            lang_pair = f"en|{tgt_code}"
            return self._translate(text_part, lang_pair, tgt_name)

        return (
            "Could not parse translation request. Try:\n"
            "  translate hello to spanish\n"
            "  translate good morning from english to hindi\n"
            "  translate 'merci beaucoup' from french to english"
        )

    # ------------------------------------------------------------------
    # API call
    # ------------------------------------------------------------------

    def _translate(self, text: str, lang_pair: str, target_lang_name: str) -> str:
        if not text:
            return "Please provide text to translate."

        try:
            r = requests.get(
                self.API_URL,
                params={"q": text, "langpair": lang_pair},
                timeout=self.TIMEOUT,
            )
            if r.status_code != 200:
                return f"Translation API error ({r.status_code}). Please try again."

            data = r.json()
            response_data = data.get("responseData", {})
            translated = response_data.get("translatedText", "")

            if not translated:
                return "Translation returned empty result. Please try again."

            # MyMemory returns error strings when quota is exceeded
            if "MYMEMORY WARNING" in translated.upper():
                return "Translation quota exceeded. Please try again later."

            confidence = response_data.get("match", 0)
            confidence_str = f" (confidence: {int(confidence * 100)}%)" if confidence else ""

            return (
                f"Translation to {target_lang_name.title()}{confidence_str}:\n"
                f"  Original : {text}\n"
                f"  Translated: {translated}"
            )

        except requests.exceptions.ConnectionError:
            return "Translation failed: No internet connection."
        except requests.exceptions.Timeout:
            return "Translation timed out. Please try again."
        except Exception as e:
            return f"Translation failed: {e}"
