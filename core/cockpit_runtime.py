"""Runtime bridge between J.A.R.V.I.S. commands/AI and the dynamic cockpit."""
from __future__ import annotations

import json
import re
from functools import wraps
from urllib.parse import quote, urlparse

from .web_search import WebSearchProvider


_MARKER = re.compile(r"NEO_PANEL\s*(\{.*?\})", re.IGNORECASE | re.DOTALL)


class CockpitRuntime:
    """Safe bridge that lets commands and the conversational AI request UI panels."""

    def __init__(self, assistant):
        self.assistant = assistant
        self.search = WebSearchProvider(timeout=6)
        self._installed = False
        self._original_process = None
        self._original_chat = None

    @property
    def hud(self):
        return getattr(self.assistant, "cockpit", None)

    def show(self, panel_id, title, content="", kind="info", source=""):
        hud = self.hud
        if hud is None:
            return False
        try:
            return bool(hud.show_dynamic_panel(panel_id, title, content, kind, source))
        except Exception:
            return False

    def remove(self, panel_id):
        hud = self.hud
        if hud is None:
            return False
        try:
            return bool(hud.remove_dynamic_panel(panel_id))
        except Exception:
            return False

    def clear(self):
        hud = self.hud
        if hud is None:
            return False
        try:
            hud.clear_dynamic_panels()
            return True
        except Exception:
            return False

    @staticmethod
    def _url(value):
        try:
            parsed = urlparse(str(value).strip())
            return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
        except Exception:
            return False

    def _show_search_results(self, query, image=False):
        query = str(query).strip()[:300]
        if not query:
            return False
        if image:
            url = f"https://www.google.com/search?tbm=isch&q={quote(query)}"
            return self.show("image-search", f"IMAGES · {query}", kind="web", source=url)
        try:
            results = self.search.search(query, limit=3)
        except Exception as exc:
            return self.show("web-search", f"RECHERCHE · {query}", f"Recherche indisponible : {exc}", "notification")
        shown = False
        for index, result in enumerate(results, 1):
            shown = self.show(
                f"web-{index}",
                result.title,
                result.snippet,
                "web",
                result.url,
            ) or shown
        return shown

    def handle_directive(self, text):
        """Handle explicit cockpit-oriented requests before/alongside legacy intents."""
        raw = str(text).strip()
        low = raw.lower()
        if not raw:
            return False
        if re.search(r"(?:efface|vide|supprime)\s+(?:tous\s+)?(?:les\s+)?panneaux", low):
            return self.clear()
        match = re.search(r"(?:ferme|supprime)\s+(?:le\s+)?panneau\s+([\w.-]+)", low)
        if match:
            return self.remove(match.group(1))
        match = re.search(r"(?:affiche|montre)\s+(?:une\s+)?(?:recherche|résultats?)\s+(?:web|internet)\s+(?:sur|pour)\s+(.+)", raw, re.I)
        if match:
            return self._show_search_results(match.group(1))
        match = re.search(r"(?:affiche|montre)\s+(?:des\s+)?images?\s+(?:sur|de|pour)\s+(.+)", raw, re.I)
        if match:
            return self._show_search_results(match.group(1), image=True)
        match = re.search(r"(?:affiche|ouvre)\s+(?:la\s+)?page\s+(https?://\S+)", raw, re.I)
        if match:
            url = match.group(1).rstrip(".,)")
            return self.show("web-page", "PAGE WEB", kind="web", source=url) if self._url(url) else False
        return False

    def enrich_common_request(self, text):
        """Add useful cockpit panels while keeping applications in their own windows."""
        low = str(text).lower()
        shown = False
        if "météo" in low or "meteo" in low:
            city_match = re.search(r"météo\s+(?:de|à|a|pour)\s+([\wÀ-ÿ' -]{2,60})", text, re.I)
            city = city_match.group(1).strip() if city_match else "Paris"
            url = f"https://www.google.com/search?q={quote('météo ' + city)}"
            shown = self.show("weather", f"MÉTÉO · {city}", kind="web", source=url) or shown
        if re.search(r"\b(?:cherche|recherche|trouve)\b", low) and "web" not in low:
            query = re.sub(r".*?\b(?:cherche|recherche|trouve)\b\s*", "", text, count=1, flags=re.I).strip()
            if query and len(query) <= 180:
                shown = self._show_search_results(query) or shown
        return shown

    def _parse_ai_markers(self, response):
        if not isinstance(response, str):
            return response
        clean = response
        for match in list(_MARKER.finditer(response)):
            raw = match.group(1)
            try:
                spec = json.loads(raw)
            except Exception:
                continue
            if not isinstance(spec, dict):
                continue
            kind = str(spec.get("kind", "info")).lower().strip()
            panel_id = str(spec.get("id", "ai-panel")).strip()[:80]
            title = str(spec.get("title", "JARVIS")).strip()[:80]
            content = str(spec.get("content", "")).strip()[:4000]
            source = str(spec.get("source", "")).strip()[:1000]
            if kind == "web_search":
                self._show_search_results(spec.get("query", ""), image=False)
            elif kind == "image_search":
                self._show_search_results(spec.get("query", ""), image=True)
            elif kind in {"web", "image"} and self._url(source):
                self.show(panel_id, title, content, kind, source)
            elif kind in {"info", "status", "notification"}:
                self.show(panel_id, title, content, kind, source)
            clean = clean.replace(match.group(0), "").strip()
        return clean

    def install(self):
        if self._installed:
            return
        processor = getattr(self.assistant, "processor", None)
        if processor is not None:
            self._original_process = processor.process
            runtime = self

            @wraps(self._original_process)
            def wrapped_process(text):
                runtime.handle_directive(text)
                result = runtime._original_process(text)
                runtime.enrich_common_request(text)
                return result

            processor.process = wrapped_process

            self._original_chat = None
            try:
                conversation_cls = type(getattr(processor, "conversation_ai", None)) if getattr(processor, "conversation_ai", None) else None
                if conversation_cls is not None and hasattr(conversation_cls, "chat"):
                    self._patch_chat(conversation_cls)
            except Exception:
                pass

        self._installed = True

    def _patch_chat(self, conversation_cls):
        if getattr(conversation_cls, "_neo_cockpit_patched", False):
            return
        original = conversation_cls.chat
        runtime = self

        @wraps(original)
        def wrapped_chat(self_ai, messages, *args, **kwargs):
            items = list(messages or [])
            protocol = (
                "\n\nCOCKPIT NEO : tu peux demander l'affichage dynamique quand cela apporte une vraie valeur. "
                "Après ta réponse normale, ajoute éventuellement une ligne NEO_PANEL suivie d'un JSON. "
                "Formats : {\"id\":\"...\",\"title\":\"...\",\"kind\":\"info|status|notification|web|image|web_search|image_search\",\"content\":\"...\",\"source\":\"https://...\",\"query\":\"...\"}. "
                "Utilise web_search pour faire rechercher un sujet et afficher les vrais résultats. Utilise image_search pour une recherche d'images. "
                "N'utilise pas le cockpit pour remplacer une application : ETS2, Discord, VS Code et les autres applications restent dans leur propre fenêtre."
            )
            if items and items[0].get("role") == "system":
                first = dict(items[0])
                first["content"] = first.get("content", "") + protocol
                items[0] = first
            result = original(self_ai, items, *args, **kwargs)
            return runtime._parse_ai_markers(result)

        conversation_cls.chat = wrapped_chat
        conversation_cls._neo_cockpit_patched = True


__all__ = ["CockpitRuntime"]
