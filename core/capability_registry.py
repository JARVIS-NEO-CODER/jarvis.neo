"""Central registry describing what J.A.R.V.I.S. NEO can safely do."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

@dataclass(frozen=True)
class Capability:
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    permission: str = "normal"
    conditions: tuple[str, ...] = ()
    verifier: str | None = None
    action: str | None = None
    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["conditions"] = list(self.conditions)
        return data

class CapabilityRegistry:
    """Single source of truth for capabilities exposed to planners and agents."""
    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}
        self._handlers: dict[str, Callable[..., Any]] = {}
    def register(self, capability: Capability, handler: Callable[..., Any] | None = None) -> None:
        if not capability.name.strip(): raise ValueError("Le nom de la capacité ne peut pas être vide.")
        if capability.name in self._capabilities: raise ValueError(f"Capacité déjà enregistrée: {capability.name}")
        self._capabilities[capability.name] = capability
        if handler is not None: self._handlers[capability.name] = handler
    def unregister(self, name: str) -> None:
        self._capabilities.pop(name, None); self._handlers.pop(name, None)
    def get(self, name: str) -> Capability | None: return self._capabilities.get(name)
    def require(self, name: str) -> Capability:
        capability = self.get(name)
        if capability is None: raise KeyError(f"Capacité inconnue: {name}")
        return capability
    def list(self) -> tuple[Capability, ...]: return tuple(self._capabilities[n] for n in sorted(self._capabilities))
    def names(self) -> tuple[str, ...]: return tuple(sorted(self._capabilities))
    def manifest(self) -> list[dict[str, Any]]: return [c.as_dict() for c in self.list()]
    def for_planner(self) -> tuple[dict[str, Any], ...]: return tuple(c.as_dict() for c in self.list())
    def bind(self, name: str, handler: Callable[..., Any]) -> None: self.require(name); self._handlers[name] = handler
    def execute(self, name: str, **kwargs: Any) -> Any:
        self.require(name)
        handler = self._handlers.get(name)
        if handler is None: raise RuntimeError(f"Aucun handler pour la capacité: {name}")
        return handler(**kwargs)
    def clear(self) -> None: self._capabilities.clear(); self._handlers.clear()

__all__ = ["Capability", "CapabilityRegistry"]
