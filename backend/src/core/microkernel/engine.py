"""Microkernel DAG Execution Engine with declarative operator invocation.

Execution semantics
-------------------
* The topology is validated as a DAG with exactly one entry and one exit node.
* Nodes are grouped into topological *levels*; nodes inside a level execute
  concurrently, levels execute in order.
* Every node resolves its declarative ``inputs_map`` against the pipeline scope
  (``$inputs``, ``$context``, ``$nodes.<id>``, ``$params``) and receives the
  result under ``inputs["args"]``. ``inputs["params"]`` carries its static
  configuration. This keeps operators free of business knowledge.
* ``when`` expressions can skip a node; downstream nodes skip automatically
  when all of their predecessors were skipped.
* A failing node aborts the pipeline and triggers reverse-order Saga
  compensation for every node that completed successfully.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Optional

from .dispatcher import DispatchMode, DualModeDispatcher, dispatcher
from .expr import ExpressionError, evaluate
from .models import (
    CompensationTrace,
    DAGConfig,
    ExecutionResult,
    ExecutionStatus,
    NodeDef,
    NodeExecutionTrace,
)
from .registry import registry
from src.core.telemetry import get_current_trace_id


class MicrokernelEngine:
    """Executes validated DAG topologies asynchronously via DualModeDispatcher."""

    def __init__(self, atomic_registry=None, dispatcher_inst: Optional[DualModeDispatcher] = None):
        self.registry = atomic_registry or registry
        self.dispatcher = dispatcher_inst or dispatcher

    # ------------------------------------------------------------------
    # Topology validation
    # ------------------------------------------------------------------
    def validate_and_sort(self, config: DAGConfig) -> tuple[list[str], str, str]:
        """Kahn's algorithm to sort nodes, detect cycles, and strictly validate single-entry & single-exit."""
        nodes = {n.id: n for n in config.execution_graph.nodes}
        if not nodes:
            raise ValueError("Execution graph cannot be empty!")

        in_degree = {nid: 0 for nid in nodes}
        out_degree = {nid: 0 for nid in nodes}
        adj: dict[str, list[str]] = {nid: [] for nid in nodes}

        for edge in config.execution_graph.edges:
            from_n = edge.from_node
            to_n = edge.to_node
            if from_n in adj and to_n in in_degree:
                adj[from_n].append(to_n)
                in_degree[to_n] += 1
                out_degree[from_n] += 1

        source_nodes = [nid for nid, deg in in_degree.items() if deg == 0]
        if len(source_nodes) == 0:
            raise ValueError("Cyclic dependency detected in execution graph: no entry node found!")
        if len(source_nodes) > 1:
            raise ValueError(f"Graph must have exactly ONE entry point, found {len(source_nodes)}: {source_nodes}")

        entry_node = source_nodes[0]
        if config.execution_graph.entry_node and config.execution_graph.entry_node != entry_node:
            raise ValueError(
                f"Declared entry_node '{config.execution_graph.entry_node}' does not match topological source '{entry_node}'"
            )

        sink_nodes = [nid for nid, deg in out_degree.items() if deg == 0]
        if len(sink_nodes) == 0:
            raise ValueError("No exit node found: graph contains cycles or has no sink!")
        if len(sink_nodes) > 1:
            raise ValueError(f"Graph must have exactly ONE exit point, found {len(sink_nodes)}: {sink_nodes}")

        exit_node = sink_nodes[0]
        if config.execution_graph.exit_node and config.execution_graph.exit_node != exit_node:
            raise ValueError(
                f"Declared exit_node '{config.execution_graph.exit_node}' does not match topological sink '{exit_node}'"
            )

        config.execution_graph.entry_node = entry_node
        config.execution_graph.exit_node = exit_node

        queue = [entry_node]
        sorted_nodes: list[str] = []
        remaining = dict(in_degree)
        while queue:
            curr = queue.pop(0)
            sorted_nodes.append(curr)
            for neighbor in adj[curr]:
                remaining[neighbor] -= 1
                if remaining[neighbor] == 0:
                    queue.append(neighbor)

        if len(sorted_nodes) != len(nodes):
            raise ValueError("Cyclic dependency or disconnected unreachable nodes detected in execution graph!")

        return sorted_nodes, entry_node, exit_node

    def topological_sort(self, config: DAGConfig) -> list[str]:
        sorted_nodes, _, _ = self.validate_and_sort(config)
        return sorted_nodes

    def _levels(self, config: DAGConfig) -> list[list[str]]:
        """Group nodes by topological level so independent nodes run concurrently."""
        nodes = {n.id: n for n in config.execution_graph.nodes}
        in_degree = {nid: 0 for nid in nodes}
        adj: dict[str, list[str]] = {nid: [] for nid in nodes}
        for edge in config.execution_graph.edges:
            if edge.from_node in adj and edge.to_node in in_degree:
                adj[edge.from_node].append(edge.to_node)
                in_degree[edge.to_node] += 1

        levels: list[list[str]] = []
        current = [nid for nid, degree in in_degree.items() if degree == 0]
        while current:
            levels.append(sorted(current))
            nxt: list[str] = []
            for nid in current:
                for neighbor in adj[nid]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        nxt.append(neighbor)
            current = nxt
        return levels

    def _predecessors(self, config: DAGConfig) -> dict[str, list[str]]:
        preds: dict[str, list[str]] = {n.id: [] for n in config.execution_graph.nodes}
        for edge in config.execution_graph.edges:
            if edge.to_node in preds:
                preds[edge.to_node].append(edge.from_node)
        return preds

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    async def execute_dag(
        self,
        config: DAGConfig,
        initial_inputs: dict[str, Any] | None = None,
        trace_id: str | None = None,
        override_dispatch_mode: Optional[DispatchMode] = None,
        initial_context: Optional[dict[str, Any]] = None,
    ) -> ExecutionResult:
        start_time = time.perf_counter()
        tid = trace_id or get_current_trace_id()
        pipeline_id = f"pipe_{uuid.uuid4().hex[:12]}"
        inputs = dict(initial_inputs or {})
        traces: list[NodeExecutionTrace] = []
        node_map = {n.id: n for n in config.execution_graph.nodes}
        context: dict[str, Any] = {
            "pipeline_id": pipeline_id,
            "version": config.version,
            "trace_id": tid,
            "inputs": inputs,
        }
        if initial_context:
            context.update(initial_context)
        context["nodes"] = {}
        node_outputs: dict[str, dict[str, Any]] = context["nodes"]
        skipped: dict[str, bool] = {}

        try:
            _order, _entry, exit_node = self.validate_and_sort(config)
        except ValueError as exc:
            total_dur = (time.perf_counter() - start_time) * 1000
            return ExecutionResult(
                pipeline_id=pipeline_id,
                trace_id=tid,
                version=config.version,
                scenario_code=config.scenario_code,
                status=ExecutionStatus.CYCLE_DETECTED,
                total_duration_ms=round(total_dur, 2),
                entry_node=config.execution_graph.entry_node,
                exit_node=config.execution_graph.exit_node,
                node_traces=[],
                final_output={},
                error_message=str(exc),
            )

        final_output: dict[str, Any] = {}
        executed_nodes: list[tuple[str, str, dict[str, Any], dict[str, Any]]] = []
        predecessors = self._predecessors(config)
        levels = self._levels(config)

        for level in levels:
            prepared: list[tuple[NodeDef, dict[str, Any], Any]] = []
            for nid in level:
                node_def = node_map[nid]
                preds = predecessors.get(nid) or []
                if preds and all(skipped.get(p) for p in preds):
                    skipped[nid] = True
                    traces.append(
                        NodeExecutionTrace(
                            node_id=nid,
                            action_handler=node_def.action_handler,
                            type=node_def.type,
                            status=ExecutionStatus.SKIPPED,
                            duration_ms=0.0,
                            trace_id=tid,
                            output={"skipped": True, "reason": "all predecessors skipped"},
                        )
                    )
                    node_outputs[nid] = {}
                    continue

                scope = {
                    "inputs": inputs,
                    "context": context,
                    "nodes": node_outputs,
                    "params": node_def.params,
                }
                try:
                    if node_def.when and not self._truthy(node_def.when, scope):
                        skipped[nid] = True
                        traces.append(
                            NodeExecutionTrace(
                                node_id=nid,
                                action_handler=node_def.action_handler,
                                type=node_def.type,
                                status=ExecutionStatus.SKIPPED,
                                duration_ms=0.0,
                                trace_id=tid,
                                output={"skipped": True, "reason": f"when: {node_def.when}"},
                            )
                        )
                        node_outputs[nid] = {}
                        continue
                    node_params = self._resolve(node_def.params, scope)
                    args = {key: self._resolve(value, scope) for key, value in node_def.inputs_map.items()}
                except ExpressionError as exc:
                    return self._fail(
                        config, pipeline_id, tid, start_time, traces, final_output,
                        executed_nodes, inputs, context, None,
                        str(exc), ExecutionStatus.FAILED, node_def,
                    )

                node_inputs = dict(inputs)
                node_inputs.update(args)
                node_inputs["params"] = node_params
                if node_def.inputs_map:
                    node_inputs["args"] = args
                node_inputs["_node"] = nid
                prepared.append((node_def, node_inputs, time.perf_counter()))

            if not prepared:
                continue

            results = await asyncio.gather(
                *[
                    self._run_node(node_def, node_inputs, context, override_dispatch_mode)
                    for node_def, node_inputs, _ in prepared
                ],
                return_exceptions=True,
            )

            for (node_def, node_inputs, node_started), result in zip(prepared, results):
                nid = node_def.id
                node_duration = round((time.perf_counter() - node_started) * 1000, 2)
                if isinstance(result, BaseException):
                    traces.append(
                        NodeExecutionTrace(
                            node_id=nid,
                            action_handler=node_def.action_handler,
                            type=node_def.type,
                            status=ExecutionStatus.GUARD_REJECTED
                            if isinstance(result, PermissionError)
                            else ExecutionStatus.FAILED,
                            duration_ms=node_duration,
                            trace_id=tid,
                            error=str(result),
                        )
                    )
                    status = (
                        ExecutionStatus.GUARD_REJECTED
                        if isinstance(result, PermissionError)
                        else ExecutionStatus.FAILED
                    )
                    prefix = "Guard check failed: " if status == ExecutionStatus.GUARD_REJECTED else f"Node {nid} execution error: "
                    return await self._fail(
                        config, pipeline_id, tid, start_time, traces, final_output,
                        executed_nodes, inputs, context, node_inputs,
                        f"{prefix}{result}", status, node_def,
                    )

                out = result if isinstance(result, dict) else {"result": result}
                node_outputs[nid] = out
                executed_nodes.append((nid, node_def.action_handler, node_inputs, out))
                traces.append(
                    NodeExecutionTrace(
                        node_id=nid,
                        action_handler=node_def.action_handler,
                        type=node_def.type,
                        status=ExecutionStatus.SUCCESS,
                        duration_ms=node_duration,
                        trace_id=tid,
                        output=out,
                    )
                )
                if node_def.output_key:
                    inputs[node_def.output_key] = out
                else:
                    inputs.update(out)
                final_output.update(out)

        total_dur = (time.perf_counter() - start_time) * 1000
        return ExecutionResult(
            pipeline_id=pipeline_id,
            trace_id=tid,
            version=config.version,
            scenario_code=config.scenario_code,
            status=ExecutionStatus.SUCCESS,
            total_duration_ms=round(total_dur, 2),
            entry_node=config.execution_graph.entry_node,
            exit_node=exit_node,
            node_traces=traces,
            final_output=final_output,
            compensation_traces=[],
        )

    async def _run_node(
        self,
        node_def: NodeDef,
        node_inputs: dict[str, Any],
        context: dict[str, Any],
        override_dispatch_mode: Optional[DispatchMode],
    ) -> dict[str, Any]:
        handler = self.registry.get(node_def.action_handler)
        mode, endpoint = self.dispatcher.get_operator_mode(node_def.action_handler)
        effective_mode = override_dispatch_mode or mode

        if effective_mode == DispatchMode.IN_PROCESS and not handler:
            raise KeyError(f"Handler '{node_def.action_handler}' not registered in method pool")

        timeout_sec = node_def.timeout_ms / 1000.0
        last_exc: Optional[BaseException] = None
        for attempt in range(node_def.retry + 1):
            try:
                out = await asyncio.wait_for(
                    self.dispatcher.dispatch(
                        name=node_def.action_handler,
                        handler=handler,
                        inputs=node_inputs,
                        context=context,
                        timeout_sec=timeout_sec,
                    ),
                    timeout=timeout_sec,
                )
                if not isinstance(out, dict):
                    out = {"result": out}
                return out
            except (PermissionError, ValueError, KeyError):
                raise
            except BaseException as exc:  # noqa: BLE001 - retried then surfaced
                last_exc = exc
                if attempt >= node_def.retry:
                    raise
                await asyncio.sleep(0)
        raise last_exc or RuntimeError("operator execution failed")

    async def _fail(
        self,
        config: DAGConfig,
        pipeline_id: str,
        tid: str,
        start_time: float,
        traces: list[NodeExecutionTrace],
        final_output: dict[str, Any],
        executed_nodes: list[tuple[str, str, dict[str, Any], dict[str, Any]]],
        inputs: dict[str, Any],
        context: dict[str, Any],
        node_inputs: Optional[dict[str, Any]],
        error_message: str,
        status: ExecutionStatus,
        node_def: Optional[NodeDef],
    ) -> ExecutionResult:
        comp_traces, comp_ok = await self._rollback_saga(
            config=config,
            executed_nodes=executed_nodes,
            inputs=inputs,
            context=context,
            trace_id=tid,
        )
        final_status = (
            ExecutionStatus.ROLLED_BACK
            if (comp_traces and comp_ok)
            else (ExecutionStatus.COMPENSATION_FAILED if (comp_traces and not comp_ok) else status)
        )
        total_dur = (time.perf_counter() - start_time) * 1000
        return ExecutionResult(
            pipeline_id=pipeline_id,
            trace_id=tid,
            version=config.version,
            scenario_code=config.scenario_code,
            status=final_status,
            total_duration_ms=round(total_dur, 2),
            entry_node=config.execution_graph.entry_node,
            exit_node=config.execution_graph.exit_node,
            node_traces=traces,
            final_output=final_output,
            error_message=error_message,
            compensation_traces=comp_traces,
        )

    async def _rollback_saga(
        self,
        config: DAGConfig,
        executed_nodes: list[tuple[str, str, dict[str, Any], dict[str, Any]]],
        inputs: dict[str, Any],
        context: dict[str, Any],
        trace_id: str,
    ) -> tuple[list[CompensationTrace], bool]:
        """Sequentially execute registered compensators in reverse order."""
        if not config.enable_saga_compensation or not executed_nodes:
            return [], True

        traces: list[CompensationTrace] = []
        all_ok = True

        for nid, handler_name, node_inputs, node_output in reversed(executed_nodes):
            start = time.perf_counter()
            compensator = self.registry.get_compensator(handler_name)
            if not compensator:
                continue
            comp_inputs = dict(node_inputs)
            comp_inputs["output"] = node_output
            try:
                out = compensator(comp_inputs, context)
                if asyncio.iscoroutine(out):
                    out = await out
                dur = (time.perf_counter() - start) * 1000
                traces.append(
                    CompensationTrace(
                        node_id=nid,
                        action_handler=f"{handler_name}_compensate",
                        status="SUCCESS",
                        duration_ms=round(dur, 2),
                        trace_id=trace_id,
                        output=out if isinstance(out, dict) else {"result": str(out)},
                    )
                )
            except Exception as exc:  # noqa: BLE001 - compensation failures are reported
                all_ok = False
                dur = (time.perf_counter() - start) * 1000
                traces.append(
                    CompensationTrace(
                        node_id=nid,
                        action_handler=f"{handler_name}_compensate",
                        status="FAILED",
                        duration_ms=round(dur, 2),
                        trace_id=trace_id,
                        error=str(exc),
                    )
                )
        return traces, all_ok

    # ------------------------------------------------------------------
    # Declarative value resolution
    # ------------------------------------------------------------------
    def _resolve(self, value: Any, scope: dict[str, Any]) -> Any:
        if isinstance(value, str) and value.startswith("$"):
            path = value[1:]
            current: Any = scope
            for part in path.split("."):
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    return None
            return current
        if isinstance(value, dict):
            return {k: self._resolve(v, scope) for k, v in value.items()}
        if isinstance(value, list):
            return [self._resolve(v, scope) for v in value]
        return value

    def _truthy(self, expression: str, scope: dict[str, Any]) -> bool:
        normalized = expression.replace("$", "")
        return bool(evaluate(normalized, scope))


microkernel_engine = MicrokernelEngine()
