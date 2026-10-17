"""Service for saving and loading versioned DAG configs, frontend visual layouts, and executing composable scenarios."""
import uuid
import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

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
from src.core.microkernel.dispatcher import dispatcher, DispatchMode
from src.core.microkernel.engine import microkernel_engine
from src.core.microkernel.models import (
    DAGConfig,
    ExecutionGraph,
    NodeDef,
    EdgeDef,
    NodeType,
)
from src.core.telemetry import get_current_trace_id


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class OrchestrationService:
    """Manages versioned DAG configs, frontend layouts, and executes composable scenarios."""

    def __init__(self):
        # Key: (scenario_code, version)
        self._dag_configs: Dict[Tuple[str, str], DAGConfigRecord] = {}
        # Key: layout_name
        self._layouts: Dict[str, FrontendLayoutRecord] = {}
        self._seed_default_configs()

    def _seed_default_configs(self):
        # 1. Default VAT exemption DAG
        topo_vat = {
            "topology": "DAG",
            "entry_node": "dnode-1",
            "nodes": [
                {"id": "dnode-1", "action_handler": "gateway_ingress", "type": "GATEWAY"},
                {"id": "dnode-2", "action_handler": "auth_guard", "type": "GUARD"},
                {"id": "dnode-3", "action_handler": "invoice_tax_calc", "type": "BIZ"},
                {"id": "dnode-4", "action_handler": "es_audit_sync", "type": "STORAGE"},
            ],
            "edges": [
                {"from": "dnode-1", "to": "dnode-2"},
                {"from": "dnode-2", "to": "dnode-3"},
                {"from": "dnode-3", "to": "dnode-4"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="tax.calculate_vat_exemption",
                version="v1.0.4-draft",
                topology_graph=topo_vat,
                status="ACTIVE",
            )
        )

        # 2. Composable Startup Compliance Pipeline: OPC_COMPLIANCE_STARTUP_FLOW
        topo_startup = {
            "topology": "DAG",
            "entry_node": "step_auth",
            "nodes": [
                {"id": "step_auth", "action_handler": "auth_guard", "type": "GUARD"},
                {"id": "step_tax_calc", "action_handler": "policy.calculate_tax", "type": "BIZ"},
                {"id": "step_ai_charter", "action_handler": "external.ai.generate_charter", "type": "BIZ"},
                {"id": "step_render_sop", "action_handler": "sop.render_document", "type": "STORAGE"},
                {"id": "step_compliance", "action_handler": "compliance.evaluate_audit", "type": "GUARD"},
            ],
            "edges": [
                {"from": "step_auth", "to": "step_tax_calc"},
                {"from": "step_tax_calc", "to": "step_ai_charter"},
                {"from": "step_ai_charter", "to": "step_render_sop"},
                {"from": "step_render_sop", "to": "step_compliance"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_COMPLIANCE_STARTUP_FLOW",
                version="v1.0.0",
                topology_graph=topo_startup,
                status="ACTIVE",
            )
        )

        # 3. Composable Policy Tax & AI Match Pipeline: OPC_POLICY_TAX_AI_MATCH
        topo_policy = {
            "topology": "DAG",
            "entry_node": "step_ingress",
            "nodes": [
                {"id": "step_ingress", "action_handler": "gateway_ingress", "type": "GATEWAY"},
                {"id": "step_auth", "action_handler": "auth_guard", "type": "GUARD"},
                {"id": "step_tax_calc", "action_handler": "invoice_tax_calc", "type": "BIZ"},
                {"id": "step_subsidies", "action_handler": "policy.match_subsidies", "type": "BIZ"},
                {"id": "step_audit", "action_handler": "es_audit_sync", "type": "STORAGE"},
            ],
            "edges": [
                {"from": "step_ingress", "to": "step_auth"},
                {"from": "step_auth", "to": "step_tax_calc"},
                {"from": "step_tax_calc", "to": "step_subsidies"},
                {"from": "step_subsidies", "to": "step_audit"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_POLICY_TAX_AI_MATCH",
                version="v1.0.0",
                topology_graph=topo_policy,
                status="ACTIVE",
            )
        )

        # 4. Composable Home Overview Pipeline: OPC_HOME_OVERVIEW_PIPELINE
        topo_home = {
            "topology": "DAG",
            "entry_node": "step_metrics",
            "nodes": [
                {"id": "step_metrics", "action_handler": "home.metrics.collector", "type": "BIZ"},
                {"id": "step_sitemap", "action_handler": "home.sitemap.builder", "type": "BIZ"},
                {"id": "step_agg", "action_handler": "home.overview.aggregator", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_metrics", "to": "step_sitemap"},
                {"from": "step_sitemap", "to": "step_agg"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_HOME_OVERVIEW_PIPELINE",
                version="v1.0.0",
                topology_graph=topo_home,
                status="ACTIVE",
            )
        )

        # 5. Forum Thread Publish DAG Pipeline: OPC_FORUM_THREAD_PUBLISH
        topo_forum_thread = {
            "topology": "DAG",
            "entry_node": "step_guard",
            "enable_saga_compensation": True,
            "nodes": [
                {"id": "step_guard", "action_handler": "forum.thread.validate_guard", "type": "GUARD"},
                {"id": "step_persist", "action_handler": "forum.thread.persist", "type": "STORAGE"},
                {"id": "step_telemetry", "action_handler": "forum.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_guard", "to": "step_persist"},
                {"from": "step_persist", "to": "step_telemetry"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_FORUM_THREAD_PUBLISH",
                version="v1.0.0",
                topology_graph=topo_forum_thread,
                status="ACTIVE",
            )
        )

        # 6. Forum Comment Publish DAG Pipeline: OPC_FORUM_COMMENT_PUBLISH
        topo_forum_comment = {
            "topology": "DAG",
            "entry_node": "step_guard",
            "enable_saga_compensation": True,
            "nodes": [
                {"id": "step_guard", "action_handler": "forum.comment.validate_guard", "type": "GUARD"},
                {"id": "step_persist", "action_handler": "forum.comment.persist", "type": "STORAGE"},
                {"id": "step_telemetry", "action_handler": "forum.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_guard", "to": "step_persist"},
                {"from": "step_persist", "to": "step_telemetry"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_FORUM_COMMENT_PUBLISH",
                version="v1.0.0",
                topology_graph=topo_forum_comment,
                status="ACTIVE",
            )
        )

        # 7. Product Showcase Publish DAG Pipeline: OPC_PRODUCT_PUBLISH_PIPELINE
        topo_product_publish = {
            "topology": "DAG",
            "entry_node": "step_guard",
            "enable_saga_compensation": True,
            "nodes": [
                {"id": "step_guard", "action_handler": "product.validate_guard", "type": "GUARD"},
                {"id": "step_persist", "action_handler": "product.persist", "type": "STORAGE"},
                {"id": "step_telemetry", "action_handler": "product.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_guard", "to": "step_persist"},
                {"from": "step_persist", "to": "step_telemetry"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_PRODUCT_PUBLISH_PIPELINE",
                version="v1.0.0",
                topology_graph=topo_product_publish,
                status="ACTIVE",
            )
        )

        # 8. Policy Radar Match DAG Pipeline: OPC_POLICY_MATCH_PIPELINE
        topo_policy_match = {
            "topology": "DAG",
            "entry_node": "step_guard",
            "enable_saga_compensation": True,
            "nodes": [
                {"id": "step_guard", "action_handler": "policy.qualify_guard", "type": "GUARD"},
                {"id": "step_tax", "action_handler": "policy.calculate_tax", "type": "BIZ"},
                {"id": "step_subsidies", "action_handler": "policy.match_subsidies", "type": "BIZ"},
                {"id": "step_telemetry", "action_handler": "policy.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_guard", "to": "step_tax"},
                {"from": "step_tax", "to": "step_subsidies"},
                {"from": "step_subsidies", "to": "step_telemetry"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_POLICY_MATCH_PIPELINE",
                version="v1.0.0",
                topology_graph=topo_policy_match,
                status="ACTIVE",
            )
        )

        # 9. Policy Radar Publish DAG Pipeline: OPC_POLICY_PUBLISH_PIPELINE
        topo_policy_publish = {
            "topology": "DAG",
            "entry_node": "step_guard",
            "enable_saga_compensation": True,
            "nodes": [
                {"id": "step_guard", "action_handler": "policy.publish.guard", "type": "GUARD"},
                {"id": "step_persist", "action_handler": "policy.publish.persist", "type": "STORAGE"},
                {"id": "step_telemetry", "action_handler": "policy.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_guard", "to": "step_persist"},
                {"from": "step_persist", "to": "step_telemetry"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_POLICY_PUBLISH_PIPELINE",
                version="v1.0.0",
                topology_graph=topo_policy_publish,
                status="ACTIVE",
            )
        )

        # 10. Demands Publish DAG Pipeline: OPC_DEMAND_PUBLISH_PIPELINE
        topo_demand_publish = {
            "topology": "DAG",
            "entry_node": "step_guard",
            "enable_saga_compensation": True,
            "nodes": [
                {"id": "step_guard", "action_handler": "demand.publish.guard", "type": "GUARD"},
                {"id": "step_persist", "action_handler": "demand.publish.persist", "type": "STORAGE"},
                {"id": "step_telemetry", "action_handler": "demand.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_guard", "to": "step_persist"},
                {"from": "step_persist", "to": "step_telemetry"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_DEMAND_PUBLISH_PIPELINE",
                version="v1.0.0",
                topology_graph=topo_demand_publish,
                status="ACTIVE",
            )
        )

        # 11. Demands Bid DAG Pipeline: OPC_DEMAND_BID_PIPELINE
        topo_demand_bid = {
            "topology": "DAG",
            "entry_node": "step_guard",
            "enable_saga_compensation": True,
            "nodes": [
                {"id": "step_guard", "action_handler": "demand.bid.guard", "type": "GUARD"},
                {"id": "step_persist", "action_handler": "demand.bid.persist", "type": "STORAGE"},
                {"id": "step_telemetry", "action_handler": "demand.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_guard", "to": "step_persist"},
                {"from": "step_persist", "to": "step_telemetry"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_DEMAND_BID_PIPELINE",
                version="v1.0.0",
                topology_graph=topo_demand_bid,
                status="ACTIVE",
            )
        )

        # 12. SOP Document Render DAG Pipeline: OPC_SOP_DOCUMENT_RENDER_PIPELINE
        topo_sop_render = {
            "topology": "DAG",
            "entry_node": "step_guard",
            "enable_saga_compensation": True,
            "nodes": [
                {"id": "step_guard", "action_handler": "sop.document.validate_guard", "type": "GUARD"},
                {"id": "step_persist", "action_handler": "sop.document.render_persist", "type": "STORAGE"},
                {"id": "step_telemetry", "action_handler": "sop.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_guard", "to": "step_persist"},
                {"from": "step_persist", "to": "step_telemetry"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_SOP_DOCUMENT_RENDER_PIPELINE",
                version="v1.0.0",
                topology_graph=topo_sop_render,
                status="ACTIVE",
            )
        )

        # 13. Perks Claim DAG Pipeline: OPC_PERK_CLAIM_PIPELINE
        topo_perk_claim = {
            "topology": "DAG",
            "entry_node": "step_guard",
            "enable_saga_compensation": True,
            "nodes": [
                {"id": "step_guard", "action_handler": "perk.claim.guard", "type": "GUARD"},
                {"id": "step_persist", "action_handler": "perk.claim.persist", "type": "STORAGE"},
                {"id": "step_telemetry", "action_handler": "perk.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_guard", "to": "step_persist"},
                {"from": "step_persist", "to": "step_telemetry"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_PERK_CLAIM_PIPELINE",
                version="v1.0.0",
                topology_graph=topo_perk_claim,
                status="ACTIVE",
            )
        )

        # 14. Perks Publish DAG Pipeline: OPC_PERK_PUBLISH_PIPELINE
        topo_perk_publish = {
            "topology": "DAG",
            "entry_node": "step_guard",
            "enable_saga_compensation": True,
            "nodes": [
                {"id": "step_guard", "action_handler": "perk.publish.guard", "type": "GUARD"},
                {"id": "step_persist", "action_handler": "perk.publish.persist", "type": "STORAGE"},
                {"id": "step_telemetry", "action_handler": "perk.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_guard", "to": "step_persist"},
                {"from": "step_persist", "to": "step_telemetry"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_PERK_PUBLISH_PIPELINE",
                version="v1.0.0",
                topology_graph=topo_perk_publish,
                status="ACTIVE",
            )
        )

        # 15. Compliance Audit DAG Pipeline: OPC_COMPLIANCE_AUDIT_PIPELINE
        topo_compliance_audit = {
            "topology": "DAG",
            "entry_node": "step_guard",
            "enable_saga_compensation": True,
            "nodes": [
                {"id": "step_guard", "action_handler": "compliance.audit.guard", "type": "GUARD"},
                {"id": "step_eval", "action_handler": "compliance.evaluate_audit", "type": "BIZ"},
                {"id": "step_telemetry", "action_handler": "compliance.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_guard", "to": "step_eval"},
                {"from": "step_eval", "to": "step_telemetry"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_COMPLIANCE_AUDIT_PIPELINE",
                version="v1.0.0",
                topology_graph=topo_compliance_audit,
                status="ACTIVE",
            )
        )







        # Default frontend layout
        self.save_frontend_layout(
            FrontendLayoutSaveRequest(
                layout_name="main_console_layout",
                version="v1.0.4",
                grid_schema={"columns": 24, "row_gap": 16, "col_gap": 16},
                widgets=[
                    {"id": "w1", "type": "stat", "span": 6, "title": "本季总创收", "value": "¥ 280,000"},
                    {"id": "w2", "type": "stat", "span": 6, "title": "免征增值税", "value": "¥ 8,400"},
                    {"id": "w3", "type": "form", "span": 12, "title": "政策核算申报入口"},
                ],
            )
        )

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
        return record

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
        """Execute a composable scenario DAG pipeline."""
        tid = trace_id or get_current_trace_id()
        # Find latest active DAG config for the scenario
        candidates = [c for c in self._dag_configs.values() if c.scenario_code == req.scenario_code and c.status == "ACTIVE"]
        if not candidates:
            # Fallback to any version
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
                )
            )

        edges = []
        for e in topo.get("edges", []):
            edges.append(
                EdgeDef(
                    from_node=e.get("from") or e.get("from_node"),
                    to_node=e.get("to") or e.get("to_node"),
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
            compensation_traces=[c.model_dump() for c in res.compensation_traces],
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
        return record

    def get_frontend_layout(self, layout_name: str = "main_console_layout") -> FrontendLayoutRecord:
        if layout_name not in self._layouts:
            raise KeyError(f"Frontend layout {layout_name} not found")
        return self._layouts[layout_name]


orchestration_service = OrchestrationService()
