from __future__ import annotations

import json
import urllib.request
from typing import Any


SYSTEM_PROMPT = """You are the planning core of JARVIS NEO.
You are an agent, not a command router. Given a goal and the current environment,
you decide what to do next using only the available tools.

Return ONLY valid JSON with one of these shapes:
{"kind":"tool","tool":"namespace.name","arguments":{...}}
{"kind":"finish","message":"..."}
{"kind":"wait","message":"..."}

Rules:
- Never invent tool results or system state.
- Do not finish until the goal is actually achieved or genuinely impossible.
- Use the result of each tool call as an observation for the next decision.
- If a tool fails, inspect the error and try a better approach when reasonable.
- If the request is ambiguous and clarification is necessary, use kind=wait.
- Keep each action focused. Do not emit multiple tool calls in one decision.
"""


class OllamaAdapter:
    """Minimal local Ollama adapter using only Python's standard library."""

    def __init__(self, model: str = "qwen2.5:7b", host: str = "http://127.0.0.1:11434"):
        self.model = model
        self.host = host.rstrip("/")

    def decide(self, context: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(context, ensure_ascii=False, indent=2)},
            ],
            "options": {"temperature": 0.1},
        }
        request = urllib.request.Request(
            f"{self.host}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=180) as response:
            body = json.loads(response.read().decode("utf-8"))
        content = body.get("message", {}).get("content")
        if not content:
            raise RuntimeError("Ollama returned no message content")
        return json.loads(content)
