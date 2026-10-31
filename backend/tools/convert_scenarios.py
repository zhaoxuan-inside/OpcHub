"""Convert OpcHub scenario YAML assets into MicroFlow4Python flow definitions.

One-shot migration tool (framework-replacement project). Reads
``config/scenarios/*.yaml`` and emits a MicroFlow project JSON
(``config/flows/opchub_flows.json``) plus a conversion report
(``config/flows/conversion_report.json``). Unmappable constructs are collected
per scenario and must be resolved — the tool never drops anything silently.

Mapping rules (engine semantics preserved):

- ``$inputs.k``            -> ``flow.input.payload.k``  (identity keys read the
  ``guard.authn`` node output when the scenario has one, mirroring the old
  ``inputs.update(node_output)`` scope spreading)
- ``$context.x``           -> ``flow.input.__context__.x`` (the host gateway
  bridge injects the request context snapshot under ``__context__``; the key is
  bridge-controlled and overrides any payload field of the same name)
- ``$nodes.id`` / ``$nodes.id.f`` -> ``nodes.id.output.data[.f]``
- static ``params`` leaves -> ``{"from": "context.__mf_params__.<k>",
  "required": false, "default": <literal>}`` (``context.__mf_params__`` is a
  framework-owned, guaranteed-missing namespace, so the default literal is the
  only possible value; ``from`` is mandatory in MicroFlow mapping rules)
- ``params`` subtrees containing ``$`` references are decomposed leaf-by-leaf
- ``when: <expr>``         -> MicroFlow condition AST via a Python-AST
  translation of the OpcHub safe-expression subset; bare paths become
  ``truthy`` (missing -> False, faithful to ``engine._truthy``); comparisons
  gain ``exists`` guards so a missing operand is False for eq/lt/... and True
  for ne (``and``/``or`` short-circuit in the framework evaluator)
- YAML ``edges``           -> ``depends_on`` control edges, preserving the old
  topological order that ``final_output`` key precedence depends on
- ``guard.*`` nodes stay ordinary operators (the gateway RBAC layer is
  unchanged and still enforces permissions before dispatch)
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

BACKEND_DIR = Path(__file__).resolve().parents[1]
SCENARIO_DIR = BACKEND_DIR / "config" / "scenarios"
OUTPUT_DIR = BACKEND_DIR / "config" / "flows"

MF_PARAMS_ROOT = "context.__mf_params__"
FLOW_INPUT_SCHEMA = {"type": "object", "additionalProperties": True}
PERMISSIVE_NOTE = "permissive object schemas; operator-level validation stays in OpcHub code"

# Keys that the old engine's scope spreading resolved from guard.authn output.
AUTHN_OUTPUT_KEYS = {"user_id", "user_role"}


class Unmappable(Exception):
    """A construct the converter refuses to guess at."""


# ---------------------------------------------------------------------------
# OpcHub safe-expression AST -> MicroFlow condition AST
# ---------------------------------------------------------------------------
def _path_of(node: ast.AST) -> str:
    """Translate a Name/Attribute chain rooted at inputs/nodes/context."""
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if not isinstance(current, ast.Name):
        raise Unmappable(f"expression path root {ast.dump(node)[:80]}")
    parts.append(current.id)
    parts.reverse()
    root = parts[0]
    rest = parts[1:]
    if root == "inputs":
        return ".".join(["flow", "input", "payload", *rest])
    if root == "context":
        return ".".join(["flow", "input", "__context__", *rest])
    if root == "nodes":
        if not rest:
            raise Unmappable("bare 'nodes' reference")
        head, *tail = rest
        return _node_source(head, *tail)
    raise Unmappable(f"expression root '{root}'")


def _operand(node: ast.AST) -> Any:
    """Comparison operand: a path reference or a JSON literal."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, int, float, bool)) or (
            isinstance(node, ast.Constant) and node.value is None):
        return node.value
    if isinstance(node, (ast.Name, ast.Attribute)):
        return {"path": _path_of(node)}
    if isinstance(node, ast.Subscript):
        raise Unmappable("subscript operand in condition")
    raise Unmappable(f"condition operand {type(node).__name__}")


