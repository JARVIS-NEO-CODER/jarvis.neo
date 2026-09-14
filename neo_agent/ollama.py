from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


SYSTEM_PROMPT = """You are the planning core of JARVIS NEO.
You are an autonomous agent, not a command router. Given a goal and current observations, decide the single best next action using only available tools.

Return ONLY valid JSON:
{"kind":"tool","tool":"namespace.name","arguments":{...}}
{"kind":"finish","message":"..."}
{"kind":"wait","message":"..."}

Rules:
- Never invent tool results, files, URLs, application state, or success.
- Never finish merely because a search or tool was started. Finish only after verifying the requested outcome.
- Treat tool output as ground truth for what happened.
- After meaningful changes, inspect/test the result before claiming success.
- When a tool fails, diagnose the returned error and try a safer or better approach when reasonable.
- Prefer direct data and page inspection over blindly opening a search engine.
- For image requests, use web.image_search and then present/use the returned media data when possible, rather than only opening Google Images.
- For coding tasks, inspect the workspace, make the smallest coherent changes, run tests or the program, read errors, fix them, and retest.
- For browser tasks, browser.open only starts navigation. Use browser.click, browser.type, browser.key, browser.scroll, browser.back, browser.forward or browser.reload as needed, and use screen.screenshot to observe the resulting screen before deciding the next action.
- Browser click coordinates must come from an actual screen observation. Never invent coordinates.
- Do not blindly repeat clicks, typing or scrolling. Observe after meaningful navigation actions and adapt.
- If the goal is ambiguous and clarification is genuinely necessary, use kind=wait.
- One tool call per decision. Do not emit a sequence of calls in one JSON object.
- Do not repeat a failed action without changing the approach.
"""


class OllamaAdapter:
    """Local Ollama adapter using the standard library."""

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
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Ollama unavailable: {exc}") from exc
        content = body.get("message", {}).get("content")
        if not content:
            raise RuntimeError("Ollama returned no message content")
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Ollama returned invalid agent JSON: {content[:500]}") from exc
