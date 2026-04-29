import re
from typing import Dict, Any

EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")

def parse_email_command(text: str) -> Dict[str, Any]:
    t = (text or "").strip()
    low = t.lower()

    # provider config
    if low.startswith("set email provider "):
        p = low.replace("set email provider ", "").strip()
        if p in ("gmail", "outlook"):
            return {"action": "set_provider", "provider": p}

    # connect email providers
    if low in ("connect gmail", "gmail connect"):
        return {"action": "connect_provider", "provider": "gmail"}
    if low in ("connect outlook", "outlook connect"):
        return {"action": "connect_provider", "provider": "outlook"}

    # confirmation
    if low in ("confirm send", "yes send", "yes", "confirm"):
        return {"action": "confirm_send"}
    if low in ("cancel send", "cancel email", "no send", "no"):
        return {"action": "cancel_send"}

    # send draft
    if low in ("send last draft", "send draft", "send it", "send this draft"):
        return {"action": "prepare_send_last_draft"}

    # natural "send this mail to ..."
    if "send this mail to" in low or "send to" in low:
        m = EMAIL_RE.search(t)
        if m:
            return {"action": "prepare_send_last_draft", "to": m.group(0)}

    # direct send with optional provider + attachment
    m = re.match(
        r"send email to\s+(?P<to>\S+)\s+subject\s+(?P<subject>.+?)\s+body\s+(?P<body>.+?)(?:\s+provider\s+(?P<provider>gmail|outlook))?(?:\s+attachment\s+(?P<attachment>.+))?$",
        t,
        flags=re.I
    )
    if m:
        attachments = []
        if m.group("attachment"):
            attachments = [m.group("attachment").strip()]
        return {
            "action": "prepare_send_direct",
            "to": m.group("to").strip(),
            "subject": m.group("subject").strip(),
            "body": m.group("body").strip(),
            "provider": (m.group("provider") or "").lower() or None,
            "attachments": attachments,
        }

    # attach to last draft
    if low.startswith("attach "):
        path = t[7:].strip()
        return {"action": "attach_last_draft", "path": path}

    # draft
    if low.startswith("draft email") or low.startswith("write a mail") or low.startswith("write an email"):
        return {"action": "draft_email", "prompt": t}

    # calendar
    if low in ("connect calendar google", "calendar google connect"):
        return {"action": "connect_calendar", "provider": "google"}
    if low in ("connect calendar outlook", "calendar outlook connect"):
        return {"action": "connect_calendar", "provider": "outlook"}
    if low.startswith("create meeting "):
        return {"action": "create_meeting", "raw": t}
    if low in ("list today meetings", "today meetings", "list meetings"):
        return {"action": "list_meetings_today"}

    # tasks
    if low.startswith("add task "):
        return {"action": "add_task", "raw": t}
    if low in ("list tasks", "show tasks", "my tasks"):
        return {"action": "list_tasks"}
    if low.startswith("complete task "):
        return {"action": "complete_task", "raw": t}
    if low.startswith("delete task "):
        return {"action": "delete_task", "raw": t}

    return {"action": "none"}