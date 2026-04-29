from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import urllib.parse
import webbrowser
import re

from search.email_parse import parse_email_command
from integrations.email_router import EmailRouter
from integrations.calendar_router import CalendarRouter
from integrations.tasks_router import TasksRouter


class AgentSkills:
    """
    Phase 12.3+ skill set:
    - Draft email
    - Save last email draft
    - Send last draft (real provider or mailto fallback)
    - Connect Gmail/Outlook
    - Direct send command parsing
    - Confirmation flow (confirm/cancel send)
    - Attachment support
    - Natural language fallback (write/send in any style)
    - Meeting summary
    - Daily brief
    - Calendar hooks
    - Task hooks
    """

    def __init__(self, groq_client, memory, search, config):
        self.groq = groq_client
        self.memory = memory
        self.search = search
        self.config = config

        self.email_router = EmailRouter(config)
        self.calendar_router = CalendarRouter(config)
        self.tasks_router = TasksRouter(config)

        self.last_email_draft = None  # {to, subject, body, created_at, attachments}
        self.pending_email_send = None  # {to, subject, body, provider, attachments, source}

    async def handle(self, text: str) -> Optional[str]:
        text = text or ""
        low = text.lower().strip()

        parsed = parse_email_command(text)
        action = parsed.get("action", "none")

        # ------------------------------------------------------------------
        # 1) Provider settings and connect
        # ------------------------------------------------------------------
        if action == "set_provider":
            provider = (parsed.get("provider") or "").lower().strip()
            if provider not in {"gmail", "outlook"}:
                return "Unknown provider. Use: gmail or outlook."
            self.memory.set_preference("email_provider", provider)
            return f"Default email provider set to {provider}."

        if action == "connect_provider":
            provider = (parsed.get("provider") or "").lower().strip()
            if provider not in {"gmail", "outlook"}:
                return "Unknown provider. Use: connect gmail / connect outlook"
            return self.email_router.connect(provider)

        # ------------------------------------------------------------------
        # 2) Confirm / cancel email send
        # ------------------------------------------------------------------
        if action == "confirm_send":
            return self._confirm_pending_send()

        if action == "cancel_send":
            self.pending_email_send = None
            return "Email send cancelled."

        # ------------------------------------------------------------------
        # 3) Drafting + attachments
        # ------------------------------------------------------------------
        if action == "draft_email":
            return await self._skill_draft_email(parsed.get("prompt", text))

        if action == "attach_last_draft":
            return self._attach_to_last_draft(parsed.get("path", ""))

        # ------------------------------------------------------------------
        # 4) Prepare send (requires confirm)
        # ------------------------------------------------------------------
        if action == "prepare_send_last_draft":
            to_override = parsed.get("to")
            return self._prepare_send_last_draft(to_override=to_override)

        if action == "prepare_send_direct":
            to = parsed.get("to", "")
            subject = parsed.get("subject", "Quick Email")
            body = parsed.get("body", "")
            provider = parsed.get("provider") or self.memory.get_preference(
                "email_provider", getattr(self.config, "EMAIL_PROVIDER_DEFAULT", "gmail")
            )
            attachments = parsed.get("attachments") or []
            return self._prepare_send_direct(to, subject, body, provider, attachments)

        # ------------------------------------------------------------------
        # 5) Backward-compatible explicit commands
        # ------------------------------------------------------------------
        if low in {"connect gmail", "gmail connect"}:
            return self.email_router.connect("gmail")

        if low in {"connect outlook", "outlook connect"}:
            return self.email_router.connect("outlook")

        if low.startswith("draft email to "):
            return await self._skill_draft_email(text)

        if low in {"save email draft", "save draft", "save last draft"}:
            return self._save_last_email_draft()

        if low in {"send last draft", "send draft", "send it", "send this draft"}:
            return self._prepare_send_last_draft()

        if low.startswith("send email to "):
            return self._prepare_send_from_legacy_command(text)

        # ------------------------------------------------------------------
        # 6) Calendar hooks
        # ------------------------------------------------------------------
        if action == "connect_calendar":
            return self.calendar_router.connect(parsed.get("provider", "google"))

        if action == "create_meeting":
            return self.calendar_router.create_meeting(parsed.get("raw", text))

        if action == "list_meetings_today":
            return self.calendar_router.list_today()

        # ------------------------------------------------------------------
        # 7) Tasks hooks
        # ------------------------------------------------------------------
        if action == "add_task":
            return self.tasks_router.add_task(parsed.get("raw", text))

        if action == "list_tasks":
            return self.tasks_router.list_tasks()

        if action == "complete_task":
            return self.tasks_router.complete_task(parsed.get("raw", text))

        if action == "delete_task":
            return self.tasks_router.delete_task(parsed.get("raw", text))

        # ------------------------------------------------------------------
        # 8) Other existing skills
        # ------------------------------------------------------------------
        if low.startswith("summarize meeting:") or low.startswith("meeting summary:"):
            return await self._skill_meeting_summary(text)

        if low in {"daily brief", "give me daily brief", "morning brief"}:
            return await self._skill_daily_brief()

        # ------------------------------------------------------------------
        # 9) NATURAL LANGUAGE FALLBACK (ANY STYLE)
        # ------------------------------------------------------------------
        fallback = await self._handle_natural_language_email(text)
        if fallback is not None:
            return fallback

        return None

    # ------------------------------------------------------------------
    # Natural language fallback
    # ------------------------------------------------------------------
    async def _handle_natural_language_email(self, text: str) -> Optional[str]:
        low = (text or "").lower()
        email_in_text = self._extract_any_email(text)

        # If user expresses "send" intent in any style
        if self._looks_like_send_intent(text):
            # If there is a draft, use that + optional recipient override
            if self.last_email_draft:
                if email_in_text:
                    self.last_email_draft["to"] = email_in_text
                return self._prepare_send_last_draft()

            # No draft, but email present: prepare direct send using message as body
            if email_in_text:
                subject = self._extract_subject_hint(text)
                provider = self.memory.get_preference(
                    "email_provider", getattr(self.config, "EMAIL_PROVIDER_DEFAULT", "gmail")
                )
                return self._prepare_send_direct(
                    to=email_in_text,
                    subject=subject,
                    body=text.strip(),
                    provider=provider,
                    attachments=[],
                )

        # If user expresses draft/compose intent in any style
        if self._looks_like_draft_intent(text):
            # Normalize into your draft path so last_email_draft is always saved
            normalized = f"draft email to {text.strip()}"
            return await self._skill_draft_email(normalized)

        return None

    def _extract_any_email(self, text: str) -> Optional[str]:
        m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text or "")
        return m.group(0) if m else None

    def _looks_like_send_intent(self, text: str) -> bool:
        low = (text or "").lower()
        return any(w in low for w in ["send", "mail", "email", "forward", "deliver"])

    def _looks_like_draft_intent(self, text: str) -> bool:
        low = (text or "").lower()
        return any(w in low for w in ["write", "draft", "compose", "letter", "make mail", "create email"])

    def _extract_subject_hint(self, text: str) -> str:
        low = (text or "").lower()
        for k in ["about", "regarding", "subject"]:
            token = f" {k} "
            if token in low:
                idx = low.find(token)
                guess = text[idx + len(token):].strip()
                return guess[:120] if guess else "Quick Email"
        return "Quick Email"

    # ------------------------------------------------------------------
    # Email drafting
    # ------------------------------------------------------------------
    async def _skill_draft_email(self, text: str) -> str:
        raw = text.strip()
        low = raw.lower()

        after = raw[len("draft email to "):].strip() if low.startswith("draft email to ") else raw
        recipient = "recipient"
        topic = "the requested topic"

        if " about " in after.lower():
            idx = after.lower().find(" about ")
            recipient = after[:idx].strip() or recipient
            topic = after[idx + len(" about "):].strip() or topic
        else:
            recipient = after.strip() or recipient

        tone = self.memory.get_preference("tone", "professional")
        brevity = self.memory.get_preference("brevity", "medium")
        user_name = self.memory.get_user_name() or ""

        prompt = (
            "Create a practical professional email draft.\n"
            "Return exactly this format:\n"
            "Subject: <one line>\n"
            "Body:\n"
            "<body text>\n\n"
            f"Recipient: {recipient}\n"
            f"Topic: {topic}\n"
            f"Tone: {tone}\n"
            f"Brevity: {brevity}\n"
            f"Sender name: {user_name}\n"
        )

        try:
            res = (await self.groq.chat(prompt) or "").strip()
            if not res:
                return "I couldn't draft the email right now."

            subject, body = self._parse_email_blocks(res)
            self.last_email_draft = {
                "to": recipient,
                "subject": subject,
                "body": body,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "attachments": [],
            }

            return (
                f"{res}\n\n"
                "Commands:\n"
                "- 'save draft'\n"
                "- 'attach C:\\path\\file.pdf'\n"
                "- 'send this mail to someone@example.com'\n"
                "- 'send last draft'\n"
                "- 'confirm send' / 'cancel send'"
            )
        except Exception:
            return "I couldn't draft the email right now."

    def _parse_email_blocks(self, draft_text: str):
        subject = "Draft Email"
        body = draft_text.strip()

        lines = draft_text.splitlines()
        for i, line in enumerate(lines):
            if line.lower().startswith("subject:"):
                subject = line.split(":", 1)[1].strip() or subject
                body_idx = None
                for j in range(i + 1, len(lines)):
                    if lines[j].lower().startswith("body:"):
                        body_idx = j + 1
                        break
                if body_idx is not None:
                    body = "\n".join(lines[body_idx:]).strip() or body
                break
        return subject, body

    def _save_last_email_draft(self) -> str:
        if not self.last_email_draft:
            return "No draft available. First run: draft email to ... about ..."

        drafts_dir = Path("exports/email_drafts")
        drafts_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_to = "".join(c for c in self.last_email_draft["to"] if c.isalnum() or c in ("-", "_", ".")).strip()
        safe_to = safe_to or "recipient"

        file_path = drafts_dir / f"draft_{safe_to}_{ts}.md"
        content = [
            "# Email Draft",
            "",
            f"- To: {self.last_email_draft['to']}",
            f"- Subject: {self.last_email_draft['subject']}",
            f"- Created: {self.last_email_draft['created_at']}",
            f"- Attachments: {', '.join(self.last_email_draft.get('attachments', [])) or 'None'}",
            "",
            "## Body",
            "",
            self.last_email_draft["body"],
            "",
        ]
        file_path.write_text("\n".join(content), encoding="utf-8")
        return f"Draft saved: {file_path}"

    # ------------------------------------------------------------------
    # Send prepare/confirm
    # ------------------------------------------------------------------
    def _prepare_send_last_draft(self, to_override: Optional[str] = None) -> str:
        if not self.last_email_draft:
            return "No draft available. First run: draft email to ... about ..."

        draft = dict(self.last_email_draft)

        if to_override:
            draft["to"] = to_override

        to = (draft.get("to") or "").strip()
        if not self._is_valid_email(to):
            return f"Recipient is missing or invalid: '{to}'. Please provide a valid email."

        provider = self.memory.get_preference("email_provider", getattr(self.config, "EMAIL_PROVIDER_DEFAULT", "gmail"))
        provider = (provider or "gmail").lower()

        attachments = draft.get("attachments") or []
        bad = self._invalid_attachments(attachments)
        if bad:
            return f"Attachment file(s) not found: {', '.join(bad)}"

        self.pending_email_send = {
            "to": to,
            "subject": draft.get("subject", "Draft Email"),
            "body": draft.get("body", ""),
            "provider": provider,
            "attachments": attachments,
            "source": "last_draft",
        }
        return self._pending_summary()

    def _prepare_send_direct(self, to: str, subject: str, body: str, provider: str, attachments: List[str]) -> str:
        to = (to or "").strip()
        provider = (provider or "gmail").lower().strip()

        if not self._is_valid_email(to):
            return f"Invalid recipient email: {to}"

        bad = self._invalid_attachments(attachments)
        if bad:
            return f"Attachment file(s) not found: {', '.join(bad)}"

        self.pending_email_send = {
            "to": to,
            "subject": subject or "Quick Email",
            "body": body or "",
            "provider": provider,
            "attachments": attachments or [],
            "source": "direct",
        }
        return self._pending_summary()

    def _prepare_send_from_legacy_command(self, text: str) -> str:
        raw = text.strip()
        low = raw.lower()

        after = raw[len("send email to "):].strip() if low.startswith("send email to ") else raw
        to = after
        subject = "Quick Email"
        body = ""
        provider = self.memory.get_preference("email_provider", getattr(self.config, "EMAIL_PROVIDER_DEFAULT", "gmail"))
        attachments = []

        low_after = after.lower()

        p_idx = low_after.rfind(" provider ")
        if p_idx != -1:
            provider = after[p_idx + len(" provider "):].strip() or provider
            after = after[:p_idx].strip()
            low_after = after.lower()

        a_idx = low_after.rfind(" attachment ")
        if a_idx != -1:
            att = after[a_idx + len(" attachment "):].strip()
            if att:
                attachments.append(att)
            after = after[:a_idx].strip()
            low_after = after.lower()

        s_idx = low_after.find(" subject ")
        b_idx = low_after.find(" body ")

        if s_idx != -1 and b_idx != -1 and s_idx < b_idx:
            to = after[:s_idx].strip()
            subject = after[s_idx + len(" subject "):b_idx].strip() or subject
            body = after[b_idx + len(" body "):].strip()
        elif s_idx != -1:
            to = after[:s_idx].strip()
            subject = after[s_idx + len(" subject "):].strip() or subject
        elif b_idx != -1:
            to = after[:b_idx].strip()
            body = after[b_idx + len(" body "):].strip()

        return self._prepare_send_direct(to, subject, body, provider, attachments)

    def _confirm_pending_send(self) -> str:
        if not self.pending_email_send:
            return "No pending email to send. Use 'send last draft' or 'send email to ...' first."

        p = self.pending_email_send
        result = self._send_direct_with_fallback(
            to=p["to"],
            subject=p["subject"],
            body=p["body"],
            provider=p["provider"],
            attachments=p.get("attachments", []),
        )
        self.pending_email_send = None
        return result

    def _pending_summary(self) -> str:
        p = self.pending_email_send or {}
        atts = p.get("attachments") or []
        att_line = ", ".join(atts) if atts else "None"
        return (
            "Ready to send email:\n"
            f"- To: {p.get('to','')}\n"
            f"- Subject: {p.get('subject','')}\n"
            f"- Provider: {p.get('provider','gmail')}\n"
            f"- Attachments: {att_line}\n\n"
            "Reply with 'confirm send' to send or 'cancel send' to cancel."
        )

    def _attach_to_last_draft(self, file_path: str) -> str:
        if not self.last_email_draft:
            return "No draft available. First create a draft, then attach file."

        path = (file_path or "").strip().strip('"').strip("'")
        if not path:
            return "Attachment path missing. Example: attach C:\\docs\\plan.pdf"

        p = Path(path)
        if not p.exists() or not p.is_file():
            return f"Attachment file not found: {path}"

        attachments = self.last_email_draft.get("attachments") or []
        if str(p) not in attachments:
            attachments.append(str(p))
        self.last_email_draft["attachments"] = attachments
        return f"Attached to last draft: {p}"

    def _send_direct_with_fallback(
        self,
        to: str,
        subject: str,
        body: str,
        provider: str,
        attachments: Optional[List[str]] = None,
    ) -> str:
        if not self._is_valid_email(to):
            return f"Invalid recipient email: {to}"

        attachments = attachments or []
        bad = self._invalid_attachments(attachments)
        if bad:
            return f"Attachment file(s) not found: {', '.join(bad)}"

        try:
            result = self.email_router.send(
                to=to,
                subject=subject,
                body=body,
                provider=provider,
                attachments=attachments,
            )
        except TypeError:
            # fallback if router doesn't yet accept attachments
            result = self.email_router.send(
                to=to,
                subject=subject,
                body=body,
                provider=provider,
            )

        low_res = (result or "").lower()
        if "not connected" in low_res or "missing" in low_res or "unknown provider" in low_res:
            return result + "\n" + self._open_mailto(to, subject, body)

        return result

    def _open_mailto(self, to: str, subject: str, body: str) -> str:
        to_q = urllib.parse.quote((to or "").strip())
        sub_q = urllib.parse.quote(subject or "")
        body_q = urllib.parse.quote(body or "")
        url = f"mailto:{to_q}?subject={sub_q}&body={body_q}"

        try:
            ok = webbrowser.open(url, new=1)
            if ok:
                return "Opened your default mail app with prefilled draft."
            return "Tried opening mail app, but system blocked it."
        except Exception as e:
            return f"Could not open mail app: {e}"

    # ------------------------------------------------------------------
    # Meeting summary
    # ------------------------------------------------------------------
    async def _skill_meeting_summary(self, text: str) -> str:
        notes = text.split(":", 1)[1].strip() if ":" in text else ""
        if not notes:
            return "Please provide notes after 'summarize meeting:'."

        tone = self.memory.get_preference("tone", "clear")
        brevity = self.memory.get_preference("brevity", "medium")

        prompt = (
            "Summarize these meeting notes in sections:\n"
            "1) Summary\n2) Key Decisions\n3) Action Items\n4) Risks/Blockers\n"
            "If owner unknown, write Owner: Unassigned.\n"
            f"Tone: {tone}; Brevity: {brevity}\n\n"
            f"{notes}"
        )
        try:
            res = await self.groq.chat(prompt)
            return res.strip() if res else "I couldn't summarize the meeting notes right now."
        except Exception:
            return "I couldn't summarize the meeting notes right now."

    # ------------------------------------------------------------------
    # Daily brief
    # ------------------------------------------------------------------
    async def _skill_daily_brief(self) -> str:
        city = self.memory.get_preference("city", "New York")
        weather_line = await self._get_weather_line(city)
        headlines = await self.search.search("latest world headlines", max_results=5)

        lines = [
            f"Daily Brief ({datetime.now().strftime('%Y-%m-%d %H:%M')})",
            "",
            f"Weather ({city}): {weather_line}",
            "",
            "Top Headlines:"
        ]

        if not headlines:
            lines.append("- Could not fetch headlines right now.")
        else:
            for i, h in enumerate(headlines[:5], 1):
                lines.append(f"{i}. {h.get('title', 'No title')}")
                if h.get("url"):
                    lines.append(f"   Source: {h['url']}")

        return "\n".join(lines)

    async def _get_weather_line(self, city: str) -> str:
        try:
            rs = await self.search.search(f"current weather in {city}", max_results=3)
            if not rs:
                return "Unavailable right now."
            return rs[0].get("snippet", "Available via live sources.")
        except Exception:
            return "Unavailable right now."

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------
    def _is_valid_email(self, email: str) -> bool:
        return re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", (email or "").strip()) is not None

    def _invalid_attachments(self, paths: List[str]) -> List[str]:
        bad = []
        for p in paths or []:
            x = Path((p or "").strip().strip('"').strip("'"))
            if not x.exists() or not x.is_file():
                bad.append(str(x))
        return bad