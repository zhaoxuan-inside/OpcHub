"""Operator SDK for the business-agnostic operator kernel.

An operator is a single-purpose callable with the canonical microkernel
signature ``(inputs, context) -> dict``. Operators registered through this SDK
receive two convenience keys in ``inputs``:

* ``params`` – static node configuration compiled from the scenario asset
* ``args``   – per-node input mapping resolved from the pipeline scope

Rules enforced by ``tests/test_operator_contract.py``:

1. Operator modules must not import ``src.domains``.
2. An operator must do exactly one thing (validate / guard / persist / query /
   transform / notify / audit / metric / render / external / response).
3. Operators must not call the orchestrator, the engine or other operators.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

OperatorHandler = Callable[[dict[str, Any], dict[str, Any]], Any]


@dataclass
class OperatorDefinition:
    name: str
    handler: OperatorHandler
    category: str
    description: str
    params: dict[str, Any]
    compensator: Optional[OperatorHandler] = None


REGISTRY: list[OperatorDefinition] = []


def operator(
    name: str,
    category: str,
    description: str = "",
    *,
    params: Optional[dict[str, Any]] = None,
    compensator: Optional[Callable[..., Any]] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register a single-purpose operator definition.

    The decorated function may be sync or async and is called as
    ``fn(params, args, context)``. Returning ``None`` is treated as an empty
    result; returning a non-dict value is wrapped as ``{"result": value}``.
    """

    if not name or not category:
        raise ValueError("Operator name and category are mandatory")

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        async def handler(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
            params = dict(inputs.get("params") or {})
            if "args" in inputs:
                args = dict(inputs.get("args") or {})
            elif params.get("legacy_inputs"):
                # Explicit opt-in for control-plane nodes without inputs_map.
                args = {
                    key: value
                    for key, value in inputs.items()
                    if key not in ("params", "context", "_node")
                }
            else:
                args = {}
            result = fn(params, args, context or {})
            if inspect.isawaitable(result):
                result = await result
            if result is None:
                return {}
            if not isinstance(result, dict):
                return {"result": result}
            return result

        wrapped_compensator = None
        if compensator is not None:

            async def _comp(inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
                merged_args = dict(inputs.get("output") or {})
                merged_args.update(dict(inputs.get("args") or {}))
                result = compensator(
                    dict(inputs.get("params") or {}),
                    merged_args,
                    context or {},
                )
                if inspect.isawaitable(result):
                    result = await result
                return result if isinstance(result, dict) else {}

            wrapped_compensator = _comp

        REGISTRY.append(
            OperatorDefinition(
                name=name,
                handler=handler,
                category=category,
                description=description,
                params=params or {},
                compensator=wrapped_compensator,
            )
        )
        return fn

    return decorator


def register_operators(registry: Any) -> None:
    """Attach every declared operator (and its compensator) to a registry."""
    for definition in REGISTRY:
        registry.register(
            definition.name,
            definition.handler,
            domain=definition.category,
            description=definition.description,
            compensator=definition.compensator,
        )
