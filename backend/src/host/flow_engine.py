"""MicroFlow release engine for OpcHub scenario execution.

Compiles the converted flow project (``config/flows/opchub_flows.json``)
together with the bridged operator registry into one immutable MicroFlow
release, then executes scenarios per request with ``LocalRuntime.run_async``
(the framework forbids blocking ``run()`` inside a running event loop).

Response/error semantics mirror the retired hand-rolled engine exactly:

* ``final_output`` is the ordered merge of every SUCCEEDED node's output data
  (``engine.py`` used to merge into a single dict as it walked the levels)
* ``PermissionError``/``ValueError``/``KeyError`` raised by operators are
  re-raised with their original messages so gateway HTTP mapping is unchanged
* scenario resolution errors keep the ``KeyError`` shape the gateway expects
"""
from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import microflow
from microflow.compiler import compile_release
from microflow.runtime import LocalRuntime
from microflow.values import thaw

from src.host.operator_bridge import build_registry

logger = logging.getLogger("opchub.host.flow_engine")

_FLOW_FILE_CANDIDATES = [
    Path("backend/config/flows/opchub_flows.json"),
    Path("config/flows/opchub_flows.json"),
]

_EPHEMERAL_DEFAULTS = {"durability": "ephemeral", "recovery": {"enabled": False}}

_ERROR_TYPE_BY_CLASS = {"PermissionError": PermissionError, "KeyError": KeyError, "ValueError": ValueError}

# Node-type prefixes, mirroring the scenario loader's classification so legacy
# trace consumers keep reading the same shapes.
_NODE_TYPE_BY_PREFIX = {"guard": "GUARD", "validate": "GUARD", "entity": "STORAGE",
                        "render": "BIZ", "response": "BIZ"}


@dataclass
class ScenarioRun:
    final_output: dict[str, Any] = field(default_factory=dict)
    node_traces: list[dict[str, Any]] = field(default_factory=list)
    trace_id: str = ""


def _find_flow_file() -> Path:
    env_path = os.getenv("OPCHUB_FLOWS_FILE")
    if env_path and Path(env_path).is_file():
        return Path(env_path)
    for candidate in _FLOW_FILE_CANDIDATES:
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError("opchub_flows.json not found; run tools/convert_scenarios.py first")


