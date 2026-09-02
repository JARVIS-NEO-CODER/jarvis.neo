"""Groq-backed goal planner for the J.A.R.V.I.S. NEO agent."""
from __future__ import annotations
import json
from .groq_provider import GroqProvider

class GroqPlanner:
    def __init__(self, api_key: str, model: str = "llama-3.1-8b-instant", timeout: float = 60.0):
        self.provider = GroqProvider(api_key=api_key, model=model, timeout=timeout)

    def plan(self, objective, capabilities):
        return self._request(self._build_prompt(objective, capabilities))

    def replan(self, objective, capabilities, *, failure, observation, attempted_actions=()):
        return self._request(self._build_replan_prompt(objective, capabilities, failure, observation, attempted_actions))

    def _request(self, prompt):
        raw = self.provider.chat([{"role": "system", "content": "Tu es le planificateur d'agent de J.A.R.V.I.S. NEO. Retourne uniquement du JSON valide."}, {"role": "user", "content": prompt}], temperature=0, max_tokens=1200)
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("Groq a renvoyé un JSON de plan invalide.") from exc
        if not isinstance(parsed, dict):
            raise ValueError("Le plan Groq doit être un objet JSON.")
        return parsed

    @staticmethod
    def _manifest(capabilities): return json.dumps(list(capabilities), ensure_ascii=False)
    def _build_prompt(self, objective, capabilities):
        return f'''Objectif utilisateur : {objective}\n\nCAPACITÉS DISPONIBLES :\n{self._manifest(capabilities)}\n\nConstruis le minimum d'étapes nécessaires. Utilise uniquement les capacités enregistrées. Respecte leurs permissions et conditions. Pour chaque étape, fournis action, kwargs et description. JSON uniquement : {{"steps":[{{"action":"capability.name","kwargs":{{}},"description":"..."}}]}}'''
    def _build_replan_prompt(self, objective, capabilities, failure, observation, attempted_actions):
        return f'''Objectif : {objective}\nÉchec : {failure}\nObservation : {json.dumps(observation, ensure_ascii=False)}\nActions déjà tentées : {json.dumps(attempted_actions, ensure_ascii=False)}\nCAPACITÉS : {self._manifest(capabilities)}\nPropose une alternative sûre et minimale. N'invente aucune capacité. JSON uniquement : {{"steps":[{{"action":"capability.name","kwargs":{{}},"description":"..."}}]}}'''

__all__ = ["GroqPlanner"]
