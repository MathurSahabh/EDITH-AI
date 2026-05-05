"""
Feature 5: Password Generator for EDITH-AI
============================================
Uses Python's built-in `secrets` module — cryptographically secure.

Commands:
  generate password               — 16-char alphanumeric + symbols
  generate password 20            — custom length
  generate password 24 characters — custom length (with word)
  generate password no symbols    — letters + digits only
  generate password with symbols  — letters + digits + symbols
  generate pin                    — 6-digit PIN
  generate pin 4                  — custom PIN length
  generate passphrase             — 4-word passphrase
  generate passphrase 5           — custom word count
"""

import re
import secrets
import string
from typing import Optional


# Common English words for passphrase generation
_WORDS = [
    "apple", "arrow", "beach", "blade", "brick", "cable", "candy", "chase",
    "chest", "cloud", "coral", "crisp", "crown", "curve", "dance", "delta",
    "depot", "drain", "dream", "drift", "drip", "eagle", "earth", "ember",
    "enter", "equal", "field", "flame", "flash", "float", "flood", "flora",
    "flute", "focus", "forge", "found", "front", "frost", "fruit", "glass",
    "globe", "gloom", "glove", "grace", "grade", "grain", "grand", "grant",
    "grape", "grasp", "gravel", "great", "green", "greet", "grove", "guard",
    "guide", "heart", "hedge", "hinge", "honey", "horse", "house", "human",
    "hurry", "hatch", "ideal", "image", "input", "inter", "jewel", "joint",
    "judge", "juice", "jumbo", "karma", "knife", "label", "lance", "laser",
    "laugh", "layer", "learn", "level", "light", "limit", "linen", "liver",
    "lobby", "lodge", "logic", "lotus", "lucky", "lunar", "magic", "major",
    "maple", "march", "match", "mayor", "media", "merge", "metal", "modal",
    "model", "money", "month", "moral", "mount", "mouse", "movie", "music",
    "never", "night", "noble", "north", "novel", "nurse", "ocean", "offer",
    "olive", "onion", "orbit", "order", "outer", "oxide", "paint", "panel",
    "paper", "patch", "pause", "peace", "pearl", "phase", "phone", "piano",
    "pilot", "pinch", "pixel", "pizza", "plain", "plane", "plant", "plate",
    "plaza", "plume", "point", "polar", "poppy", "power", "press", "price",
    "pride", "prime", "print", "prize", "probe", "pulse", "queen", "quest",
    "queue", "quick", "quiet", "quota", "quote", "radar", "radio", "rally",
    "rapid", "ratio", "reach", "ready", "realm", "rebel", "reign", "relay",
    "remix", "rider", "ridge", "rifle", "right", "river", "robot", "rocky",
    "rouge", "round", "route", "royal", "ruler", "rural", "saint", "sauce",
    "scale", "scene", "score", "scout", "seam", "serve", "seven", "shade",
    "shake", "shape", "share", "shark", "shine", "ship", "shirt", "shore",
    "shift", "short", "shout", "sight", "sigma", "since", "skill", "skull",
    "slate", "sleep", "slice", "slide", "slope", "smart", "smile", "smoke",
    "snake", "solar", "solid", "solve", "sonic", "south", "space", "speed",
    "spice", "spine", "spool", "spoon", "spray", "squad", "stack", "staff",
    "stage", "stamp", "stand", "stark", "start", "state", "steel", "steep",
    "stock", "stone", "store", "storm", "story", "strap", "straw", "strip",
    "study", "style", "sugar", "suite", "super", "surge", "swamp", "sweep",
    "sweet", "swift", "swing", "sword", "table", "taste", "teach", "terms",
    "think", "three", "throw", "tiger", "tidal", "title", "toast", "topic",
    "torch", "total", "touch", "tower", "track", "trade", "trail", "train",
    "trait", "brave", "treat", "trend", "trial", "trick", "troop", "trust",
    "truth", "tumor", "ultra", "under", "unify", "union", "unity", "until",
    "upper", "upset", "urban", "usage", "using", "usual", "valid", "value",
    "vapor", "vault", "venus", "venom", "verse", "video", "vista", "voice",
    "voter", "waste", "watch", "water", "world", "worry", "worth", "yield",
    "young", "zebra", "zeros", "zonal",
]


