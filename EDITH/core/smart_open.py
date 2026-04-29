import os
import re
import subprocess
import urllib.parse
import webbrowser
from typing import Tuple


def _safe_startfile(uri: str) -> bool:
    try:
        os.startfile(uri)  # Windows only
        return True
    except Exception:
        return False


def _open_url(url: str) -> bool:
    try:
        webbrowser.open(url)
        return True
    except Exception:
        return False


def _open_exe(candidates) -> bool:
    for cmd in candidates:
        try:
            subprocess.Popen(cmd, shell=True)
            return True
        except Exception:
            continue
    return False


def _normalize(text: str) -> str:
    t = (text or "").lower().strip()
    t = re.sub(r"\s+", " ", t)
    return t


def _extract_after_open(t: str) -> str:
    for p in ["open ", "launch ", "start "]:
        if t.startswith(p):
            return t[len(p):].strip()
    return t


def _open_youtube_search(query: str) -> Tuple[bool, str]:
    q = (query or "").strip(" .,!?:;")
    if not q:
        return True, "What should I search on YouTube?"
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(q)
    ok = _open_url(url)
    return True, (f"Opening YouTube search for {q}." if ok else "Could not open YouTube search.")


def _open_google_search(query: str) -> Tuple[bool, str]:
    q = (query or "").strip(" .,!?:;")
    if not q:
        return True, "What should I search on Google?"
    url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(q)
    ok = _open_url(url)
    return True, (f"Searching Google for {q}." if ok else "Could not open Google search.")


def handle_search_shortcut(user_text: str) -> Tuple[bool, str]:
    """
    EN + HI robust shortcut parser.
    Returns:
      (True, message)  => handled
      (False, "")      => not handled
    """
    try:
        t = _normalize(user_text)
        if not t:
            return False, ""

        # open youtube direct
        if t in {
            "open youtube", "youtube open", "open youtube app",
            "youtube kholo", "youtube khol", "youtube open karo",
            "youtube chalu karo", "youtube chalao"
        }:
            ok = _open_url("https://www.youtube.com")
            return True, ("Opening YouTube." if ok else "Could not open YouTube.")

        # -------- English YouTube --------
        en_yt_patterns = [
            r"^(search|find|play)\s+(for\s+)?(.+?)\s+on\s+youtube\.?$",
            r"^search\s+(.+?)\s+youtube\.?$",
            r"^(on\s+)?youtube(\s+and)?\s+(search|find|play)\s+(for\s+)?(.+?)\.?$",
            r"^youtube(\s+and)?\s+search\s+(for\s+)?(.+?)\.?$",
            r"^youtube\s+play\s+(.+?)\.?$",
        ]
        for pat in en_yt_patterns:
            m = re.match(pat, t)
            if m:
                groups = [g for g in m.groups() if g]
                q = groups[-1] if groups else ""
                q = re.sub(r"^(for\s+)", "", q).strip()
                return _open_youtube_search(q)

        # -------- Hindi YouTube --------
        hi_yt_patterns = [
            r"^youtube\s+(par|pe|per)\s+(.+?)\s+(search|dhoondo|dhundo)\s+karo\.?$",
            r"^(.+?)\s+ko?\s*youtube\s+(par|pe|per)\s+(search|dhoondo|dhundo)\s+karo\.?$",
            r"^youtube\s+(par|pe|per)\s+(.+?)\s+chalao\.?$",
            r"^youtube\s+(par|pe|per)\s+(.+?)\s+play\s+karo\.?$",
            r"^(.+?)\s+youtube\s+(par|pe|per)\s+chalao\.?$",
            r"^youtube\s+(par|pe|per)\s+(.+?)\s+dikhao\.?$",
            r"^(.+?)\s+youtube\s+(par|pe|per)\s+search\s+karo\.?$",
        ]
        for pat in hi_yt_patterns:
            m = re.match(pat, t)
            if m:
                q = ""
                if len(m.groups()) >= 2 and m.group(2) and m.group(2) not in {"par", "pe", "per"}:
                    q = m.group(2)
                elif m.group(1) and m.group(1) not in {"par", "pe", "per"}:
                    q = m.group(1)

                if not q:
                    for g in reversed(m.groups()):
                        if g and g not in {"par", "pe", "per", "search", "dhoondo", "dhundo", "karo", "chalao", "play", "dikhao"}:
                            q = g
                            break
                return _open_youtube_search(q)

        # -------- English Google --------
        en_google_patterns = [
            r"^(search|find|google)\s+(for\s+)?(.+?)\s+on\s+google\.?$",
            r"^google\s+(.+?)\.?$",
        ]
        for pat in en_google_patterns:
            m = re.match(pat, t)
            if m:
                groups = [g for g in m.groups() if g]
                q = groups[-1] if groups else ""
                q = re.sub(r"^(for\s+)", "", q).strip()
                return _open_google_search(q)

        # -------- Hindi Google --------
        hi_google_patterns = [
            r"^google\s+(par|pe|per)\s+(.+?)\s+(search|dhoondo|dhundo)\s+karo\.?$",
            r"^(.+?)\s+ko?\s*google\s+(par|pe|per)\s+(search|dhoondo|dhundo)\s+karo\.?$",
        ]
        for pat in hi_google_patterns:
            m = re.match(pat, t)
            if m:
                q = m.group(2) if len(m.groups()) >= 2 else ""
                if not q and m.group(1) not in {"par", "pe", "per"}:
                    q = m.group(1)
                return _open_google_search(q)

        return False, ""

    except Exception as e:
        return True, f"Shortcut error handled safely: {type(e).__name__}"


