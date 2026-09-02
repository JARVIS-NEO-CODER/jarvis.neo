"""Human-readable capability manifest for J.A.R.V.I.S. NEO."""
from __future__ import annotations
from .capability_registry import CapabilityRegistry

def build_capability_manifest(registry: CapabilityRegistry) -> list[dict]:
    """Return the live tool contract used by UI, agents and diagnostics."""
    return registry.manifest()

def capability_summary(registry: CapabilityRegistry) -> str:
    items = registry.list()
    if not items:
        return "Aucune capacité enregistrée."
    return "Capacités actives : " + ", ".join(c.name for c in items)

__all__ = ["build_capability_manifest", "capability_summary"]
