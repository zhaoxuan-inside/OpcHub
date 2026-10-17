"""Microkernel DAG Execution Engine with Dual-Mode Dispatcher Integration."""
import asyncio
import time
import uuid
from typing import Any, Optional
from .models import (
    DAGConfig, ExecutionResult, ExecutionStatus, NodeExecutionTrace, NodeType, CompensationTrace
)
from .registry import registry
from .dispatcher import dispatcher, DispatchMode, DualModeDispatcher
from src.core.telemetry import get_current_trace_id


class MicrokernelEngine:
    """Executes validated DAG topologies asynchronously via DualModeDispatcher."""

    def __init__(self, atomic_registry=None, dispatcher_inst: Optional[DualModeDispatcher] = None):
        self.registry = atomic_registry or registry
        self.dispatcher = dispatcher_inst or dispatcher

    def topological_sort(self, config: DAGConfig) -> list[str]:
        """Kahn's algorithm to sort nodes and detect cycles."""
        nodes = {n.id: n for n in config.execution_graph.nodes}
        in_degree = {nid: 0 for nid in nodes}
        adj: dict[str, list[str]] = {nid: [] for nid in nodes}

        for edge in config.execution_graph.edges:
            from_n = edge.from_node
            to_n = edge.to_node
            if from_n in adj and to_n in in_degree:
                adj[from_n].append(to_n)
                in_degree[to_n] += 1

        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        sorted_nodes = []

        while queue:
            curr = queue.pop(0)
            sorted_nodes.append(curr)
            for neighbor in adj[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(sorted_nodes) != len(nodes):
            raise ValueError("Cyclic dependency detected in execution graph!")

        return sorted_nodes

    async def execute_dag(
        self,
        config: DAGConfig,
        initial_inputs: dict[str, Any] | None = None,
        trace_id: str | None = None,
        override_dispatch_mode: Optional[DispatchMode] = None,
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
        }

        try:
            order = self.topological_sort(config)
        except ValueError as e:
            total_dur = (time.perf_counter() - start_time) * 1000
            return ExecutionResult(
                pipeline_id=pipeline_id,
                trace_id=tid,
                version=config.version,
                scenario_code=config.scenario_code,
                status=ExecutionStatus.CYCLE_DETECTED,
                total_duration_ms=round(total_dur, 2),
                entry_node=config.execution_graph.entry_node,
                node_traces=[],
                final_output={},
                error_message=str(e),
            )

        final_output: dict[str, Any] = {}
        executed_nodes: list[tuple[str, str]] = []

        for nid in order:
            node_def = node_map[nid]
            t_start = time.perf_counter()
            handler = self.registry.get(node_def.action_handler)
            mode, endpoint = self.dispatcher.get_operator_mode(node_def.action_handler)
            effective_mode = override_dispatch_mode or mode

            if effective_mode == DispatchMode.IN_PROCESS and not handler:
                dur = (time.perf_counter() - t_start) * 1000
                err_msg = f"Handler '{node_def.action_handler}' not registered in method pool"
                traces.append(NodeExecutionTrace(
                    node_id=nid,
                    action_handler=node_def.action_handler,
                    type=node_def.type,
                    status=ExecutionStatus.FAILED,
                    duration_ms=round(dur, 2),
                    trace_id=tid,
                    error=err_msg,
                ))
                comp_traces, comp_ok = await self._rollback_saga(
                    config=config,
                    executed_nodes=executed_nodes,
                    inputs=inputs,
                    context=context,
                    trace_id=tid,
                )
                final_status = (
                    ExecutionStatus.ROLLED_BACK if (comp_traces and comp_ok)
                    else (ExecutionStatus.COMPENSATION_FAILED if (comp_traces and not comp_ok) else ExecutionStatus.FAILED)
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
                    node_traces=traces,
                    final_output=final_output,
                    error_message=err_msg,
                    compensation_traces=comp_traces,
                )

            try:
                # Dispatch handler with timeout via DualModeDispatcher
                timeout_sec = node_def.timeout_ms / 1000.0
                out = await asyncio.wait_for(
                    self.dispatcher.dispatch(
                        name=node_def.action_handler,
                        handler=handler,
                        inputs=inputs,
                        context=context,
                        timeout_sec=timeout_sec,
                    ),
                    timeout=timeout_sec,
                )
                dur = (time.perf_counter() - t_start) * 1000
                traces.append(NodeExecutionTrace(
                    node_id=nid,
                    action_handler=node_def.action_handler,
                    type=node_def.type,
                    status=ExecutionStatus.SUCCESS,
                    duration_ms=round(dur, 2),
                    trace_id=tid,
                    output=out,
                ))
                executed_nodes.append((nid, node_def.action_handler))
                if isinstance(out, dict):
                    inputs.update(out)
                    final_output.update(out)

            except PermissionError as e:
                dur = (time.perf_counter() - t_start) * 1000
                traces.append(NodeExecutionTrace(
                    node_id=nid,
                    action_handler=node_def.action_handler,
                    type=node_def.type,
                    status=ExecutionStatus.GUARD_REJECTED,
                    duration_ms=round(dur, 2),
                    trace_id=tid,
                    error=str(e),
                ))
                comp_traces, comp_ok = await self._rollback_saga(
                    config=config,
                    executed_nodes=executed_nodes,
                    inputs=inputs,
                    context=context,
                    trace_id=tid,
                )
                final_status = (
                    ExecutionStatus.ROLLED_BACK if (comp_traces and comp_ok)
                    else (ExecutionStatus.COMPENSATION_FAILED if (comp_traces and not comp_ok) else ExecutionStatus.GUARD_REJECTED)
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
                    node_traces=traces,
                    final_output=final_output,
                    error_message=f"Guard check failed: {e}",
                    compensation_traces=comp_traces,
                )
            except Exception as e:
                dur = (time.perf_counter() - t_start) * 1000
                traces.append(NodeExecutionTrace(
                    node_id=nid,
                    action_handler=node_def.action_handler,
                    type=node_def.type,
                    status=ExecutionStatus.FAILED,
                    duration_ms=round(dur, 2),
                    trace_id=tid,
                    error=str(e),
                ))
                comp_traces, comp_ok = await self._rollback_saga(
                    config=config,
                    executed_nodes=executed_nodes,
                    inputs=inputs,
                    context=context,
                    trace_id=tid,
                )
                final_status = (
                    ExecutionStatus.ROLLED_BACK if (comp_traces and comp_ok)
                    else (ExecutionStatus.COMPENSATION_FAILED if (comp_traces and not comp_ok) else ExecutionStatus.FAILED)
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
                    node_traces=traces,
                    final_output=final_output,
                    error_message=f"Node {nid} execution error: {e}",
                    compensation_traces=comp_traces,
                )

        total_dur = (time.perf_counter() - start_time) * 1000
        return ExecutionResult(
            pipeline_id=pipeline_id,
            trace_id=tid,
            version=config.version,
            scenario_code=config.scenario_code,
            status=ExecutionStatus.SUCCESS,
            total_duration_ms=round(total_dur, 2),
            entry_node=config.execution_graph.entry_node,
            node_traces=traces,
            final_output=final_output,
            compensation_traces=[],
        )

    async def _rollback_saga(
        self,
        config: DAGConfig,
        executed_nodes: list[tuple[str, str]],
        inputs: dict[str, Any],
        context: dict[str, Any],
        trace_id: str,
    ) -> tuple[list[CompensationTrace], bool]:
        """Sequentially execute registered compensators in reverse order for all completed nodes."""
        if not config.enable_saga_compensation or not executed_nodes:
            return [], True

        traces: list[CompensationTrace] = []
        all_ok = True

        for nid, handler_name in reversed(executed_nodes):
            t_start = time.perf_counter()
            compensator = self.registry.get_compensator(handler_name)
            if not compensator:
                # Node has no registered compensator (pure read / idempotent)
                continue

            try:
                comp_out = compensator(inputs, context)
                if asyncio.iscoroutine(comp_out):
                    comp_out = await comp_out
                dur = (time.perf_counter() - t_start) * 1000
                traces.append(CompensationTrace(
                    node_id=nid,
                    action_handler=f"{handler_name}_compensate",
                    status="SUCCESS",
                    duration_ms=round(dur, 2),
                    trace_id=trace_id,
                    output=comp_out if isinstance(comp_out, dict) else {"result": str(comp_out)},
                ))
            except Exception as e:
                all_ok = False
                dur = (time.perf_counter() - t_start) * 1000
                traces.append(CompensationTrace(
                    node_id=nid,
                    action_handler=f"{handler_name}_compensate",
                    status="FAILED",
                    duration_ms=round(dur, 2),
                    trace_id=trace_id,
                    error=str(e),
                ))

        return traces, all_ok


microkernel_engine = MicrokernelEngine()