def open_target(user_text: str) -> Tuple[bool, str]:
    t = _normalize(user_text)

    if not (t.startswith("open ") or t.startswith("launch ") or t.startswith("start ")):
        return False, ""

    target = _extract_after_open(t)
    target = (
        target.replace("the ", "")
        .replace(" app", "")
        .replace(" application", "")
        .replace(" website", "")
        .strip()
    )

    app_map = {
        "whatsapp": (["whatsapp:"], ["https://web.whatsapp.com"], ["start whatsapp"]),
        "youtube": ([], ["https://www.youtube.com"], []),
        "gmail": ([], ["https://mail.google.com"], []),
        "google calendar": ([], ["https://calendar.google.com"], []),
        "calendar": ([], ["https://calendar.google.com"], []),
        "google drive": ([], ["https://drive.google.com"], []),
        "telegram": (["tg:"], ["https://web.telegram.org"], ["start telegram"]),
        "spotify": (["spotify:"], ["https://open.spotify.com"], ["start spotify"]),
        "notepad": ([], [], ["notepad"]),
        "calculator": (["calculator:"], [], ["calc"]),
        "paint": ([], [], ["mspaint"]),
        "chrome": ([], ["https://www.google.com"], ["start chrome"]),
        "edge": ([], ["https://www.bing.com"], ["start msedge"]),
        "github": ([], ["https://github.com"], []),
        "linkedin": ([], ["https://www.linkedin.com"], []),
        "twitter": ([], ["https://x.com"], []),
        "x": ([], ["https://x.com"], []),
    }

    aliases = {
        "whatsapp web": "whatsapp",
        "whats app": "whatsapp",
        "yt": "youtube",
        "mail": "gmail",
        "g mail": "gmail",
        "calender": "calendar",
    }
    if target in aliases:
        target = aliases[target]

    if target in app_map:
        uris, urls, exes = app_map[target]

        for uri in uris:
            if _safe_startfile(uri):
                return True, f"Opening {target} app."

        if exes and _open_exe(exes):
            return True, f"Opening {target}."

        for url in urls:
            if _open_url(url):
                return True, f"Opening {target}."

        return True, f"I recognized '{target}', but couldn't open it."

    if target.startswith(("http://", "https://")) or "." in target:
        url = target if target.startswith(("http://", "https://")) else f"https://{target}"
        ok = _open_url(url)
        return True, (f"Opening {url}" if ok else f"Couldn't open {url}")

    _open_url(f"https://www.google.com/search?q={urllib.parse.quote_plus(target)}")
    return True, f"Couldn't find direct app mapping. Searching for {target}."