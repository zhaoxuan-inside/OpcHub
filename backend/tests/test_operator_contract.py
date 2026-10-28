"""Conformance tests for the operator kernel.

These tests are the executable version of
``hs_dev_docs/_03_architecture_design/_03_detailed_design/_06_operator_kernel_v2.md``.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest
import yaml

BACKEND = Path(__file__).resolve().parents[1]
GENERIC_OPERATORS = BACKEND / "src" / "core" / "operators"
DOMAINS = BACKEND / "src" / "domains"
SCENARIOS = BACKEND / "config" / "scenarios"

ALLOWED_GENERIC_PREFIXES = {
    "guard",
    "validate",
    "transform",
    "entity",
    "notify",
    "audit",
    "metric",
    "render",
    "external",
    "response",
    "query",
}

FORBIDDEN_FUNCTION_CALLS = {
    "execute_scenario",
    "execute_dag",
    "microkernel_engine",
    "orchestration_service",
    "domain_persistence",
}
FORBIDDEN_FUNCTION_IMPORTS = {"requests", "httpx", "urllib", "aiohttp", "sqlalchemy"}


def _domain_name(path: Path) -> str:
    relative = path.relative_to(DOMAINS)
    return relative.parts[0]


def _iter_python(directory: Path):
    for path in directory.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


def test_generic_operators_do_not_import_domains() -> None:
    offenders: list[str] = []
    for path in _iter_python(GENERIC_OPERATORS):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("src.domains"):
                        offenders.append(f"{path.name}:{node.lineno} -> {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module.startswith("src.domains"):
                    offenders.append(f"{path.name}:{node.lineno} -> {module}")
    assert not offenders, "Generic operators must stay business-agnostic:\n" + "\n".join(offenders)


def test_generic_operator_names_are_business_agnostic() -> None:
    offenders: list[str] = []
    for path in _iter_python(GENERIC_OPERATORS):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name) and func.id == "operator" and node.args:
                name = node.args[0]
                if isinstance(name, ast.Constant) and isinstance(name.value, str):
                    prefix = name.value.split(".", 1)[0]
                    if prefix not in ALLOWED_GENERIC_PREFIXES:
                        offenders.append(name.value)
    assert not offenders, f"Non-generic operator names found: {offenders}"


def test_domain_functions_are_single_purpose_and_pure() -> None:
    offenders: list[str] = []
    for path in _iter_python(DOMAINS):
        if path.name != "functions.py":
            continue
        owner = _domain_name(path)
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                modules = []
                if isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                else:
                    modules = [node.module or ""]
                for module in modules:
                    if module.startswith("src.domains") and not module.startswith(f"src.domains.{owner}"):
                        offenders.append(f"{path}:{node.lineno} cross-domain import {module}")
                    if module.split(".", 1)[0] in FORBIDDEN_FUNCTION_IMPORTS:
                        offenders.append(f"{path}:{node.lineno} forbidden import {module}")
            elif isinstance(node, ast.Call):
                func = node.func
                name = None
                if isinstance(func, ast.Name):
                    name = func.id
                elif isinstance(func, ast.Attribute):
                    name = func.attr
                if name in FORBIDDEN_FUNCTION_CALLS:
                    offenders.append(f"{path}:{node.lineno} forbidden call {name}")
    assert not offenders, "Domain functions must be single-purpose and pure:\n" + "\n".join(offenders)


def test_all_scenario_assets_compile() -> None:
    from src.core.scenario.loader import compile_scenario

    failures: list[str] = []
    for path in sorted(SCENARIOS.glob("*.yaml")):
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        assets = payload.get("scenarios") if isinstance(payload, dict) and "scenarios" in payload else [payload]
        for asset in assets:
            try:
                topology = compile_scenario(asset)
                node_ids = {node["id"] for node in topology["nodes"]}
                incoming = {node_id: 0 for node_id in node_ids}
                outgoing = {node_id: 0 for node_id in node_ids}
                for edge in topology["edges"]:
                    outgoing[edge["from"]] += 1
                    incoming[edge["to"]] += 1
                entries = [n for n, degree in incoming.items() if degree == 0]
                exits = [n for n, degree in outgoing.items() if degree == 0]
                assert len(entries) == 1, f"{asset['scenario']} has entries {entries}"
                assert len(exits) == 1, f"{asset['scenario']} has exits {exits}"
            except Exception as exc:  # noqa: BLE001 - aggregated assertion
                failures.append(f"{path.name}/{asset.get('scenario')}: {exc}")
    assert not failures, "Invalid scenario assets:\n" + "\n".join(failures)


def test_scenario_operators_are_registered() -> None:
    from src.core.microkernel.registry import registry
    from src.core.scenario.loader import compile_scenario

    registered = set(registry.list_handlers())
    missing: list[str] = []
    for path in sorted(SCENARIOS.glob("*.yaml")):
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        assets = payload.get("scenarios") if isinstance(payload, dict) and "scenarios" in payload else [payload]
        for asset in assets:
            topology = compile_scenario(asset)
            for node in topology["nodes"]:
                if node["action_handler"] not in registered:
                    missing.append(f"{asset['scenario']}:{node['action_handler']}")
    assert not missing, "Scenario references unknown operators:\n" + "\n".join(sorted(set(missing)))
