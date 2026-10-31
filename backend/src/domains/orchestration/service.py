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
    OperatorModeUpdateRequest,
    ScenarioExecuteRequest,
    ScenarioExecuteResponse,
)
from src.core.microkernel.dispatcher import dispatcher
from src.core.microkernel.engine import microkernel_engine
from src.core.microkernel.models import (
    DAGConfig,
    ExecutionGraph,
    NodeDef,
    EdgeDef,
    NodeType,
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

        Configs the converter cannot express keep executing on the legacy engine
        (execute_scenario falls back when the flow id is absent from the release),
        so authoring never silently loses semantics.
        """
        import os

        if os.getenv("OPCHUB_FLOW_ENGINE", "1") == "0" or self._dynamic_sync_suspended:
            return
        try:
            from tools.convert_scenarios import convert_scenario

            from src.host.flow_engine import flow_engine
        except ImportError:
            return
        flows: list[dict[str, Any]] = []
        failures: list[str] = []
        for (code, version), record in self._dag_configs.items():
            if record.status != "ACTIVE":
                continue
            topo = record.topology_graph or {}
            asset = {
                "scenario": code,
                "version": version,
                "domain": topo.get("domain", ""),
                "nodes": topo.get("nodes") or [],
                "edges": [[e.get("from"), e.get("to")] for e in (topo.get("edges") or [])],
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
            logger.warning("Dynamic configs kept on the legacy engine: %s", failures)

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
        """List all registered atomic operator descriptors across all domains."""
        return dispatcher.list_descriptors()

    def update_operator_mode(self, req: OperatorModeUpdateRequest) -> OperatorDescriptor:
        """Update dispatch mode (IN_PROCESS vs HTTP_REMOTE) for an operator."""
        dispatcher.set_operator_mode(req.name, req.mode, req.remote_endpoint)
        mode, endpoint = dispatcher.get_operator_mode(req.name)
        return OperatorDescriptor(
            name=req.name,
            domain="custom",
            description=f"Operator: {req.name}",
            mode=mode,
            remote_endpoint=endpoint,
        )

    async def execute_scenario(
        self,
        req: ScenarioExecuteRequest,
        trace_id: Optional[str] = None,
    ) -> ScenarioExecuteResponse:
        """Execute a composable scenario DAG pipeline.

        Converted scenarios (the 129 asset-defined flows) execute on the
        MicroFlow4Python framework release; anything else (dynamically saved
        DAG configs, e.g. workbench-authored or test fixtures) keeps the
        legacy in-process engine until the workbench authoring path is
        migrated. ``OPCHUB_FLOW_ENGINE=0`` forces the legacy path everywhere.
        """
        if _flow_engine_enabled() and _flow_engine_has(req.scenario_code):
            return await self._execute_via_microflow(req, trace_id)
        tid = trace_id or get_current_trace_id()
        # Find latest active DAG config for the scenario
        candidates = [c for c in self._dag_configs.values() if c.scenario_code == req.scenario_code and c.status == "ACTIVE"]
        if not candidates:
            # Scenario assets are the single source of truth for business flows;
            # load them lazily so direct service/tests do not depend on lifespan.
            from src.core.scenario import ensure_scenarios_loaded

            ensure_scenarios_loaded()
            candidates = [c for c in self._dag_configs.values() if c.scenario_code == req.scenario_code and c.status == "ACTIVE"]
            if not candidates:
                candidates = [c for c in self._dag_configs.values() if c.scenario_code == req.scenario_code]

        if not candidates:
            raise KeyError(f"Scenario code '{req.scenario_code}' has no configured DAG pipeline")

        config_record = candidates[-1]
        topo = config_record.topology_graph

        # Convert topology dictionary to DAGConfig
        nodes = []
        for n in topo.get("nodes", []):
            ntype = NodeType[n.get("type", "BIZ")] if n.get("type") in NodeType.__members__ else NodeType.BIZ
            nodes.append(
                NodeDef(
                    id=n["id"],
                    action_handler=n["action_handler"],
                    type=ntype,
                    timeout_ms=n.get("timeout_ms", 3000),
                    params=n.get("params") or {},
                    inputs_map=n.get("inputs_map") or n.get("args") or {},
                    when=n.get("when"),
                    output_key=n.get("output_key"),
                )
            )

        edges = []
        for e in topo.get("edges", []):
            edges.append(
                EdgeDef(
                    from_node=e.get("from") or e.get("from_node"),
                    to_node=e.get("to") or e.get("to_node"),
                    when=e.get("when"),
                )
            )

        dag_config = DAGConfig(
            version=config_record.version,
            scenario_code=config_record.scenario_code,
            enable_saga_compensation=topo.get("enable_saga_compensation", True),
            execution_graph=ExecutionGraph(
                topology=topo.get("topology", "DAG"),
                entry_node=topo.get("entry_node", nodes[0].id if nodes else ""),
                nodes=nodes,
                edges=edges,
            ),
        )

        res = await microkernel_engine.execute_dag(
            config=dag_config,
            initial_inputs=req.inputs,
            initial_context=req.context,
            trace_id=tid,
            override_dispatch_mode=req.override_dispatch_mode,
        )

        effective_mode = req.override_dispatch_mode.value if req.override_dispatch_mode else dispatcher.default_mode.value

        return ScenarioExecuteResponse(
            scenario_code=req.scenario_code,
            status=res.status.value,
            execution_time_ms=res.total_duration_ms,
            trace_id=res.trace_id,
            effective_dispatch_mode=effective_mode,
            node_traces=[t.model_dump() for t in res.node_traces],
            final_output=res.final_output,
            error_message=res.error_message,
            error_type=res.error_type,
            compensation_traces=[c.model_dump() for c in res.compensation_traces],
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
            return ScenarioExecuteResponse(
                scenario_code=req.scenario_code, status="FAILED",
                execution_time_ms=round((_time.perf_counter() - started) * 1000, 2),
                trace_id=tid, effective_dispatch_mode="IN_PROCESS",
                node_traces=[], final_output={},
                error_message=str(exc), error_type="KeyError",
            )
        except (PermissionError, ValueError) as exc:
            # The legacy engine marked permission failures GUARD_REJECTED.
            status = "GUARD_REJECTED" if isinstance(exc, PermissionError) else "FAILED"
            return ScenarioExecuteResponse(
                scenario_code=req.scenario_code, status=status,
                execution_time_ms=round((_time.perf_counter() - started) * 1000, 2),
                trace_id=tid, effective_dispatch_mode="IN_PROCESS",
                node_traces=[], final_output={},
                error_message=str(exc), error_type=type(exc).__name__,
            )
        return ScenarioExecuteResponse(
            scenario_code=req.scenario_code,
            status="SUCCESS",
            execution_time_ms=round((_time.perf_counter() - started) * 1000, 2),
            trace_id=run.trace_id or tid,
            effective_dispatch_mode="IN_PROCESS",
            node_traces=run.node_traces,
            final_output=run.final_output,
        )

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