_CMP_OPS = {
    ast.Eq: "eq", ast.NotEq: "ne", ast.Lt: "lt", ast.LtE: "lte",
    ast.Gt: "gt", ast.GtE: "gte", ast.In: "in", ast.Is: "eq", ast.IsNot: "ne",
}
_MISSING_TRUE_OPS = {"ne"}  # OpcHub: None != X -> True; missing path behaves as None


def _comparison(left: ast.AST, op: ast.AST, right: ast.AST) -> dict[str, Any]:
    if type(op) in (ast.NotIn,):
        inner = _comparison(left, ast.In(), right)
        return {"not": inner}
    name = _CMP_OPS.get(type(op))
    if name is None:
        raise Unmappable(f"comparison {type(op).__name__}")
    mf_left, mf_right = _operand(left), _operand(right)
    payload = {name: [mf_left, mf_right]}
    guard_paths = [v["path"] for v in (mf_left, mf_right) if isinstance(v, dict) and "path" in v]
    if not guard_paths:
        return payload
    if name in _MISSING_TRUE_OPS:
        # Missing operand must evaluate truthy (OpcHub compares None != X).
        escapes = [{"not": {"exists": p}} for p in guard_paths]
        return {"or": [*escapes, payload]}
    # Missing operand must evaluate falsy; "and" short-circuits on first False.
    return {"and": [{"exists": p} for p in guard_paths] + [payload]}


def translate_condition(expression: str) -> dict[str, Any]:
    """Translate one OpcHub ``when`` expression into the MicroFlow whitelist AST."""
    source = str(expression).strip().lstrip("$")
    tree = ast.parse(source, mode="eval").body

    def walk(node: ast.AST) -> dict[str, Any]:
        if isinstance(node, ast.BoolOp):
            op = "and" if isinstance(node.op, ast.And) else "or"
            return {op: [walk(v) for v in node.values]}
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return {"not": walk(node.operand)}
        if isinstance(node, ast.Compare):
            # Chained comparisons become a conjunction of pairwise comparisons
            # (the middle operand is re-evaluated; conditions are side-effect free).
            clauses = []
            left = node.left
            for op, comparator in zip(node.ops, node.comparators):
                clauses.append(_comparison(left, op, comparator))
                left = comparator
            return clauses[0] if len(clauses) == 1 else {"and": clauses}
        if isinstance(node, ast.Constant):
            raise Unmappable(f"bare literal condition {node.value!r}")
        if isinstance(node, (ast.Name, ast.Attribute)):
            return {"truthy": _path_of(node)}
        if isinstance(node, ast.Call):
            if (isinstance(node.func, ast.Name) and node.func.id == "bool" and len(node.args) == 1
                    and isinstance(node.args[0], (ast.Name, ast.Attribute))):
                return {"truthy": _path_of(node.args[0])}
            raise Unmappable(f"call in condition: {ast.dump(node)[:80]}")
        if isinstance(node, ast.BinOp):
            raise Unmappable(f"arithmetic in condition: {ast.dump(node)[:80]}")
        if isinstance(node, ast.IfExp):
            raise Unmappable("ternary in condition")
        raise Unmappable(f"condition construct {type(node).__name__}")

    return walk(tree)


