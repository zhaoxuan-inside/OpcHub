"""Project the OpcHub operator SDK registry into MicroFlow contract operators.

Every OpcHub operator keeps its ``(params, args, context) -> dict`` signature —
the SDK handler already wraps it. The bridge adapts it to the MicroFlow
six-param contract:

* input  ``{"params": ..., "args": ...}`` assembled by the flow mapping
* errors: ``PermissionError``/``ValueError``/``KeyError`` become business
  rejections (``False`` + structured reason in output.data); unexpected
  exceptions propagate to the framework (fallback/circuit-break semantics)
* results: every returned key is published into output.data so downstream
  mappings address ``nodes.<id>.output.data.<key>`` exactly like the old engine

Effect classes: storage/side-effect/metric operators declare ``write`` (they
need an ``allow_write`` runtime — see flow_engine); everything else is pure or
read. Schemas are deliberately permissive objects: payload validation stays
with the OpcHub operators and pydantic models.
"""
from __future__ import annotations

from typing import Any

from microflow import Registry
from microflow.values import thaw
from pydantic_core import to_jsonable_python

from src.core.operators.sdk import REGISTRY, OperatorDefinition

INPUT_SCHEMA = {"type": "object", "additionalProperties": True}
_EFFECT_WRITE_PREFIXES = ("entity.", "side_effects.", "metric.", "notification.")


def effect_for(operator_name: str) -> str:
    return "write" if operator_name.startswith(_EFFECT_WRITE_PREFIXES) else "read"


def _bridge(definition: OperatorDefinition):
    async def run(input, output, context, metrix, debug, log) -> bool:
        opc_context = context.resource("opchub")
        # OpcHub operators expect plain dicts (isinstance checks, .get chains);
        # MicroFlow freezes mappings, so thaw before handing data over. The
        # whole mapped input passes through (reserved channels like
        # __payload__ ride along for dynamic operators).
        handler_input = thaw(dict(input))
        params = handler_input.get("params")
        args = handler_input.get("args")
        handler_input["params"] = params if isinstance(params, dict) else {}
        handler_input["args"] = args if isinstance(args, dict) else {}
        try:
            result = await definition.handler(handler_input, opc_context)
        except (PermissionError, ValueError, KeyError) as exc:
            # Business rejection: the framework carries the message through
            # Output.reject into the error envelope; the original exception
            # class travels as data for the host to re-raise faithfully.
            output.set("error_type", type(exc).__name__)
            output.reject(message=str(exc))
            return False
        for key, value in dict(result).items():
            # The legacy engine let operators return pydantic models/datetimes and
            # relied on FastAPI to serialize; the framework requires JSON-safe
            # output envelopes, so convert at the bridge boundary.
            output.set(str(key), to_jsonable_python(value))
        return True

    return run


def build_registry() -> Registry:
    """Build a sealed-ready MicroFlow registry from the OpcHub SDK registry."""
    registry = Registry()
    registry.register_schema("opchub.object", INPUT_SCHEMA)
    # Hot reload re-imports operator modules, appending duplicates to the SDK
    # registry; last definition wins, mirroring the legacy atomic registry.
    latest: dict[str, OperatorDefinition] = {}
    for definition in REGISTRY:
        latest[definition.name] = definition
    for definition in latest.values():
        registry.register_operator(
            name=definition.name,
            version="1",
            method=_bridge(definition),
            input_schema="opchub.object",
            output_schema="opchub.object",
            capabilities={"effect": effect_for(definition.name),
                          "idempotency_support": "natural"},
            description=definition.description,
        )
    return registry
