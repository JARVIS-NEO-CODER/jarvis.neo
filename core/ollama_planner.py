"""Local Ollama-backed planner and replanner for J.A.R.V.I.S. NEO."""
from __future__ import annotations
import json
import urllib.error
import urllib.request
from typing import Any

class OllamaPlanner:
    """Generate structured plans and recovery plans through local Ollama."""
    def __init__(self, model: str = "llama3.2:3b", base_url: str = "http://127.0.0.1:11434", timeout: float = 60.0) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = max(1.0, float(timeout))

    def __call__(self, objective: str, actions: tuple[str, ...]) -> dict[str, Any]:
        return self.plan(objective, actions)

    def plan(self, objective: str, actions: tuple[str, ...]) -> dict[str, Any]:
        return self._request(self._build_prompt(objective, actions))

    def replan(self, objective: str, actions: tuple[str, ...], *, failure: str, observation: dict[str, Any], attempted_actions: tuple[str, ...] = ()) -> dict[str, Any]:
        if not objective.strip():
            raise ValueError("L'objectif ne peut pas être vide.")
        if not actions:
            raise ValueError("Aucune action enregistrée n'est disponible.")
        return self._request(self._build_replan_prompt(objective, actions, failure, observation, attempted_actions))

    def _request(self, prompt: str) -> dict[str, Any]:
        payload = {"model": self.model, "prompt": prompt, "stream": False, "format": "json", "options": {"temperature": 0}}
        request = urllib.request.Request(f"{self.base_url}/api/generate", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
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
    def _action_list(actions: tuple[str, ...]) -> str:
        return "\n".join(f"- {name}" for name in actions)

    def _build_prompt(self, objective: str, actions: tuple[str, ...]) -> str:
        return f"""You are the planning component of J.A.R.V.I.S. NEO.
Create a minimal, safe, executable plan for this objective:
{objective}
Only use actions from this exact allow-list:
{self._action_list(actions)}
Return ONLY valid JSON: {{"steps":[{{"action":"action.name","kwargs":{{}},"description":"short explanation"}}]}}
Never invent an action. If impossible, return {{"steps":[]}}.
"""

    def _build_replan_prompt(self, objective: str, actions: tuple[str, ...], failure: str, observation: dict[str, Any], attempted_actions: tuple[str, ...]) -> str:
        return f"""You are the recovery planner of J.A.R.V.I.S. NEO.
Original objective: {objective}
Previous failure: {failure}
System observation: {json.dumps(observation, ensure_ascii=False)}
Already attempted actions: {json.dumps(attempted_actions, ensure_ascii=False)}
Create a DIFFERENT, minimal, safe recovery plan that still pursues the original objective.
Only use actions from this exact allow-list:
{self._action_list(actions)}
Do not repeat the failed action unless there is a clear reason. Never invent actions. Never output shell commands or code.
Return ONLY valid JSON: {{"steps":[{{"action":"action.name","kwargs":{{}},"description":"short explanation"}}]}}
If no safe recovery is possible, return {{"steps":[]}}.
"""

__all__ = ["OllamaPlanner"]