class PasswordGenerator:
    """Generates cryptographically secure passwords, PINs, and passphrases."""

    DEFAULT_PASSWORD_LENGTH = 16
    DEFAULT_PIN_LENGTH = 6
    DEFAULT_PASSPHRASE_WORDS = 4

    _ALPHA_NUMERIC = string.ascii_letters + string.digits
    _FULL = string.ascii_letters + string.digits + string.punctuation
    _SAFE_SYMBOLS = string.ascii_letters + string.digits + "!@#$%^&*-_=+?"

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def handle(self, text: str) -> Optional[str]:
        """Return a response string if this module handles the command, else None."""
        raw = (text or "").strip()
        low = raw.lower()

        # --- Passphrase ---
        if low.startswith("generate passphrase") or low.startswith("create passphrase"):
            m = re.search(r"(\d+)", low)
            count = int(m.group(1)) if m else self.DEFAULT_PASSPHRASE_WORDS
            count = max(2, min(count, 10))
            return self._passphrase(count)

        # --- PIN ---
        if low.startswith("generate pin") or low.startswith("create pin"):
            m = re.search(r"(\d+)", low)
            length = int(m.group(1)) if m else self.DEFAULT_PIN_LENGTH
            length = max(4, min(length, 12))
            return self._pin(length)

        # --- Password ---
        if low.startswith("generate password") or low.startswith("create password"):
            # Length?
            m = re.search(r"(\d+)", low)
            length = int(m.group(1)) if m else self.DEFAULT_PASSWORD_LENGTH
            length = max(8, min(length, 128))

            # Symbol preference
            if "no symbol" in low:
                charset = self._ALPHA_NUMERIC
                style = "no symbols"
            elif "with symbol" in low or "symbol" in low:
                charset = self._SAFE_SYMBOLS
                style = "with symbols"
            else:
                charset = self._SAFE_SYMBOLS
                style = "with symbols"

            return self._password(length, charset, style)

        return None

    # ------------------------------------------------------------------
    # Generators
    # ------------------------------------------------------------------

    def _password(self, length: int, charset: str, style: str) -> str:
        pwd = "".join(secrets.choice(charset) for _ in range(length))
        strength = self._strength(pwd)
        return (
            f"Generated password ({length} chars, {style}):\n"
            f"  {pwd}\n"
            f"  Strength: {strength}\n"
            f"  Tip: Store it in a password manager!"
        )

    def _pin(self, length: int) -> str:
        pin = "".join(secrets.choice(string.digits) for _ in range(length))
        return (
            f"Generated {length}-digit PIN:\n"
            f"  {pin}\n"
            f"  Tip: Never share your PIN with anyone."
        )

    def _passphrase(self, word_count: int) -> str:
        words = [secrets.choice(_WORDS) for _ in range(word_count)]
        separator = secrets.choice(["-", "_", ".", " "])
        phrase = separator.join(words)
        return (
            f"Generated passphrase ({word_count} words):\n"
            f"  {phrase}\n"
            f"  Tip: Passphrases are easy to remember and very secure!"
        )

    # ------------------------------------------------------------------
    # Strength estimator
    # ------------------------------------------------------------------

    @staticmethod
    def _strength(pwd: str) -> str:
        score = 0
        if len(pwd) >= 12:
            score += 1
        if len(pwd) >= 16:
            score += 1
        if any(c.islower() for c in pwd):
            score += 1
        if any(c.isupper() for c in pwd):
            score += 1
        if any(c.isdigit() for c in pwd):
            score += 1
        if any(c in string.punctuation for c in pwd):
            score += 1

        if score <= 2:
            return "Weak ❌"
        elif score <= 4:
            return "Medium ⚠️"
        else:
            return "Strong ✅"
