"""Conversation AI facade and autonomous-agent bridge for J.A.R.V.I.S. NEO."""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from .ai_provider_router import AIProviderRouter
from .groq_provider import GroqProvider

DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"

CONVERSATION_STYLE = """STYLE CONVERSATIONNEL NEO :
- Parle comme un assistant personnel présent, naturel et attentif, pas comme un formulaire.
- Réponds en français sauf demande contraire.
- Tutoye l'utilisateur si le ton de la conversation le permet. N'utilise pas « monsieur » par défaut.
- Ne répète pas la demande de l'utilisateur et n'annonce pas inutilement ce que tu vas faire.
- Pour une petite demande, une ou deux phrases suffisent.
- Pour une conversation, privilégie la continuité et les références au contexte récent.
- Si l'utilisateur dit « il », « elle », « le », « ça », etc., résous la référence avec le contexte récent avant de demander une précision.
- Ne pose une question que si une information réellement nécessaire manque.
- Si une action a déjà été exécutée par un outil, ne prétends pas l'exécuter à nouveau. Décris simplement le résultat fourni par le programme.
- Ne dis jamais qu'une action est terminée sans preuve fournie par le programme ou par une vérification explicite.
- Évite les formules génériques comme « Bien sûr ! », « Avec plaisir ! » ou « Comment puis-je vous aider ? » lorsqu'elles n'apportent rien.
- Varie naturellement la longueur et le ton. Une confirmation peut être très courte.
- En vocal, écris des phrases faciles à prononcer, sans listes lourdes ni symboles inutiles.
"""