# ---------------------------------------------------------------------------
# params / inputs mapping
# ---------------------------------------------------------------------------
def _is_ref(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    stripped = value.strip()
    return stripped.startswith(("$inputs.", "$nodes.", "$context.")) or stripped in ("$inputs", "$nodes", "$context")


_FIELD_RE = re.compile(r"[A-Za-z_][A-Za-z_0-9-]*")


def _node_source(node_id: str, *rest: str) -> str:
    """Source path into a node's output; quotes ids the dotted form cannot hold."""
    if _FIELD_RE.fullmatch(node_id):
        base = f"nodes.{node_id}.output.data"
    else:
        base = f'nodes["{node_id}"].output.data'
    return ".".join([base, *rest]) if rest else base


def _map_reference(reference: str) -> str:
    """Resolve one ``$``-reference into a MicroFlow source path."""
    ref = reference.strip()
    if not ref.startswith("$"):
        raise Unmappable(f"non-reference value {reference!r}")
    body = ref[1:]
    root, _, tail = body.partition(".")
    if root == "inputs":
        return ".".join(["flow", "input", "payload", tail]) if tail else "flow.input.payload"
    if root == "context":
        return ".".join(["flow", "input", "__context__", tail]) if tail else "flow.input.__context__"
    if root == "nodes":
        head, _, tail2 = tail.partition(".")
        if not head:
            raise Unmappable("bare 'nodes' reference")
        rest = (tail2,) if tail2 else ()
        return _node_source(head, *rest)
    raise Unmappable(f"reference root '{root}'")


def _has_ref(value: Any) -> bool:
    if _is_ref(value):
        return True
    if isinstance(value, dict):
        return any(_has_ref(v) for v in value.values())
    if isinstance(value, list):
        return any(_has_ref(v) for v in value)
    return False


def _emit_params(prefix: str, value: Any, inputs: dict[str, Any], counter: dict[str, int],
                 synth: list[dict[str, Any]], owner: str) -> None:
    """Emit mapping rules for one params subtree (static leaves via defaults).

    Lists that mix ``$``-references with literals cannot be built by MicroFlow
    mappings (SPARSE_ARRAY guard); the converter synthesizes an ``assemble.list``
    node that aggregates the elements and the param becomes a node reference.
    """
    if isinstance(value, list) and any(_has_ref(v) for v in value):
        synth.append({"owner": owner, "param": prefix, "elements": value})
        return
    if _has_ref(value) and not isinstance(value, str):
        if isinstance(value, dict):
            for key, item in value.items():
                _emit_params(f"{prefix}.{key}", item, inputs, counter, synth, owner)
            return
        raise Unmappable(f"unsupported $ container under params.{prefix}")
    if isinstance(value, str) and value.strip().startswith("$"):
        inputs[prefix] = {"from": _map_reference(value), "required": False, "default": None}
        return
    # Static subtree: guaranteed-missing source + literal default.
    counter["static"] = counter.get("static", 0) + 1
    inputs[prefix] = {"from": f"{MF_PARAMS_ROOT}.{prefix}", "required": False, "default": value}


def convert_inputs_map(raw_inputs: Any, authn_id: str | None, scenario: str,
                       unmapped: list[str], synth: list[dict[str, Any]],
                       owner: str, authn_precedes: bool = False,
                       authn_spreads: bool = False) -> dict[str, Any]:
    rules: dict[str, Any] = {}
    if not raw_inputs:
        return rules
    if not isinstance(raw_inputs, dict):
        unmapped.append(f"inputs is {type(raw_inputs).__name__}, expected object")
        return rules

    def walk(prefix: str, value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                walk(f"{prefix}.{key}" if prefix else str(key), item)
            return
        if isinstance(value, list):
            if any(_has_ref(v) for v in value):
                # Lists cannot be built by MicroFlow mappings; route through a
                # synthesized assemble.list node like params lists.
                synth.append({"owner": owner, "param": f"args.{prefix}", "elements": value})
            else:
                rules[f"args.{prefix}"] = {"from": f"{MF_PARAMS_ROOT}.args.{prefix}",
                                           "required": False, "default": value}
            return
        if _is_ref(value):
            source = _repair_identity_source(_map_reference(value), value, authn_id,
                                             authn_precedes and authn_spreads)
            rules[f"args.{prefix}"] = {"from": source, "required": False, "default": None}
            return
        # Static literal input value rides the same guaranteed-missing channel.
        rules[f"args.{prefix}"] = {"from": f"{MF_PARAMS_ROOT}.args.{prefix}",
                                   "required": False, "default": value}

    for key, value in raw_inputs.items():
        walk(str(key), value)
    return rules


def _topo_positions(node_ids: list[str], edges: list[list[Any]]) -> dict[str, int]:
    """Kahn ordering over the declared edges; ties keep declaration order."""
    outgoing: dict[str, list[str]] = {nid: [] for nid in node_ids}
    indegree = {nid: 0 for nid in node_ids}
    for edge in edges or []:
        source, target = str(edge[0]), str(edge[1])
        if source in outgoing and target in indegree:
            outgoing[source].append(target)
            indegree[target] += 1
    ready = [nid for nid in node_ids if indegree[nid] == 0]
    position: dict[str, int] = {}
    index = 0
    while ready:
        current = ready.pop(0)
        position[current] = index
        index += 1
        for target in outgoing[current]:
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
    for nid in node_ids:  # original cycles (none expected): keep declaration order
        position.setdefault(nid, index)
        index += 1
    return position


def _repair_identity_source(source: str, original: str, authn_id: str | None,
                            authn_precedes: bool) -> str:
    """``$inputs.user_id`` reads the authn node output when one exists upstream.

    The old engine merged every node output back into the request scope
    (``inputs.update(out)``), so identity fields written by ``guard.authn``
    shadowed payload values — but only for nodes executed after it. Rewiring a
    node that runs BEFORE the authn guard would fabricate a dependency cycle
    and change semantics (it reads the raw payload there).
    """
    if authn_id and authn_precedes and source.startswith("flow.input.payload."):
        leaf = source.rsplit(".", 1)[-1]
        if leaf in AUTHN_OUTPUT_KEYS:
            return _node_source(authn_id, leaf)
    return source


def convert_params(raw_params: Any, inputs: dict[str, Any], unmapped: list[str],
                   synth: list[dict[str, Any]], owner: str) -> None:
    if not raw_params:
        return
    counter: dict[str, int] = {}
    try:
        _emit_params("params", raw_params, inputs, counter, synth, owner)
    except Unmappable as exc:
        unmapped.append(f"params: {exc}")


def build_synthetic_nodes(synth: list[dict[str, Any]], mf_nodes: dict[str, Any],
                          unmapped: list[str]) -> None:
    """Materialize ``assemble.list`` nodes for list-shaped $-reference params."""
    for spec in synth:
        owner, param_path = spec["owner"], spec["param"]
        if owner not in mf_nodes:
            continue
        synth_id = f"{owner}__aslist_{param_path.replace('.', '_')}"
        if synth_id in mf_nodes:
            unmapped.append(f"duplicate synthetic node {synth_id}")
            continue
        element_inputs: dict[str, Any] = {}

        def emit_element(index: int, value: Any, prefix: str) -> None:
            target = f"args.{prefix}"
            if _is_ref(value):
                element_inputs[target] = {"from": _map_reference(value), "required": False, "default": None}
            elif isinstance(value, dict):
                for key, item in value.items():
                    emit_element(index, item, f"{prefix}.{key}")
            elif _has_ref(value):
                unmapped.append(f"{synth_id}: unsupported nested reference in element {index}")
                element_inputs[target] = {"from": f"{MF_PARAMS_ROOT}.{synth_id}.{prefix}",
                                          "required": False, "default": None}
            else:
                element_inputs[target] = {"from": f"{MF_PARAMS_ROOT}.{synth_id}.{prefix}",
                                          "required": False, "default": value}

        for index, element in enumerate(spec["elements"]):
            emit_element(index, element, f"e{index}")
        deps = []
        for rule in element_inputs.values():
            source = rule["from"]
            if source.startswith("nodes."):
                deps.append(source.split(".")[1])
        mf_nodes[synth_id] = {
            "operator": "assemble.list@1",
            "inputs": element_inputs,
            "depends_on": sorted(set(deps)),
        }
        owner_inputs = mf_nodes[owner].setdefault("inputs", {})
        owner_inputs[param_path] = {
            "from": f"nodes.{synth_id}.output.data.mf_items", "required": False}
        parents = mf_nodes[owner].get("depends_on", [])
        mf_nodes[owner]["depends_on"] = sorted(set(parents) | {synth_id})


# ---------------------------------------------------------------------------
# scenario -> flow
# ---------------------------------------------------------------------------
def convert_scenario(asset: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    code = str(asset["scenario"])
    unmapped: list[str] = []
    raw_nodes = asset.get("nodes") or []
    authn_id = next((str(n["id"]) for n in raw_nodes if str(n.get("operator")) == "guard.authn"), None)
    # The authn output only shadows payload keys while it spreads into the
    # request scope; a node-level output_key redirects it and stops the spread.
    authn_spreads = bool(authn_id) and not next(
        (n.get("output_key") for n in raw_nodes if str(n.get("id")) == authn_id), None)
    positions = _topo_positions([str(n.get("id")) for n in raw_nodes], asset.get("edges") or [])

    mf_nodes: dict[str, Any] = {}
    order: list[str] = []
    synth: list[dict[str, Any]] = []
    for raw in raw_nodes:
        node_id = str(raw["id"])
        order.append(node_id)
        operator = str(raw.get("operator") or raw.get("action_handler"))
        node: dict[str, Any] = {"operator": f"{operator}@1"}
        inputs: dict[str, Any] = {}
        convert_params(raw.get("params"), inputs, unmapped, synth, node_id)
        authn_precedes = bool(
            authn_id and node_id != authn_id
            and positions.get(authn_id, 0) < positions.get(node_id, 0)
        )
        inputs.update(convert_inputs_map(raw.get("inputs_map") or raw.get("inputs"),
                                         authn_id, code, unmapped, synth, node_id,
                                         authn_precedes, authn_spreads))
        if inputs:
            node["inputs"] = inputs
        else:
            # Nodes without an inputs_map ran against the legacy merged scope
            # (payload spread + params). Reserve a bridge-only channel carrying
            # the payload; ordinary operators never read it.
            node["inputs"] = {"__payload__": {"from": "flow.input.payload",
                                              "required": False, "default": {}}}
        if raw.get("when"):
            try:
                node["condition"] = translate_condition(raw["when"])
            except Unmappable as exc:
                unmapped.append(f"when on '{node_id}': {exc}")
        mf_nodes[node_id] = node

    build_synthetic_nodes(synth, mf_nodes, unmapped)

    edges = asset.get("edges") or []
    incoming: dict[str, list[str]] = {}
    for edge in edges:
        source, target = edge[0], edge[1]
        if len(edge) > 2 and edge[2]:
            unmapped.append(f"conditional edge {source}->{target}")
        incoming.setdefault(str(target), []).append(str(source))
    for node_id, parents in incoming.items():
        known = [p for p in parents if p in mf_nodes]
        if known:
            existing = mf_nodes[node_id].get("depends_on", [])
            mf_nodes[node_id]["depends_on"] = sorted(set(existing) | set(known))

    flow = {
        "id": code,
        "input_schema": "opchub.flow_input",
        "output_schema": "opchub.flow_output",
        "options": {"scene": str(asset.get("domain") or "") or "opchub", "version": str(asset.get("version") or "v1.0.0")},
        "nodes": mf_nodes,
        "outputs": {},
    }
    report = {
        "scenario": code,
        "version": flow["options"]["version"],
        "nodes": len(mf_nodes),
        "conditions": sum(1 for n in mf_nodes.values() if "condition" in n),
        "unmapped": unmapped,
    }
    return flow, report


def main() -> int:
    flows: list[dict[str, Any]] = []
    reports: list[dict[str, Any]] = []
    for asset_file in sorted(SCENARIO_DIR.glob("*.yaml")):
        payload = yaml.safe_load(asset_file.read_text(encoding="utf-8")) or {}
        assets = payload.get("scenarios") if isinstance(payload, dict) and "scenarios" in payload else [payload]
        for asset in assets:
            if not isinstance(asset, dict) or not asset.get("scenario"):
                continue
            flow, report = convert_scenario(asset)
            report["source"] = asset_file.name
            flows.append(flow)
            reports.append(report)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    project = {
        "protocol": "opchub-flows-v1",
        "note": f"Generated by tools/convert_scenarios.py; {PERMISSIVE_NOTE}",
        "schemas": {
            "opchub.flow_input": FLOW_INPUT_SCHEMA,
            "opchub.flow_output": FLOW_INPUT_SCHEMA,
        },
        "flows": flows,
    }
    (OUTPUT_DIR / "opchub_flows.json").write_text(
        json.dumps(project, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUTPUT_DIR / "conversion_report.json").write_text(
        json.dumps(reports, ensure_ascii=False, indent=1), encoding="utf-8")

    blocked = [r for r in reports if r["unmapped"]]
    total_unmapped = sum(len(r["unmapped"]) for r in reports)
    print(f"flows: {len(flows)} | scenarios with unmapped constructs: {len(blocked)} | total unmapped: {total_unmapped}")
    for report in blocked[:10]:
        print(f"- {report['scenario']} ({report['source']}): {report['unmapped'][:3]}")
    return 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
