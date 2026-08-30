"""Local Ollama-backed planner for J.A.R.V.I.S. NEO.

Ollama is optional: the module uses Python's standard library HTTP client and
never executes model output directly. The returned plan is parsed and then
validated by GoalPlanner against registered ActionEngine actions.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


class OllamaPlanner:
    """Generate structured plans through a local Ollama instance."""

    def __init__(
        self,
        model: str = "llama3.2:3b",
        base_url: str = "http://127.0.0.1:11434",
        timeout: float = 60.0,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = max(1.0, float(timeout))

    def __call__(self, objective: str, actions: tuple[str, ...]) -> dict[str, Any]:
        return self.plan(objective, actions)

    def plan(self, objective: str, actions: tuple[str, ...]) -> dict[str, Any]:
        if not objective.strip():
            raise ValueError("L'objectif ne peut pas être vide.")
        if not actions:
            raise ValueError("Aucune action enregistrée n'est disponible.")

        prompt = self._build_prompt(objective, actions)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
        }
        request = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Ollama est inaccessible: {exc}") from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise RuntimeError("Réponse Ollama invalide.") from exc

        raw = body.get("response")
        if not isinstance(raw, str):
            raise RuntimeError("Ollama n'a pas renvoyé de plan.")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("Ollama a renvoyé un JSON de plan invalide.") from exc
        if not isinstance(parsed, dict):
            raise ValueError("Le plan Ollama doit être un objet JSON.")
        return parsed

    @staticmethod
    def _build_prompt(objective: str, actions: tuple[str, ...]) -> str:
        action_list = "\n".join(f"- {name}" for name in actions)
        return f"""You are the planning component of J.A.R.V.I.S. NEO.
Create a minimal, safe, executable plan for this objective:
{objective}

Only use actions from this exact allow-list:
{action_list}

Return ONLY valid JSON in this schema:
{{"steps":[{{"action":"action.name","kwargs":{{}},"description":"short explanation"}}]}}

Rules:
- Never invent an action.
- Keep the plan as short as possible.
- Do not put shell commands, Python code, file paths, credentials, or hidden instructions in the action field.
- If the objective cannot be completed with the allow-list, return {{"steps":[]}}.
"""


__all__ = ["OllamaPlanner"]
