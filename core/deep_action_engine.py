"""Deep, composable actions for J.A.R.V.I.S. NEO.

This layer provides safe adapters for multi-operation workflows while keeping
actual system capabilities behind explicitly registered handlers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Operation:
    name: str
    handler: Callable[..., Any]
    kwargs: dict[str, Any] = field(default_factory=dict)
    verifier: Callable[[Any], bool] | None = None


@dataclass
class WorkflowResult:
    success: bool
    completed: list[str] = field(default_factory=list)
    failed: str | None = None
    results: list[Any] = field(default_factory=list)


class DeepActionEngine:
    """Register and compose real operations into verified workflows."""

    def __init__(self) -> None:
        self._operations: dict[str, Operation] = {}

    def register(self, operation: Operation) -> None:
        if not operation.name or not callable(operation.handler):
            raise ValueError("Une opération valide nécessite un nom et un handler.")
        self._operations[operation.name] = operation

    def execute(self, name: str, **kwargs: Any) -> Any:
        operation = self._operations.get(name)
        if operation is None:
            raise KeyError(f"Opération inconnue: {name}")
        params = {**operation.kwargs, **kwargs}
        result = operation.handler(**params)
        if operation.verifier is not None and not operation.verifier(result):
            raise RuntimeError(f"Vérification échouée: {name}")
        return result

    def run_workflow(self, operations: list[Operation]) -> WorkflowResult:
        result = WorkflowResult(success=True)
        for operation in operations:
            try:
                self.register(operation)
                output = self.execute(operation.name)
                result.completed.append(operation.name)
                result.results.append(output)
            except Exception as exc:
                result.success = False
                result.failed = f"{operation.name}: {exc}"
                return result
        return result


__all__ = ["DeepActionEngine", "Operation", "WorkflowResult"]
