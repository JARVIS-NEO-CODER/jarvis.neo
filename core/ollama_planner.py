"""Local Ollama-backed planner and replanner for J.A.R.V.I.S. NEO."""
from __future__ import annotations
import json, urllib.error, urllib.request
from typing import Any

class OllamaPlanner:
    """Generate plans from the live capability manifest."""
    def __init__(self, model="llama3.2:3b", base_url="http://127.0.0.1:11434", timeout=60.0): self.model=model; self.base_url=base_url.rstrip("/"); self.timeout=max(1.0,float(timeout))
    def __call__(self, objective, capabilities): return self.plan(objective, capabilities)
    def plan(self, objective, capabilities): return self._request(self._build_prompt(objective, capabilities))
    def replan(self, objective, capabilities, *, failure, observation, attempted_actions=()): return self._request(self._build_replan_prompt(objective, capabilities, failure, observation, attempted_actions))
    def _request(self,prompt):
        req=urllib.request.Request(f"{self.base_url}/api/generate",data=json.dumps({"model":self.model,"prompt":prompt,"stream":False,"format":"json","options":{"temperature":0}}).encode(),headers={"Content-Type":"application/json"},method="POST")
        try:
            with urllib.request.urlopen(req,timeout=self.timeout) as r: body=json.loads(r.read().decode())
        except urllib.error.URLError as exc: raise RuntimeError(f"Ollama est inaccessible: {exc}") from exc
        raw=body.get("response")
        if not isinstance(raw,str): raise RuntimeError("Ollama n'a pas renvoyé de plan.")
        try: parsed=json.loads(raw)
        except json.JSONDecodeError as exc: raise ValueError("Ollama a renvoyé un JSON de plan invalide.") from exc
        if not isinstance(parsed,dict): raise ValueError("Le plan Ollama doit être un objet JSON.")
        return parsed
    @staticmethod
    def _manifest(capabilities):
        if isinstance(capabilities,tuple): return json.dumps(list(capabilities),ensure_ascii=False)
        return json.dumps(capabilities,ensure_ascii=False)
    def _build_prompt(self,objective,capabilities):
        return f'''You are the planning component of J.A.R.V.I.S. NEO.\nObjective: {objective}\n\nLIVE CAPABILITY REGISTRY:\n{self._manifest(capabilities)}\n\nUse only registered capabilities. Respect permission and conditions. Return ONLY JSON: {{"steps":[{{"action":"capability.name","kwargs":{{}},"description":"short explanation"}}]}}. Never invent capabilities.'''
    def _build_replan_prompt(self,objective,capabilities,failure,observation,attempted_actions):
        return f'''You are the recovery planner of J.A.R.V.I.S. NEO.\nObjective: {objective}\nFailure: {failure}\nObservation: {json.dumps(observation,ensure_ascii=False)}\nAttempted: {json.dumps(attempted_actions,ensure_ascii=False)}\n\nLIVE CAPABILITY REGISTRY:\n{self._manifest(capabilities)}\n\nCreate a safe alternative plan. Use only registered capabilities and respect their permissions/conditions. Avoid the failed action unless justified. Return ONLY JSON: {{"steps":[{{"action":"capability.name","kwargs":{{}},"description":"short explanation"}}]}}. If impossible, return {{"steps":[]}}.'''

__all__=["OllamaPlanner"]
