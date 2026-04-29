from pathlib import Path
from datetime import datetime
import json
from typing import List, Dict, Optional
import re
import urllib.parse
import webbrowser

from core.smart_open import handle_search_shortcut, open_target
from core.commands import CommandRouter
from core.memory import MemoryStore
from nlp.groq_client import GroqClient
from nlp.tts import TTS
from search.web import WebSearch


class Orchestrator:
    """
    EDITH Orchestrator with improved deterministic routing for:
      - send message / sms / whatsapp commands
      - email composition commands
      - essay/article/paragraph generation (explicitly handled, not turned into email)
    """

    def __init__(self, config):
        self.config = config
        self.groq = GroqClient(config)
        self.memory = MemoryStore(config.DB_PATH)
        self.search = WebSearch(
            openweather_api_key=getattr(config, "OPENWEATHER_API_KEY", "05dae85c1eeba9c43924fce31778ce9b"),
            bing_api_key=getattr(config, "BING_API_KEY", ""),
            bing_endpoint=getattr(config, "BING_ENDPOINT", ""),
        )
        self.commands = CommandRouter(
            groq_client=self.groq,
            openweather_api_key=getattr(config, "OPENWEATHER_API_KEY", "05dae85c1eeba9c43924fce31778ce9b"),
            config=config
        )
        self.tts = TTS(enabled=getattr(config, "ENABLE_TTS", True))

        self.pending_action = None
        self.mode = "assistant"

        self.wake_enabled = True
        self.wake_word = "edith"

        tts_pref = self.memory.get_preference("tts_enabled", None)
        if isinstance(tts_pref, bool):
            self.tts.set_enabled(tts_pref)

    

    def _is_email_verb(self, low: str) -> bool:
        return any(w in low for w in ("email", "e-mail", "mail", "compose email", "send email", "draft email"))

    def _is_send_message_verb(self, low: str) -> bool:
        # text / sms / send message / whatsapp
        return any(w in low for w in ("send message", "send sms", "send sms to", "text ", " sms ", "whatsapp", "send whatsapp", "message to ", "send to "))

    async def _try_compose_tasks(self, text: str, low: str) -> Optional[str]:
        """
        Handle explicit 'write essay / article / paragraph / blog' commands deterministically.
        This prevents LLM intent routing from interpreting them as 'compose email'.
        Returns assistant reply string if handled, otherwise None.
        """
        
        m = re.match(r"^(write|compose|make|draft)\s+(an\s+)?(essay|article|paragraph|blog)(\s+(on|about)\s+(.+))?$", low)
        if m:
            topic = (m.group(6) or "").strip()
            if not topic:
                # ask for topic
                return "What should the essay be about?"
            style_hint = self._profile_style_prefix()
            prompt = (
                f"You are EDITH. {style_hint}\n\n"
                f"Write a clear, well-structured essay about: {topic}\n"
                "- Use 3 short paragraphs.\n"
                "- Keep language engaging and easy to read.\n"
                "- Do not format as an email; do not include salutations or signatures."
            )
            try:
                ans = await self.groq.chat(prompt)
                return ans or "I could not generate the essay right now."
            except Exception:
                return "I could not generate the essay right now (service error)."

        
        m2 = re.match(r"^(essay|article|paragraph)\s+(on|about)\s+(.+)$", low)
        if m2:
            topic = m2.group(3).strip()
            style_hint = self._profile_style_prefix()
            prompt = (
                f"You are EDITH. {style_hint}\n\n"
                f"Write a clear essay about: {topic}\n"
                "- 3 short paragraphs.\n"
                "- Do not write as an email."
            )
            try:
                ans = await self.groq.chat(prompt)
                return ans or "I could not generate the essay right now."
            except Exception:
                return "I could not generate the essay right now (service error)."

        return None

    async def _try_send_message(self, text: str, low: str) -> Optional[str]:
        """
        Try to route explicit send/text/sms/whatsapp commands to the CommandRouter
        (where message delivery logic should live). If CommandRouter handles it,
        return its result via _done pipeline. Otherwise return None to continue flow.
        """
        
        if self._is_email_verb(low):
            return None

    
        patterns = [
            r"^(send|text|sms)\s+(.+?)\s+(saying|say|says|:|-)\s+(.+)$",
            r"^(send|text|sms)\s+(.+?)\s+to\s+(.+?)\s*(?:\:|-)\s*(.+)$",
            r"^(text|send|whatsapp|whatsapp message)\s+(.+?)\s+(to|:)\s+(.+)$",
            r"^send\s+(a\s+)?message\s+to\s+(.+?)\s*(?:\:|-)\s*(.+)$",
            r"^(.+?)\s+ko\s+(message|sms|text)\s+bhejo\s*(?:\:|-)\s*(.+)$",  
            r"^(.+?)\s+ko\s+(message|sms|text)\s+bhejo$",  
        ]

        for pat in patterns:
            m = re.match(pat, low)
            if m:
                
                try:
                    cmd = await self.commands.try_execute(text, self.search, memory=self.memory)
                except Exception:
                    cmd = None

                if isinstance(cmd, dict) and cmd.get("requires_confirmation"):
                    # Let the caller handle confirmation flow
                    self.pending_action = cmd.get("pending_action")
                    return cmd.get("message", "This action needs confirmation. Type yes/no.")
                if isinstance(cmd, str):
                    return cmd

                
                return "I couldn't send that automatically. Do you want me to open the messaging app or draft it here?"

       
        m2 = re.match(r"^(text|send)\s+(.+?)\s+(.+)$", low)
        if m2:
         
            try:
                cmd = await self.commands.try_execute(text, self.search, memory=self.memory)
            except Exception:
                cmd = None

            if isinstance(cmd, dict) and cmd.get("requires_confirmation"):
                self.pending_action = cmd.get("pending_action")
                return cmd.get("message", "This action needs confirmation. Type yes/no.")
            if isinstance(cmd, str):
                return cmd

            # ask clarification if ambiguous
            return "Do you want to send that as an SMS, WhatsApp message, or email?"

        return None

    async def _try_email_compose(self, text: str, low: str) -> Optional[str]:
        """
        Deterministically handle explicit email compose/send commands by forwarding
        to CommandRouter. This prevents generic LLM completions from mislabeling.
        """
        if not self._is_email_verb(low):
            return None


        try:
            cmd = await self.commands.try_execute(text, self.search, memory=self.memory)
        except Exception:
            cmd = None

        if isinstance(cmd, dict) and cmd.get("requires_confirmation"):
            self.pending_action = cmd.get("pending_action")
            return cmd.get("message", "This action needs confirmation. Type yes/no.")
        if isinstance(cmd, str):
            return cmd

        return "I couldn't send that email automatically. Would you like me to draft it here?"


    def _is_web_priority_query(self, text: str) -> bool:
        t = text.lower().strip()
        keys = [
            "latest", "news", "today", "current", "now", "live", "update", "breaking",
            "price", "rate", "stock", "crypto", "market", "war", "election", "result",
            "time in", "weather in", "headline", "headlines"
        ]
        return any(k in t for k in keys)

    def _is_short_general_query(self, text: str) -> bool:
        return len(text.strip().split()) <= 12

    def _freshness_label_from_results(self, results: List[Dict]) -> str:
        for r in results:
            fm = (r.get("freshness_mode") or "").strip()
            if fm == "24h":
                return "Freshness window: last 24 hours"
            if fm == "7d":
                return "Freshness window: last 7 days"
            if fm == "30d":
                return "Freshness window: last 30 days"
        return ""

    def _profile_style_prefix(self) -> str:
        name = self.memory.get_user_name() or ""
        tone = self.memory.get_preference("tone", "clear")
        brevity = self.memory.get_preference("brevity", "medium")

        parts = []
        if name:
            parts.append(f"User name: {name}.")
        parts.append(f"Preferred tone: {tone}.")
        parts.append(f"Preferred brevity: {brevity}.")
        parts.append("Follow these preferences in your reply.")
        return " ".join(parts)

    def _should_skip_speaking(self, assistant_text: str) -> bool:
        low = (assistant_text or "").lower().strip()
        silent = {
            "noted.",
            "cancelled.",
            "stopped speaking.",
            "please reply with 'yes' or 'no'.",
            "switched to chat mode.",
            "switched to assistant mode.",
        }
        return low in silent

    async def _handle_pending(self, low: str) -> Optional[str]:
        if self.pending_action is None:
            return None

        if low in {"yes", "y", "confirm"}:
            result = await self.commands.execute_pending(self.pending_action, self.search)
            self.pending_action = None
            return result

        if low in {"no", "n", "cancel"}:
            self.pending_action = None
            return "Cancelled."

        return "Please reply with 'yes' or 'no'."

    def _try_profile_commands(self, text: str, low: str) -> Optional[str]:
        if low.startswith("my name is "):
            name = text[len("my name is "):].strip()
            if name:
                self.memory.set_user_name(name)
                return f"Got it. I'll remember your name as {name}."

        if low.startswith("call me "):
            name = text[len("call me "):].strip()
            if name:
                self.memory.set_user_name(name)
                return f"Sure. I'll call you {name}."

        if low in {"forget my name", "remove my name"}:
            self.memory.delete_profile_key("user.name")
            return "Okay, I forgot your name."

        if low.startswith("set tone "):
            tone = text[len("set tone "):].strip().lower()
            if tone:
                self.memory.set_preference("tone", tone)
                return f"Done. Preferred tone set to {tone}."

        if low.startswith("set brevity "):
            brev = text[len("set brevity "):].strip().lower()
            if brev in {"short", "medium", "long"}:
                self.memory.set_preference("brevity", brev)
                return f"Done. Preferred brevity set to {brev}."
            return "Please use: set brevity short|medium|long."

        if low.startswith("set city "):
            city = text[len("set city "):].strip()
            if city:
                self.memory.set_preference("city", city)
                return f"Done. Default city set to {city}."

        if low.startswith("set email provider "):
            p = text[len("set email provider "):].strip().lower()
            if p not in {"gmail", "outlook"}:
                return "Use: set email provider gmail|outlook"
            self.memory.set_preference("email_provider", p)
            return f"Default email provider set to {p}."

        if low in {"show preferences", "show prefs", "my preferences"}:
            profile = self.memory.get_all_profile()
            if not profile:
                return "No saved preferences yet."
            lines = ["Saved preferences/profile:"]
            for k, v in profile.items():
                lines.append(f"- {k}: {v}")
            return "\n".join(lines)

        if low.startswith("forget preference "):
            k = text[len("forget preference "):].strip()
            if not k:
                return "Please specify a preference key."
            self.memory.delete_profile_key(f"pref.{k}")
            return f"Removed preference pref.{k}."

        return None

    def _try_voice_commands(self, low: str) -> Optional[str]:
        if low in {"stop speaking", "stop voice"}:
            self.tts.stop()
            return "Stopped speaking."

        if low in {"mute", "mute now", "voice off"}:
            self.tts.set_enabled(False)
            self.memory.set_preference("tts_enabled", False)
            return "Voice output muted."

        if low in {"unmute", "voice on"}:
            self.tts.set_enabled(True)
            self.memory.set_preference("tts_enabled", True)
            return "Voice output enabled."

        if low in {"are you speaking", "speaking status", "voice status"}:
            return "I am speaking." if self.tts.is_speaking() else "I am not speaking."

        if low in {"wake word off", "disable wake word"}:
            self.wake_enabled = False
            return "Wake word disabled."

        if low in {"wake word on", "enable wake word"}:
            self.wake_enabled = True
            return "Wake word enabled."

        return None

    def _build_evidence_block(self, results: List[Dict], limit: int = 6) -> str:
        blocks = []
        for i, r in enumerate(results[:limit], 1):
            title = r.get("title", "No title")
            snippet = r.get("snippet", "")
            url = r.get("url", "")
            pub = r.get("published_at", "")
            pub_line = f"\nPublished (UTC): {pub}" if pub else ""
            blocks.append(
                f"[{i}] {title}\n"
                f"Snippet: {snippet}\n"
                f"URL: {url}{pub_line}"
            )
        return "\n\n".join(blocks)

    def _build_sources_block(self, results: List[Dict], limit: int = 5) -> str:
        lines = ["Sources:"]
        seen = set()
        c = 0
        for r in results:
            title = (r.get("title") or "No title").strip()
            url = (r.get("url") or "").strip()
            if not url or url in seen:
                continue
            seen.add(url)
            lines.append(f"- {title} - {url}")
            c += 1
            if c >= limit:
                break
        if c == 0:
            return "Sources: (no URL available)"
        return "\n".join(lines)

    async def _answer_from_web(self, query: str) -> Optional[str]:
        results = await self.search.search(query, max_results=8)
        if not results:
            return None

        freshness = self._freshness_label_from_results(results)
        evidence = self._build_evidence_block(results, limit=6)
        style = self._profile_style_prefix()

        prompt = (
            "You are EDITH.\n"
            f"{style}\n"
            "Answer ONLY using provided live web evidence.\n"
            "Rules:\n"
            "- Give concise direct answer first.\n"
            "- If developing story, add one short caution.\n"
            "- Do not mention knowledge cutoff.\n"
            "- End with Sources and 3-5 links.\n\n"
            f"User query: {query}\n"
            f"{freshness}\n\n"
            f"Evidence:\n{evidence}"
        )

        try:
            ans = (await self.groq.chat(prompt) or "").strip()
            if ans:
                if freshness and freshness not in ans:
                    ans = f"{freshness}\n\n{ans}"
                if "Sources:" not in ans:
                    ans = f"{ans}\n\n{self._build_sources_block(results)}"
                return ans
        except Exception:
            pass

        lines = []
        if freshness:
            lines.append(freshness)
            lines.append("")
        lines.append("Here are relevant live results:")
        for i, r in enumerate(results[:5], 1):
            lines.append(f"{i}. {r.get('title', 'No title')}")
            if r.get("published_at"):
                lines.append(f"   Published (UTC): {r['published_at']}")
            if r.get("snippet"):
                lines.append(f"   {r['snippet']}")
            if r.get("url"):
                lines.append(f"   Source: {r['url']}")
        return "\n".join(lines)



    async def handle(self, user_input: str) -> str:
        text = (user_input or "").strip()
        low = text.lower()
        if not text:
            return ""

        
        handled, msg = handle_search_shortcut(text)
        if handled:
            return self._done(msg)

      
        handled, msg = open_target(text)
        if handled:
            return self._done(msg)

        self.memory.log("user", text)

        if low == "mode chat":
            self.mode = "chat"
            return self._done("Switched to chat mode.")
        if low == "mode assistant":
            self.mode = "assistant"
            return self._done("Switched to assistant mode.")

        
        voice_cmd = self._try_voice_commands(low)
        if voice_cmd is not None:
            return self._done(voice_cmd)

        if low.startswith("remember "):
            self.memory.set_note(text[len("remember "):].strip())
            return self._done("Noted.")

        if low == "recall":
            note = self.memory.get_note()
            return self._done(note if note else "I don't have any saved note yet.")

        prof_cmd = self._try_profile_commands(text, low)
        if prof_cmd is not None:
            return self._done(prof_cmd)

        pending_reply = await self._handle_pending(low)
        if pending_reply is not None:
            return self._done(pending_reply)

       
        compose_result = await self._try_compose_tasks(text, low)
        if compose_result is not None:
            return self._done(compose_result)

 
        send_result = await self._try_send_message(text, low)
        if send_result is not None:
            return self._done(send_result)

        email_result = await self._try_email_compose(text, low)
        if email_result is not None:
            return self._done(email_result)

    
        if self.mode == "assistant":
            cmd = await self.commands.try_execute(text, self.search, memory=self.memory)

            if isinstance(cmd, dict) and cmd.get("requires_confirmation"):
                self.pending_action = cmd.get("pending_action")
                return self._done(cmd.get("message", "This action needs confirmation. Type yes/no."))

            if isinstance(cmd, str):
                return self._done(cmd)

        
        if self._is_web_priority_query(text) or self._is_short_general_query(text):
            web_ans = await self._answer_from_web(text)
            if web_ans:
                return self._done(web_ans)

            if self._is_web_priority_query(text):
                return self._done(
                    "I could not fetch live web results right now (network/provider issue). Please retry in a moment."
                )

        
        style = self._profile_style_prefix()
        reply = await self.groq.chat(f"{style}\n\nUser: {text}")
        return self._done(reply)

    def _done(self, assistant_text: str) -> str:
        self.memory.log("assistant", assistant_text)

       
        if assistant_text and not self._should_skip_speaking(assistant_text):
            self.tts.speak(assistant_text)
        return assistant_text