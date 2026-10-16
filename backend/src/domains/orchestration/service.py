"""Service for saving and loading versioned DAG configs and frontend visual layouts."""
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
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class OrchestrationService:
    """Manages versioned DAG configs and frontend layouts."""

    def __init__(self):
        # Key: (scenario_code, version)
        self._dag_configs: Dict[Tuple[str, str], DAGConfigRecord] = {}
        # Key: layout_name
        self._layouts: Dict[str, FrontendLayoutRecord] = {}
        self._seed_default_configs()

    def _seed_default_configs(self):
        # Default DAG config
        topo = {
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
                topology_graph=topo,
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
