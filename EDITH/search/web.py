import re
import time
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse, quote_plus
from xml.etree import ElementTree as ET
from typing import List, Dict, Optional

import requests
from duckduckgo_search import DDGS


class WebSearch:
    """
    Unified WebSearch (keeps your old behavior and structure):
    - News pipeline:
      Google News RSS + Bing News RSS + DDG News
    - Non-news pipeline:
      DDG Text + Wikipedia fallback
    - Freshness filtering for news
    - Ranking, dedupe, and cache
    - Result schema:
      {
        "title": str,
        "url": str,
        "snippet": str,
        "published_at": str (ISO UTC or ""),
        "freshness_mode": "24h" | "7d" | "30d" | ""
      }
    """

    def __init__(self, openweather_api_key: str = "", bing_api_key: str = "", bing_endpoint: str = ""):
        self.openweather_api_key = openweather_api_key
        self.bing_api_key = bing_api_key or ""
        self.bing_endpoint = bing_endpoint or "https://api.bing.microsoft.com/v7.0/search"

        self._cache: Dict[str, Dict] = {}
        self._cache_ttl_seconds = 60

    async def search(self, query: str, max_results: int = 8) -> List[Dict]:
        q = (query or "").strip()
        if not q:
            return []

        cache_key = f"{q.lower()}::{max_results}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        is_news = self._is_news_query(q)
        mode = self._freshness_mode(q) if is_news else ""

        if is_news:
            pool: List[Dict] = []

            gnews = self._search_google_news_rss(q, max_results=max_results * 3)
            pool.extend(gnews)

            bing_news = self._search_bing_news_rss(q, max_results=max_results * 3)
            pool.extend(bing_news)

            ddg_news = self._search_ddg_news(q, max_results=max_results * 2)
            pool.extend(ddg_news)

            # Optional: Bing Web API if key exists
            # Useful when RSS coverage is weak.
            if self.bing_api_key:
                bing_web = self._search_bing_web_api(q, max_results=max_results * 2)
                pool.extend(bing_web)

            pool = self._dedupe_by_url(pool)
            pool = self._apply_news_freshness_filter(mode, pool)
            pool = self._rank_and_filter(q, pool, max_results=max_results)

            for r in pool:
                r["freshness_mode"] = mode

            self._cache_set(cache_key, pool)
            return pool

        # non-news
        ddg = self._search_ddg_text(q, max_results=max_results * 2)
        ddg = self._rank_and_filter(q, ddg, max_results=max_results)
        ddg = self._dedupe_by_url(ddg)
        for r in ddg:
            r["freshness_mode"] = ""

        if ddg:
            self._cache_set(cache_key, ddg)
            return ddg

        wiki = self._search_wikipedia(q, max_results=max_results)
        wiki = self._rank_and_filter(q, wiki, max_results=max_results)
        wiki = self._dedupe_by_url(wiki)
        for r in wiki:
            r["freshness_mode"] = ""

        self._cache_set(cache_key, wiki)
        return wiki

    # ---------------- query helpers ----------------
    def _is_news_query(self, query: str) -> bool:
        q = query.lower()
        keys = [
            "news", "latest", "today", "breaking", "current", "update",
            "war", "election", "conflict", "headline", "headlines"
        ]
        return any(k in q for k in keys)

    def _freshness_mode(self, query: str) -> str:
        q = query.lower()
        if any(k in q for k in ["today", "now", "just now", "breaking"]):
            return "24h"
        if any(k in q for k in ["latest", "current"]):
            return "7d"
        return "30d"

    # ---------------- provider: google news rss ----------------
    def _search_google_news_rss(self, query: str, max_results: int = 24) -> List[Dict]:
        try:
            url = "https://news.google.com/rss/search"
            params = {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"}
            r = requests.get(url, params=params, timeout=15)
            if r.status_code != 200:
                return []
            return self._parse_rss_items(r.text, max_results=max_results)
        except Exception:
            return []

    # ---------------- provider: bing news rss ----------------
    def _search_bing_news_rss(self, query: str, max_results: int = 24) -> List[Dict]:
        try:
            q = quote_plus(query)
            url = f"https://www.bing.com/news/search?q={q}&format=rss"
            r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200:
                return []
            return self._parse_rss_items(r.text, max_results=max_results)
        except Exception:
            return []

    # ---------------- provider: ddg news ----------------
    def _search_ddg_news(self, query: str, max_results: int = 16) -> List[Dict]:
        try:
            with DDGS() as ddgs:
                rows = list(ddgs.news(query, max_results=max_results))

            out: List[Dict] = []
            for it in rows:
                title = (it.get("title") or "").strip()
                url = (it.get("url") or "").strip()
                snippet = (it.get("body") or "").strip()
                date_raw = (it.get("date") or "").strip()

                pub_iso = ""
                if date_raw:
                    try:
                        dt = datetime.fromisoformat(date_raw.replace("Z", "+00:00"))
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        pub_iso = dt.astimezone(timezone.utc).isoformat()
                    except Exception:
                        pub_iso = ""

                if title and url:
                    out.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet,
                        "published_at": pub_iso
                    })
            return out
        except Exception:
            return []

    # ---------------- optional provider: bing web api ----------------
    def _search_bing_web_api(self, query: str, max_results: int = 12) -> List[Dict]:
        if not self.bing_api_key:
            return []
        try:
            headers = {"Ocp-Apim-Subscription-Key": self.bing_api_key}
            params = {
                "q": query,
                "count": max(1, min(max_results, 20)),
                "mkt": "en-US",
                "textDecorations": False,
                "textFormat": "Raw",
                "sortBy": "Date",
            }
            r = requests.get(self.bing_endpoint, headers=headers, params=params, timeout=15)
            if r.status_code != 200:
                return []
            data = r.json()

            out: List[Dict] = []
            for it in data.get("webPages", {}).get("value", []):
                title = (it.get("name") or "").strip()
                url = (it.get("url") or "").strip()
                snippet = (it.get("snippet") or "").strip()
                pub_iso = self._parse_possible_datetime(
                    it.get("datePublished") or it.get("dateLastCrawled") or ""
                )

                if title and url:
                    out.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet,
                        "published_at": pub_iso
                    })
            return out
        except Exception:
            return []

    # ---------------- non-news providers ----------------
    def _search_ddg_text(self, query: str, max_results: int = 12) -> List[Dict]:
        try:
            with DDGS() as ddgs:
                rows = list(ddgs.text(query, max_results=max_results))

            out = []
            for r in rows:
                out.append({
                    "title": (r.get("title") or "").strip(),
                    "url": (r.get("href") or "").strip(),
                    "snippet": (r.get("body") or "").strip(),
                    "published_at": ""
                })
            return [x for x in out if x["title"] and x["url"]]
        except Exception:
            return []

    def _search_wikipedia(self, query: str, max_results: int = 8) -> List[Dict]:
        try:
            url = "https://en.wikipedia.org/w/api.php"
            params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": max_results
            }
            r = requests.get(url, params=params, timeout=10)
            if r.status_code != 200:
                return []
            data = r.json()

            out = []
            for it in data.get("query", {}).get("search", []):
                title = (it.get("title") or "").strip()
                if not title:
                    continue
                out.append({
                    "title": title,
                    "url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                    "snippet": self._clean_html(it.get("snippet") or ""),
                    "published_at": ""
                })
            return out
        except Exception:
            return []

    # ---------------- parsing ----------------
    def _parse_rss_items(self, xml_text: str, max_results: int = 24) -> List[Dict]:
        out = []
        try:
            root = ET.fromstring(xml_text)
            items = root.findall(".//item")
            for it in items[:max_results]:
                title = (it.findtext("title") or "").strip()
                link = (it.findtext("link") or "").strip()
                desc = self._clean_html(it.findtext("description") or "")
                pub_raw = (it.findtext("pubDate") or "").strip()

                pub_iso = ""
                if pub_raw:
                    try:
                        dt = parsedate_to_datetime(pub_raw)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        pub_iso = dt.astimezone(timezone.utc).isoformat()
                    except Exception:
                        pub_iso = ""

                if title and link:
                    out.append({
                        "title": title,
                        "url": link,
                        "snippet": desc,
                        "published_at": pub_iso
                    })
        except Exception:
            return []
        return out

    def _parse_possible_datetime(self, raw: str) -> str:
        if not raw:
            return ""
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except Exception:
            pass
        try:
            dt = parsedate_to_datetime(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except Exception:
            return ""

    # ---------------- freshness/ranking ----------------
    def _apply_news_freshness_filter(self, mode: str, results: List[Dict]) -> List[Dict]:
        if not results:
            return []

        now_utc = datetime.now(timezone.utc)
        if mode == "24h":
            cutoff = now_utc - timedelta(hours=24)
        elif mode == "7d":
            cutoff = now_utc - timedelta(days=7)
        else:
            cutoff = now_utc - timedelta(days=30)

        kept = []
        for r in results:
            p = r.get("published_at", "")
            if not p:
                if mode in {"24h", "7d"}:
                    continue
                kept.append(r)
                continue
            try:
                dt = datetime.fromisoformat(p.replace("Z", "+00:00"))
                if dt >= cutoff:
                    kept.append(r)
            except Exception:
                continue

        def dt_key(x):
            p = x.get("published_at", "")
            if not p:
                return datetime(1970, 1, 1, tzinfo=timezone.utc)
            try:
                return datetime.fromisoformat(p.replace("Z", "+00:00"))
            except Exception:
                return datetime(1970, 1, 1, tzinfo=timezone.utc)

        kept.sort(key=dt_key, reverse=True)
        return kept

    def _rank_and_filter(self, query: str, results: List[Dict], max_results: int = 8) -> List[Dict]:
        if not results:
            return []

        q_terms = set(re.findall(r"[a-z0-9]+", query.lower()))
        bad_domains = {"aaronsw.com", "pinterest.com"}
        trusted_news = [
            "reuters.com", "apnews.com", "bbc.", "aljazeera.", "nytimes.com",
            "theguardian.com", "cnn.com", "npr.org", "wsj.com", "ft.com", "bloomberg.com"
        ]

        scored = []
        is_news = self._is_news_query(query)

        for r in results:
            title = (r.get("title") or "").lower()
            snippet = (r.get("snippet") or "").lower()
            url = (r.get("url") or "").lower()

            if not title or not url:
                continue
            if any(b in url for b in bad_domains):
                continue

            overlap = sum(1 for t in q_terms if t in f"{title} {snippet}")
            score = overlap

            if is_news and any(td in url for td in trusted_news):
                score += 3
            if r.get("published_at"):
                score += 1

            scored.append((score, r))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:max_results]]

    # ---------------- dedupe/cache/utils ----------------
    def _dedupe_by_url(self, results: List[Dict]) -> List[Dict]:
        seen = set()
        out = []
        for r in results:
            url = (r.get("url") or "").strip()
            if not url:
                continue
            norm = self._normalize_url(url)
            if norm in seen:
                continue
            seen.add(norm)
            out.append(r)
        return out

    def _normalize_url(self, url: str) -> str:
        try:
            p = urlparse(url)
            host = (p.netloc or "").lower().replace("www.", "")
            path = p.path.rstrip("/")
            return f"{host}{path}"
        except Exception:
            return url.strip().lower()

    def _cache_get(self, key: str):
        node = self._cache.get(key)
        if not node:
            return None
        if (time.time() - node["ts"]) > self._cache_ttl_seconds:
            self._cache.pop(key, None)
            return None
        return node["data"]

    def _cache_set(self, key: str, data):
        self._cache[key] = {"ts": time.time(), "data": data}

    def _clean_html(self, s: str) -> str:
        s = re.sub(r"<[^>]+>", " ", s or "")
        s = re.sub(r"&nbsp;|&amp;|&#39;|&quot;", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s