class OllamaChatProvider:
    def __init__(self, ollama_module: Any, model: str, base_url: str | None = None):
        self.ollama = ollama_module
        self.model = model
        self.base_url = base_url

    @property
    def available(self) -> bool:
        return self.ollama is not None

    def chat(self, messages, *, temperature=0.2, max_tokens=2048):
        if self.ollama is None:
            raise RuntimeError("Ollama n'est pas installé.")
        client = self.ollama.Client(**({"host": self.base_url} if self.base_url else {}))
        response = client.chat(model=self.model, messages=messages, options={"temperature": temperature, "num_predict": max_tokens})
        try:
            return response["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise RuntimeError("Réponse Ollama invalide.") from exc


class ConversationAI:
    def __init__(self, config: dict[str, Any], ollama_module: Any = None):
        self.config = config
        if ollama_module is None:
            try:
                import ollama as ollama_module
            except ImportError:
                ollama_module = None
        self.ollama_module = ollama_module
        self.config.setdefault("groq_model", DEFAULT_GROQ_MODEL)
        self.config.setdefault("ollama_enabled", True)
        self.config.setdefault("ai_provider", "groq")
        self.config.setdefault("groq_fallback_to_ollama", True)
        self.config.setdefault("groq_quota_fallback", "ollama")
        self.router = self._build_router()

    def _build_router(self):
        groq = GroqProvider(api_key=self.config.get("groq_api_key", ""), model=self.config.get("groq_model", DEFAULT_GROQ_MODEL), timeout=float(self.config.get("groq_timeout", 60)))
        ollama = None
        if self.config.get("ollama_enabled", True):
            ollama = OllamaChatProvider(self.ollama_module, self.config.get("model", "llama3.2:3b"), self.config.get("ollama_base_url", "http://127.0.0.1:11434"))
        return AIProviderRouter(groq=groq, ollama=ollama, prefer_groq=self.config.get("ai_provider", "groq") != "ollama", fallback_to_ollama=self.config.get("groq_fallback_to_ollama", True), quota_fallback_mode=self.config.get("groq_quota_fallback", "ollama"))

    def refresh(self) -> dict[str, Any]:
        self.router = self._build_router()
        return self.router.status

    @staticmethod
    def _with_style(messages):
        items = list(messages or [])
        style = {"role": "system", "content": CONVERSATION_STYLE}
        if items and items[0].get("role") == "system":
            first = dict(items[0])
            first["content"] = first.get("content", "") + "\n\n" + CONVERSATION_STYLE
            items[0] = first
            return items
        return [style, *items]

    def chat(self, messages, *, temperature=0.2, max_tokens=2048):
        return self.router.chat(self._with_style(messages), temperature=temperature, max_tokens=max_tokens)

    @property
    def status(self):
        return self.router.status


class _AgentLLMAdapter:
    SYSTEM = """Tu es le cerveau autonome de J.A.R.V.I.S. NEO.
Tu ne réponds PAS en conversation libre. Tu dois choisir l'action suivante.
Réponds avec un unique objet JSON valide, sans markdown.
Formats autorisés:
{"kind":"tool","tool":"namespace.name","arguments":{}}
{"kind":"finish","message":"résultat court"}
{"kind":"wait","message":"information ou approbation nécessaire"}

Règles:
- Utilise les outils pour connaître l'état réel du PC, des fichiers et du web.
- N'invente jamais un résultat.
- Pour une tâche de développement, inspecte d'abord le projet, écris, exécute/teste, lis les erreurs puis corrige et reteste.
- Une erreur d'outil est une observation, pas une réussite.
- Ne termine que lorsque le but est atteint ou objectivement impossible.
- Si une information indispensable manque, utilise wait.
- Pour une demande d'image, utilise web.image_search et exploite les résultats retournés. Ne te contente jamais d'ouvrir Google Images.
- Pour une recherche web, utilise web.search puis web.fetch lorsque le contenu de la page est nécessaire. browser.open sert uniquement à démarrer une navigation réellement demandée ou nécessaire.
- Une navigation interactive ne s'arrête pas à browser.open : utilise browser.click, browser.type, browser.key, browser.scroll, browser.back, browser.forward ou browser.reload, puis screen.screenshot pour observer l'écran avant de choisir la suite.
- N'invente jamais des coordonnées de clic. Elles doivent provenir d'une capture d'écran réelle.
- Après une action visuelle importante, observe avant de continuer. Si l'état n'est pas celui attendu, adapte la stratégie.
- Ne transforme pas automatiquement une demande d'image en ouverture d'un onglet Google.
- Une action de navigation doit produire une observation exploitable avant de décider de la suite.
"""

    def __init__(self, conversation: "ConversationAI"):
        self.conversation = conversation

    def decide(self, context: dict[str, Any]) -> dict[str, Any] | str:
        payload = json.dumps(context, ensure_ascii=False, default=str)
        return self.conversation.router.chat([
            {"role": "system", "content": self.SYSTEM},
            {"role": "user", "content": payload},
        ], temperature=0.1, max_tokens=1400)


class AutonomousCommandBridge:
    LONG_RUNNING_MARKERS = (
        "code ", "code-moi", "programme", "développe", "développer", "crée un jeu",
        "construis", "répare le projet", "corrige le projet", "analyse le projet",
        "installe", "configure le projet", "pendant que", "je pars", "quand je suis",
    )

    def __init__(self, config: dict[str, Any], conversation: ConversationAI | None = None):
        self.config = config
        self.conversation = conversation or ConversationAI(config)
        self.runtime = None
        self._lock = threading.Lock()

    def _ensure(self):
        if self.runtime is not None:
            return self.runtime
        with self._lock:
            if self.runtime is not None:
                return self.runtime
            from neo_agent.agent_loop import AgentLoop
            from neo_agent.models import AgentConfig
            from neo_agent.permissions import PermissionMode, PermissionPolicy
            from neo_agent.task_manager import TaskManager
            from neo_agent.tools import ToolRegistry
            import core.assistant_components as components

            mode_value = max(1, min(3, int(self.config.get("agent_permission_mode", 3))))
            cwd = str(Path(self.config.get("agent_cwd", ".")).expanduser().resolve())
            state_dir = str(Path(self.config.get("agent_state_dir", "~/.jarvis_neo/agent")).expanduser())
            agent_config = AgentConfig(permission_mode=mode_value, cwd=cwd, state_dir=state_dir, max_steps=int(self.config.get("agent_max_steps", 24)))
            tools = ToolRegistry(PermissionPolicy(PermissionMode(mode_value)), cwd)
            legacy_tools = getattr(components, "tools", None)
            if legacy_tools is not None:
                self._register_legacy_tools(tools, legacy_tools)

            def event(kind, data):
                try:
                    signals = getattr(components, "_signals", None)
                    if signals is not None and kind.startswith("task."):
                        signals.status_change.emit("AGENT")
                except Exception:
                    pass

            self.runtime = type("AgentRuntime", (), {})()
            self.runtime.agent = AgentLoop(_AgentLLMAdapter(self.conversation), config=agent_config, tools=tools, tasks=TaskManager(state_dir), event=event)
            return self.runtime

    @staticmethod
    def _register_legacy_tools(registry, legacy_tools):
        registry.register("desktop.open_application", "Ouvrir une application ou une URL", "desktop.control", lambda application: legacy_tools.open_application(application))
        registry.register("desktop.close_application", "Fermer une application/processus", "desktop.control", lambda application: legacy_tools.close_application(application))
        registry.register("desktop.web_search", "Ouvrir une recherche web", "web.open", lambda query: _emit_open_url("https://www.google.com/search?q=" + _quote(query)))
        registry.register("desktop.image_search", "Rechercher des images et retourner les résultats", "network.read", lambda query: _image_search(query))
        registry.register("desktop.screenshot", "Prendre une capture d'écran", "screen.capture", lambda: _screenshot())
        registry.register("desktop.copy_text", "Copier du texte", "desktop.clipboard", lambda text: _copy(text))
        registry.register("system.stats", "Lire les métriques système", "system.read", lambda: _system_stats())

    def _submit(self, goal: str, background: bool):
        task = self.runtime.agent.tasks.create(goal, {"source": "command_processor"})
        if background:
            thread = threading.Thread(target=self.runtime.agent.run, args=(task.id,), daemon=True, name=f"jarvis-agent-{task.id}")
            thread.start()
        else:
            self.runtime.agent.run(task.id)
        return task

    def process(self, text: str) -> str:
        goal = str(text).strip()
        background = any(marker in goal.lower() for marker in self.LONG_RUNNING_MARKERS)
        task = self._submit(goal, background=background)
        if background:
            return f"Tâche autonome lancée en arrière-plan. ID : {task.id}"
        if task.state.value == "completed":
            return str(task.context.get("result") or "Tâche terminée.")
        if task.state.value == "waiting_approval":
            return "J'attends une approbation ou une information nécessaire."
        if task.state.value == "failed":
            raise RuntimeError("agent_failed")
        return "Tâche autonome lancée."


def _quote(value: str) -> str:
    from urllib.parse import quote_plus
    return quote_plus(str(value).strip())


def _emit_open_url(url: str):
    import core.assistant_components as components
    signals = getattr(components, "_signals", None)
    if signals is None:
        raise RuntimeError("Signal d'ouverture web indisponible")
    signals.open_url.emit(url)
    return {"url": url}


def _image_search(query: str):
    from .web_media import WebMediaProvider
    return {"query": str(query).strip(), "results": [item.as_dict() for item in WebMediaProvider().search_images(query, limit=8, open_browser=False)]}


def _screenshot():
    import time
    import pyautogui
    base = Path.home() / ".jarvis_neo" / "snapshots"
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"agent_{int(time.time())}.png"
    pyautogui.screenshot(str(path))
    return {"path": str(path)}


def _copy(text: str):
    import pyperclip
    pyperclip.copy(str(text))
    return {"copied": True}


def _system_stats():
    import psutil
    return {"cpu_percent": psutil.cpu_percent(), "ram_percent": psutil.virtual_memory().percent, "disk_percent": psutil.disk_usage(Path.home().anchor or "/").percent}


def _install_autonomous_processor_hook():
    try:
        import core.assistant_components as components
        Processor = components.CommandProcessor
        if getattr(Processor, "_neo_autonomous_hook", False):
            return
        original = Processor.process
        bridge_holder: dict[int, AutonomousCommandBridge] = {}

        def process(self, text):
            config = getattr(components, "_config", None) or {}
            if config.get("agent_enabled", True) is False:
                return original(self, text)
            try:
                key = id(self)
                bridge = bridge_holder.get(key)
                if bridge is None:
                    bridge = AutonomousCommandBridge(config)
                    bridge_holder[key] = bridge
                return bridge.process(text)
            except Exception:
                return original(self, text)

        Processor.process = process
        Processor._neo_autonomous_hook = True
        Processor._neo_legacy_process = original
    except Exception:
        pass


_install_autonomous_processor_hook()

__all__ = ["ConversationAI", "OllamaChatProvider", "AutonomousCommandBridge", "CONVERSATION_STYLE"]
