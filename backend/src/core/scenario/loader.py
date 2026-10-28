"""Scenario asset loader: compiles YAML business compositions into DAG configs.

Business flows are *configuration*, not Python. Each YAML asset declares a
scenario code, a version, the operator per node, static params and the input
mapping. The loader validates the shape and registers the compiled topology with
the orchestration service, which the microkernel engine then executes.

Asset format::

    scenario: OPC_PRODUCT_PUBLISH
    version: v1.0.0
    description: 发布产品橱窗作品
    nodes:
      - id: auth
        operator: guard.authn
      - id: create
        operator: entity.create
        params: {entity: product.item}
        inputs:
          data:
            title: $inputs.title
            author_id: $context.user_id
    edges:
      - [auth, create]
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

import yaml

from src.domains.orchestration.models import DAGConfigSaveRequest
from src.domains.orchestration.service import orchestration_service

logger = logging.getLogger("opchub.scenario.loader")

_NODE_TYPE_BY_PREFIX = {
    "guard": "GUARD",
    "validate": "GUARD",
    "entity": "STORAGE",
    "render": "BIZ",
    "response": "BIZ",
}


def _infer_type(operator_name: str) -> str:
    prefix = operator_name.split(".", 1)[0]
    return _NODE_TYPE_BY_PREFIX.get(prefix, "BIZ")


def _normalise_edges(raw_edges: Any, node_ids: set[str]) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for edge in raw_edges or []:
        if isinstance(edge, dict):
            source = edge.get("from")
            target = edge.get("to")
            when = edge.get("when")
        elif isinstance(edge, (list, tuple)) and len(edge) >= 2:
            source, target = edge[0], edge[1]
            when = edge[2] if len(edge) > 2 else None
        else:
            raise ValueError(f"Unsupported edge declaration: {edge!r}")
        if source not in node_ids or target not in node_ids:
            raise ValueError(f"Edge references unknown node: {source!r} -> {target!r}")
        item: dict[str, Any] = {"from": source, "to": target}
        if when:
            item["when"] = when
        edges.append(item)
    return edges


def compile_scenario(asset: dict[str, Any]) -> dict[str, Any]:
    """Compile one YAML asset into the stored topology_graph structure."""
    code = str(asset.get("scenario") or "").strip()
    if not code:
        raise ValueError("Scenario asset is missing 'scenario'")
    version = str(asset.get("version") or "v1.0.0")
    raw_nodes = asset.get("nodes") or []
    if not raw_nodes:
        raise ValueError(f"Scenario '{code}' has no nodes")

    nodes: list[dict[str, Any]] = []
    node_ids: set[str] = set()
    for raw in raw_nodes:
        node_id = str(raw.get("id") or "").strip()
        operator_name = str(raw.get("operator") or raw.get("action_handler") or "").strip()
        if not node_id or not operator_name:
            raise ValueError(f"Scenario '{code}' has a node without id/operator")
        if node_id in node_ids:
            raise ValueError(f"Scenario '{code}' has duplicate node id '{node_id}'")
        node_ids.add(node_id)
        node: dict[str, Any] = {
            "id": node_id,
            "action_handler": operator_name,
            "type": raw.get("type") or _infer_type(operator_name),
        }
        if raw.get("params"):
            node["params"] = raw["params"]
        inputs_map = raw.get("inputs_map") or raw.get("inputs")
        if inputs_map:
            node["inputs_map"] = inputs_map
        if raw.get("when"):
            node["when"] = raw["when"]
        if raw.get("output_key"):
            node["output_key"] = raw["output_key"]
        if raw.get("retry") is not None:
            node["retry"] = int(raw["retry"])
        if raw.get("timeout_ms") is not None:
            node["timeout_ms"] = int(raw["timeout_ms"])
        nodes.append(node)

    edges = _normalise_edges(asset.get("edges"), node_ids)
    entry = asset.get("entry")
    if entry and entry not in node_ids:
        raise ValueError(f"Scenario '{code}' declares unknown entry '{entry}'")

    return {
        "topology": "DAG",
        "entry_node": entry or nodes[0]["id"],
        "exit_node": asset.get("exit"),
        "enable_saga_compensation": bool(asset.get("saga", True)),
        "nodes": nodes,
        "edges": edges,
        "description": asset.get("description", ""),
        "domain": asset.get("domain", ""),
    }


class ScenarioLoader:
    """Loads every ``config/scenarios/*.yaml`` asset into the orchestrator."""

    DEFAULT_LOCATIONS = [
        Path("backend/config/scenarios"),
        Path("config/scenarios"),
        Path(__file__).resolve().parents[3] / "config" / "scenarios",
    ]

    def __init__(self, directory: Optional[str | Path] = None):
        self._directory = Path(directory) if directory else self._find_directory()
        self._loaded = False

    @classmethod
    def _find_directory(cls) -> Path:
        env_path = os.getenv("OPCHUB_SCENARIOS_DIR")
        if env_path and Path(env_path).is_dir():
            return Path(env_path)
        for candidate in cls.DEFAULT_LOCATIONS:
            if candidate.is_dir():
                return candidate.resolve()
        return cls.DEFAULT_LOCATIONS[-1]

    @property
    def directory(self) -> Path:
        return self._directory

    def load(self, force: bool = False) -> int:
        if self._loaded and not force:
            return 0
        if not self._directory.is_dir():
            logger.warning("Scenario directory not found: %s", self._directory)
            self._loaded = True
            return 0

        existing = {
            (config.scenario_code, config.version)
            for config in orchestration_service.list_dag_configs()
        }
        count = 0
        for asset_file in sorted(self._directory.glob("*.yaml")):
            try:
                payload = yaml.safe_load(asset_file.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError as exc:
                raise ValueError(f"Invalid scenario YAML {asset_file}: {exc}") from exc
            assets = payload.get("scenarios") if isinstance(payload, dict) and "scenarios" in payload else [payload]
            for asset in assets:
                if not isinstance(asset, dict):
                    continue
                topology = compile_scenario(asset)
                code = str(asset["scenario"])
                version = str(asset.get("version") or "v1.0.0")
                if (code, version) in existing and not force:
                    continue
                orchestration_service.save_dag_config(
                    DAGConfigSaveRequest(
                        scenario_code=code,
                        version=version,
                        topology_graph=topology,
                        status=asset.get("status", "ACTIVE"),
                        created_by=asset.get("created_by", "scenario_asset"),
                    )
                )
                existing.add((code, version))
                count += 1
        self._loaded = True
        logger.info("Loaded %s scenario assets from %s", count, self._directory)
        return count


_loader: ScenarioLoader | None = None


def ensure_scenarios_loaded(force: bool = False) -> int:
    global _loader
    if _loader is None:
        _loader = ScenarioLoader()
    return _loader.load(force=force)
