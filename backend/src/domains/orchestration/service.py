"""Service for saving and loading versioned DAG configs, frontend visual layouts, and executing composable scenarios."""
import logging
import uuid
import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from src.domains.orchestration.models import (
    DAGConfigSaveRequest,
    DAGConfigRecord,
    FrontendLayoutSaveRequest,
    FrontendLayoutRecord,
    OperatorDescriptor,
    ScenarioExecuteRequest,
    ScenarioExecuteResponse,
)
from src.core.telemetry import get_current_trace_id
from src.infrastructure.database.persistence import domain_persistence


logger = logging.getLogger("opchub.orchestration")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _flow_engine_enabled() -> bool:
    """MicroFlow executes converted scenarios unless explicitly disabled."""
    import os

    return os.getenv("OPCHUB_FLOW_ENGINE", "1") != "0"


def _flow_engine_has(scenario_code: str) -> bool:
    try:
        from src.host.flow_engine import flow_engine

        if not flow_engine.is_ready:
            flow_engine.build()
        return flow_engine.has_flow(scenario_code)
    except FileNotFoundError:
        return False
    except Exception:  # compile failure must not break scenario resolution
        return False


class OrchestrationService:
    """Manages versioned DAG configs, frontend layouts, and executes composable scenarios."""

    def __init__(self):
        # Key: (scenario_code, version)
        self._dag_configs: Dict[Tuple[str, str], DAGConfigRecord] = {}
        # Bulk loaders suspend the per-save MicroFlow rebuild and sync once.
        self._dynamic_sync_suspended = False
        # Key: layout_name
        self._layouts: Dict[str, FrontendLayoutRecord] = {}

    def save_dag_config(self, req: DAGConfigSaveRequest) -> DAGConfigRecord:
        content_bytes = json.dumps(req.topology_graph, sort_keys=True).encode("utf-8")
        compiled_hash = hashlib.sha256(content_bytes).hexdigest()[:16]
        now = utc_now_iso()
        record_id = str(uuid.uuid4())

        record = DAGConfigRecord(
            id=record_id,
            scenario_code=req.scenario_code,
            version=req.version,
            status=req.status,
            topology_graph=req.topology_graph,
            compiled_hash=compiled_hash,
            created_by=req.created_by,
            created_at=now,
        )
        self._dag_configs[(req.scenario_code, req.version)] = record
        domain_persistence.write("orchestration.dag_configs", f"{req.scenario_code}@@{req.version}", record)
        if not self._dynamic_sync_suspended:
            self.sync_dynamic_flows()
        return record

    def sync_dynamic_flows(self) -> None:
        """Convert workbench-authored DAG configs into MicroFlow flows and rebuild.

        Configs the converter cannot express (unknown operators, unmappable
        constructs) are refused with a logged reason — the legacy engine is
        retired, so authoring never silently degrades.
        """
        import os

        if os.getenv("OPCHUB_FLOW_ENGINE", "1") == "0" or self._dynamic_sync_suspended:
            return
        try:
            from tools.convert_scenarios import convert_scenario

            from src.host.flow_engine import flow_engine
        except ImportError:
            return
        from src.domains.registry import import_domain_functions

        import_domain_functions()  # idempotent: control-plane ops must be visible
        from src.core.operators.sdk import REGISTRY

        known_operators = {d.name for d in REGISTRY}
        flows: list[dict[str, Any]] = []
        failures: list[str] = []
        for (code, version), record in self._dag_configs.items():
            if record.status != "ACTIVE":
                continue
            topo = record.topology_graph or {}
            missing = sorted({
                str(n.get("operator") or n.get("action_handler") or "")
                for n in (topo.get("nodes") or [])
            } - known_operators - {""})
            if missing:
                # One unknown operator must not poison the whole rebuild; the
                # config keeps running on ... it cannot: the legacy engine is
                # retired, so the config is refused with a logged reason.
                failures.append(f"{code}@{version}: unknown operators {missing[:3]}")
                continue
            asset = {
                "scenario": code,
                "version": version,
                "domain": topo.get("domain", ""),
                "nodes": topo.get("nodes") or [],
                "edges": [
                    [e.get("from") or e.get("from_node"), e.get("to") or e.get("to_node")]
                    for e in (topo.get("edges") or [])
                ],
            }
            try:
                flow, report = convert_scenario(asset)
            except Exception as exc:  # authoring-time safety: refuse, never guess
                failures.append(f"{code}@{version}: {exc}")
                continue
            if report["unmapped"]:
                failures.append(f"{code}@{version}: {report['unmapped'][:2]}")
                continue
            flows.append(flow)
        try:
            flow_engine.set_dynamic_flows(flows)
        except Exception as exc:
            logger.error("MicroFlow rebuild after DAG config save failed: %s", exc)
            return
        if failures:
            logger.warning("Dynamic configs refused (not convertible to MicroFlow): %s", failures)

    def get_dag_config(self, scenario_code: str, version: str) -> DAGConfigRecord:
        key = (scenario_code, version)
        if key not in self._dag_configs:
            raise KeyError(f"DAG config for scenario {scenario_code} version {version} not found")
        return self._dag_configs[key]

    def list_dag_configs(self, scenario_code: Optional[str] = None) -> List[DAGConfigRecord]:
        configs = list(self._dag_configs.values())
        if scenario_code:
            configs = [c for c in configs if c.scenario_code == scenario_code]
        return configs

    def delete_dag_config(self, scenario_code: str, version: str) -> bool:
        key = (scenario_code, version)
        if key in self._dag_configs:
            del self._dag_configs[key]
            domain_persistence.delete("orchestration.dag_configs", f"{scenario_code}@@{version}")
            return True
        return False

    def activate_dag_config(self, scenario_code: str, version: str) -> DAGConfigRecord:
        """Mark one config ACTIVE, supersede siblings, and re-order it as the
        execution resolver's last-inserted candidate (latest ACTIVE wins)."""
        key = (scenario_code, version)
        for (c, v), rec in list(self._dag_configs.items()):
            if c == scenario_code and v != version and rec.status == "ACTIVE":
                rec.status = "SUPERSEDED"
                domain_persistence.write("orchestration.dag_configs", f"{c}@@{v}", rec)
        if key not in self._dag_configs:
            raise KeyError(f"DAG config for scenario {scenario_code} version {version} not found")
        rec = self._dag_configs.pop(key)
        rec.status = "ACTIVE"
        self._dag_configs[key] = rec
        domain_persistence.write("orchestration.dag_configs", f"{scenario_code}@@{version}", rec)
        return rec

    def list_operators(self) -> List[OperatorDescriptor]:
        """List every operator the MicroFlow release can orchestrate (SDK registry)."""
        from src.core.operators.sdk import REGISTRY

        return [
            OperatorDescriptor(name=d.name, domain=d.category, description=d.description)
            for d in REGISTRY
        ]

    async def execute_scenario(
        self,
        req: ScenarioExecuteRequest,
        trace_id: Optional[str] = None,
    ) -> ScenarioExecuteResponse:
        """Execute a composable scenario DAG pipeline.

        Every scenario executes on the MicroFlow4Python framework release:
        the 129 asset-defined flows plus workbench-authored configs the
        converter accepted (sync_dynamic_flows). Unconvertible configs are
        refused honestly instead of running on a retired engine.
        """
        if _flow_engine_enabled() and _flow_engine_has(req.scenario_code):
            return await self._execute_via_microflow(req, trace_id)
        # No MicroFlow flow for this code: it was authored dynamically and the
        # converter refused it (see sync_dynamic_flows). The legacy engine is
        # retired; refuse honestly instead of degrading.
        raise ValueError(
            f"Scenario '{req.scenario_code}' is not a MicroFlow flow; its DAG config "
            f"could not be converted (see orchestration service logs)."
        )

    async def _execute_via_microflow(
        self,
        req: ScenarioExecuteRequest,
        trace_id: Optional[str],
    ) -> ScenarioExecuteResponse:
        """Execute a converted scenario on the MicroFlow4Python release."""
        import time as _time

        from src.host.flow_engine import flow_engine

        started = _time.perf_counter()
        tid = trace_id or get_current_trace_id()
        try:
            run = await flow_engine.execute(
                req.scenario_code, dict(req.inputs or {}), dict(req.context or {}),
            )
        except KeyError as exc:
            response = ScenarioExecuteResponse(
                scenario_code=req.scenario_code, status="FAILED",
                execution_time_ms=round((_time.perf_counter() - started) * 1000, 2),
                trace_id=tid, effective_dispatch_mode="IN_PROCESS",
                node_traces=[], final_output={},
                error_message=str(exc), error_type="KeyError",
            )
        except (PermissionError, ValueError) as exc:
            # The legacy engine marked permission failures GUARD_REJECTED.
            status = "GUARD_REJECTED" if isinstance(exc, PermissionError) else "FAILED"
            response = ScenarioExecuteResponse(
                scenario_code=req.scenario_code, status=status,
                execution_time_ms=round((_time.perf_counter() - started) * 1000, 2),
                trace_id=tid, effective_dispatch_mode="IN_PROCESS",
                node_traces=[], final_output={},
                error_message=str(exc), error_type=type(exc).__name__,
            )
        else:
            response = ScenarioExecuteResponse(
                scenario_code=req.scenario_code,
                status="SUCCESS",
                execution_time_ms=round((_time.perf_counter() - started) * 1000, 2),
                trace_id=run.trace_id or tid,
                effective_dispatch_mode="IN_PROCESS",
                node_traces=run.node_traces,
                final_output=run.final_output,
            )
        # 运维平台采集收口：每次场景执行落一条运行记录（write-behind，不阻塞）
        from src.domains.ops.service import ops_run_service

        ops_run_service.record(
            scenario_code=response.scenario_code,
            status=response.status,
            execution_time_ms=response.execution_time_ms,
            trace_id=response.trace_id,
            node_traces=response.node_traces,
            final_output_error=response.error_message or "",
            error_type=response.error_type or "",
            context=dict(req.context or {}),
        )
        return response

    def save_frontend_layout(self, req: FrontendLayoutSaveRequest) -> FrontendLayoutRecord:
        record_id = str(uuid.uuid4())
        record = FrontendLayoutRecord(
            id=record_id,
            layout_name=req.layout_name,
            version=req.version,
            grid_schema=req.grid_schema,
            widgets=req.widgets,
            updated_at=utc_now_iso(),
        )
        self._layouts[req.layout_name] = record
        domain_persistence.write("orchestration.layouts", req.layout_name, record)
        return record

    def get_frontend_layout(self, layout_name: str = "main_console_layout") -> FrontendLayoutRecord:
        if layout_name not in self._layouts:
            raise KeyError(f"Frontend layout {layout_name} not found")
        return self._layouts[layout_name]

    def hydrate_dag_configs(self, rows: List[Dict]) -> int:
        for r in rows:
            record = DAGConfigRecord(**r)
            self._dag_configs[(record.scenario_code, record.version)] = record
        return len(rows)

    def hydrate_layouts(self, rows: List[Dict]) -> int:
        for r in rows:
            record = FrontendLayoutRecord(**r)
            self._layouts[record.layout_name] = record
        return len(rows)


orchestration_service = OrchestrationService()

domain_persistence.register("orchestration.dag_configs", orchestration_service.hydrate_dag_configs)
domain_persistence.register("orchestration.layouts", orchestration_service.hydrate_layouts)