class FlowEngine:
    """Compile-once, execute-per-request MicroFlow host engine."""

    def __init__(self) -> None:
        self._release: Optional[Any] = None
        self._built_at: float = 0.0

    @property
    def release_id(self) -> str:
        return self._release.release_id if self._release else ""

    @property
    def is_ready(self) -> bool:
        return self._release is not None

    def build(self) -> str:
        """Compile the full flow project into a new immutable release."""
        started = time.perf_counter()
        project = json.loads(_find_flow_file().read_text(encoding="utf-8"))
        # Domain operator modules populate the SDK registry at import time; the
        # engine must see all 226+ operators before the bridge projects them.
        from src.domains.registry import import_domain_functions

        import_domain_functions()
        registry = build_registry()
        for schema_id, schema in (project.get("schemas") or {}).items():
            registry.register_schema(schema_id, schema)
        release = compile_release(
            registry,
            project["flows"],
            defaults=_EPHEMERAL_DEFAULTS,
            source_file=str(_find_flow_file()),
        )
        self._release = release
        self._built_at = time.perf_counter()
        warnings = sum(len(plan.diagnostics) for plan in release.flows.values())
        logger.info(
            "MicroFlow release %s compiled: %d flows, %d schema warnings, %.1fms",
            release.release_id[:12], len(release.flows), warnings,
            (self._built_at - started) * 1000,
        )
        return release.release_id

    def _require_release(self) -> Any:
        if self._release is None:
            self.build()
        return self._release

    def has_flow(self, scenario_code: str) -> bool:
        return scenario_code in self._require_release().flows

    async def execute(self, scenario_code: str, payload: dict[str, Any],
                      context: dict[str, Any]) -> ScenarioRun:
        """Run one scenario; returns the merged final output and node traces."""
        release = self._require_release()
        if scenario_code not in release.flows:
            raise KeyError(f"Scenario code '{scenario_code}' has no configured DAG pipeline")
        flow_input = {
            "payload": dict(payload or {}),
            "__context__": _context_snapshot(context),
        }
        # Mirror the legacy engine's operator context shape: the request context
        # plus a live "inputs" scope seeded with the payload (declarative
        # validate.expression rules read `inputs.<key>` from it). Node outputs
        # are not tracked here — no scenario expression references nodes.*.
        opc_context = {
            "pipeline_id": scenario_code,
            "trace_id": _new_trace_id(),
            "inputs": dict(payload or {}),
            **dict(context or {}),
            "nodes": {},
        }
        runtime = LocalRuntime(release, resources={"opchub": opc_context}, allow_write=True)
        result = await runtime.run_async(scenario_code, flow_input)
        final_output = self._finalize(scenario_code, result)
        return ScenarioRun(
            final_output=final_output,
            node_traces=self._node_traces(release, scenario_code, result),
            trace_id=str(result.output.get("meta", {}).get("traceId") or ""),
        )

    def _node_traces(self, release, scenario_code: str, result) -> list[dict[str, Any]]:
        """Legacy-compatible node traces (durations are per-request totals only)."""
        plan = release.flows[scenario_code]
        traces: list[dict[str, Any]] = []
        for node_id, node_result in result.nodes.items():
            operator_ref = str(plan.definition["nodes"].get(node_id, {}).get("operator") or "")
            operator_name = operator_ref.split("@", 1)[0]
            status = node_result.get("meta", {}).get("status", "SKIPPED")
            prefix = operator_name.split(".", 1)[0]
            if status == "FAILED" and operator_name.startswith(("guard.", "validate.")):
                legacy_status = "GUARD_REJECTED"
            else:
                legacy_status = {"SUCCEEDED": "SUCCESS", "SKIPPED": "SKIPPED",
                                 "FAILED": "FAILED", "CANCELLED": "CANCELLED"}.get(status, status)
            traces.append({
                "node_id": node_id,
                "action_handler": operator_name,
                "type": _NODE_TYPE_BY_PREFIX.get(prefix, "BIZ"),
                "status": legacy_status,
                "duration_ms": 0.0,
                "trace_id": str(result.output.get("meta", {}).get("traceId") or ""),
                "output": thaw(node_result["data"]) if isinstance(node_result.get("data"), Mapping) else node_result.get("data"),
                "error": (node_result.get("error") or {}).get("message"),
            })
        return traces

    def _finalize(self, scenario_code: str, result) -> dict[str, Any]:
        output_meta = result.output.get("meta", {})
        if output_meta.get("status") != "SUCCEEDED":
            self._raise_scenario_error(scenario_code, result)
        final_output: dict[str, Any] = {}
        for _node_id, node_result in result.nodes.items():
            if node_result.get("meta", {}).get("status") == "SUCCEEDED":
                data = node_result.get("data")
                if isinstance(data, Mapping):
                    final_output.update(thaw(data))
        return final_output

    def _raise_scenario_error(self, scenario_code: str, result) -> None:
        """Re-raise business errors with the original OpcHub semantics."""
        for node_id, node_result in result.nodes.items():
            meta = node_result.get("meta", {})
            if meta.get("status") != "FAILED":
                continue
            error = node_result.get("error") or result.output.get("error") or {}
            code = error.get("code", "")
            data = node_result.get("data") or {}
            message = error.get("message") or code
            if code == "OPERATOR_REJECTED":
                error_type = str(data.get("error_type") or "ValueError")
                exc_class = _ERROR_TYPE_BY_CLASS.get(error_type)
                if exc_class is not None:
                    raise exc_class(message)
                raise ValueError(message)
            if code == "UNHANDLED_OPERATOR_EXCEPTION":
                raise RuntimeError(f"Node {node_id} execution error: {error.get('type', 'Exception')}")
            if code in ("UNSUPPORTED_LOCAL_NODE", "UNSUPPORTED_LOCAL_POLICY", "WRITE_EFFECT_NOT_ALLOWED"):
                raise RuntimeError(f"Scenario '{scenario_code}' runtime misconfiguration: {code}")
            raise ValueError(f"Node {node_id} execution error: {code}")
        stop_reason = result.output.get("meta", {}).get("stopReason")
        error = result.output.get("error") or {}
        raise ValueError(f"Scenario '{scenario_code}' failed: {stop_reason or error.get('code', 'UNKNOWN')}")


def _context_snapshot(context: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Project the request context into the flow input under ``__context__``.

    Only JSON-safe scalar/_container fields the scenarios address via
    ``$context.*`` are carried; the bridge always writes this key last so a
    payload cannot spoof identity fields.
    """
    snapshot: dict[str, Any] = {}
    for key, value in dict(context or {}).items():
        if isinstance(value, (str, bool, int, float)) or value is None:
            snapshot[str(key)] = value
        elif isinstance(value, (list, dict)):
            snapshot[str(key)] = value
    return snapshot


def _new_trace_id() -> str:
    import uuid

    return uuid.uuid4().hex


flow_engine = FlowEngine()
