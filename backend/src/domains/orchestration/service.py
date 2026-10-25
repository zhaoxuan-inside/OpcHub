"""Service for saving and loading versioned DAG configs, frontend visual layouts, and executing composable scenarios."""
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
            "exit_node": "dnode-4",
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
            "exit_node": "step_compliance",
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
            "exit_node": "step_audit",
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
            "exit_node": "step_agg",
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
            "entry_node": "step_identity",
            "exit_node": "step_telemetry",
            "enable_saga_compensation": True,
            "nodes": [
                {"id": "step_identity", "action_handler": "content.publish.identity_guard", "type": "GUARD"},
                {"id": "step_guard", "action_handler": "forum.thread.validate_guard", "type": "GUARD"},
                {"id": "step_persist", "action_handler": "forum.thread.persist", "type": "STORAGE"},
                {"id": "step_invalidate_cache", "action_handler": "forum.cache.invalidate_operator", "type": "CACHE"},
                {"id": "step_telemetry", "action_handler": "forum.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_identity", "to": "step_guard"},
                {"from": "step_guard", "to": "step_persist"},
                {"from": "step_persist", "to": "step_invalidate_cache"},
                {"from": "step_invalidate_cache", "to": "step_telemetry"},
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
            "entry_node": "step_identity",
            "exit_node": "step_telemetry",
            "enable_saga_compensation": True,
            "nodes": [
                {"id": "step_identity", "action_handler": "content.publish.identity_guard", "type": "GUARD"},
                {"id": "step_guard", "action_handler": "forum.comment.validate_guard", "type": "GUARD"},
                {"id": "step_persist", "action_handler": "forum.comment.persist", "type": "STORAGE"},
                {"id": "step_telemetry", "action_handler": "forum.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_identity", "to": "step_guard"},
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

        # 6.1 Zhihu-style Answer Publish DAG Pipeline: OPC_FORUM_ANSWER_PUBLISH
        topo_forum_answer = {
            "topology": "DAG",
            "entry_node": "step_identity",
            "exit_node": "step_telemetry",
            "enable_saga_compensation": True,
            "nodes": [
                {"id": "step_identity", "action_handler": "content.publish.identity_guard", "type": "GUARD"},
                {"id": "step_guard", "action_handler": "forum.answer.validate_guard", "type": "GUARD"},
                {"id": "step_persist", "action_handler": "forum.answer.persist", "type": "STORAGE"},
                {"id": "step_hot_recalc", "action_handler": "forum.hot_score.recalculate", "type": "BIZ"},
                {"id": "step_invalidate_cache", "action_handler": "forum.cache.invalidate_operator", "type": "CACHE"},
                {"id": "step_telemetry", "action_handler": "forum.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_identity", "to": "step_guard"},
                {"from": "step_guard", "to": "step_persist"},
                {"from": "step_persist", "to": "step_hot_recalc"},
                {"from": "step_hot_recalc", "to": "step_invalidate_cache"},
                {"from": "step_invalidate_cache", "to": "step_telemetry"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_FORUM_ANSWER_PUBLISH",
                version="v1.0.0",
                topology_graph=topo_forum_answer,
                status="ACTIVE",
            )
        )

        # 6.2 Zhihu-style Answer Accept Pipeline: OPC_FORUM_ANSWER_ACCEPT_PIPELINE
        topo_forum_accept = {
            "topology": "DAG",
            "entry_node": "step_guard",
            "exit_node": "step_telemetry",
            "enable_saga_compensation": True,
            "nodes": [
                {"id": "step_guard", "action_handler": "forum.answer.accept_guard", "type": "GUARD"},
                {"id": "step_accept", "action_handler": "forum.answer.accept_persist", "type": "STORAGE"},
                {"id": "step_invalidate_cache", "action_handler": "forum.cache.invalidate_operator", "type": "CACHE"},
                {"id": "step_telemetry", "action_handler": "forum.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_guard", "to": "step_accept"},
                {"from": "step_accept", "to": "step_invalidate_cache"},
                {"from": "step_invalidate_cache", "to": "step_telemetry"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_FORUM_ANSWER_ACCEPT_PIPELINE",
                version="v1.0.0",
                topology_graph=topo_forum_accept,
                status="ACTIVE",
            )
        )

        # 6.3 Zhihu-style Mutual Vote Pipeline: OPC_FORUM_VOTE_PIPELINE
        topo_forum_vote = {
            "topology": "DAG",
            "entry_node": "step_guard",
            "exit_node": "step_telemetry",
            "enable_saga_compensation": False,
            "nodes": [
                {"id": "step_guard", "action_handler": "forum.vote.validate_guard", "type": "GUARD"},
                {"id": "step_vote", "action_handler": "forum.vote.persist", "type": "STORAGE"},
                {"id": "step_hot_recalc", "action_handler": "forum.hot_score.recalculate", "type": "BIZ"},
                {"id": "step_invalidate_cache", "action_handler": "forum.cache.invalidate_operator", "type": "CACHE"},
                {"id": "step_telemetry", "action_handler": "forum.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_guard", "to": "step_vote"},
                {"from": "step_vote", "to": "step_hot_recalc"},
                {"from": "step_hot_recalc", "to": "step_invalidate_cache"},
                {"from": "step_invalidate_cache", "to": "step_telemetry"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_FORUM_VOTE_PIPELINE",
                version="v1.0.0",
                topology_graph=topo_forum_vote,
                status="ACTIVE",
            )
        )

        # 6.4 Forum Thread Edit Pipeline: OPC_FORUM_THREAD_UPDATE_PIPELINE
        topo_forum_thread_update = {
            "topology": "DAG",
            "entry_node": "step_guard",
            "exit_node": "step_telemetry",
            "enable_saga_compensation": False,
            "nodes": [
                {"id": "step_guard", "action_handler": "forum.thread.update_guard", "type": "GUARD"},
                {"id": "step_persist", "action_handler": "forum.thread.update_persist", "type": "STORAGE"},
                {"id": "step_invalidate_cache", "action_handler": "forum.cache.invalidate_operator", "type": "CACHE"},
                {"id": "step_telemetry", "action_handler": "forum.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_guard", "to": "step_persist"},
                {"from": "step_persist", "to": "step_invalidate_cache"},
                {"from": "step_invalidate_cache", "to": "step_telemetry"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_FORUM_THREAD_UPDATE_PIPELINE",
                version="v1.0.0",
                topology_graph=topo_forum_thread_update,
                status="ACTIVE",
            )
        )

        # 6.5 Forum Answer Delete Pipeline: OPC_FORUM_ANSWER_DELETE_PIPELINE
        topo_forum_answer_delete = {
            "topology": "DAG",
            "entry_node": "step_guard",
            "exit_node": "step_telemetry",
            "enable_saga_compensation": False,
            "nodes": [
                {"id": "step_guard", "action_handler": "forum.answer.delete_guard", "type": "GUARD"},
                {"id": "step_persist", "action_handler": "forum.answer.delete_persist", "type": "STORAGE"},
                {"id": "step_invalidate_cache", "action_handler": "forum.cache.invalidate_operator", "type": "CACHE"},
                {"id": "step_telemetry", "action_handler": "forum.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_guard", "to": "step_persist"},
                {"from": "step_persist", "to": "step_invalidate_cache"},
                {"from": "step_invalidate_cache", "to": "step_telemetry"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_FORUM_ANSWER_DELETE_PIPELINE",
                version="v1.0.0",
                topology_graph=topo_forum_answer_delete,
                status="ACTIVE",
            )
        )

        # 6.6 Forum Comment Delete Pipeline: OPC_FORUM_COMMENT_DELETE_PIPELINE
        topo_forum_comment_delete = {
            "topology": "DAG",
            "entry_node": "step_guard",
            "exit_node": "step_telemetry",
            "enable_saga_compensation": False,
            "nodes": [
                {"id": "step_guard", "action_handler": "forum.comment.delete_guard", "type": "GUARD"},
                {"id": "step_persist", "action_handler": "forum.comment.delete_persist", "type": "STORAGE"},
                {"id": "step_telemetry", "action_handler": "forum.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_guard", "to": "step_persist"},
                {"from": "step_persist", "to": "step_telemetry"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_FORUM_COMMENT_DELETE_PIPELINE",
                version="v1.0.0",
                topology_graph=topo_forum_comment_delete,
                status="ACTIVE",
            )
        )

        # 7. Product Showcase Publish DAG Pipeline: OPC_PRODUCT_PUBLISH_PIPELINE
        topo_product_publish = {
            "topology": "DAG",
            "entry_node": "step_identity",
            "exit_node": "step_telemetry",
            "enable_saga_compensation": True,
            "nodes": [
                {"id": "step_identity", "action_handler": "content.publish.identity_guard", "type": "GUARD"},
                {"id": "step_guard", "action_handler": "product.validate_guard", "type": "GUARD"},
                {"id": "step_persist", "action_handler": "product.persist", "type": "STORAGE"},
                {"id": "step_telemetry", "action_handler": "product.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_identity", "to": "step_guard"},
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

        # 8. Policy Center Match DAG Pipeline: OPC_POLICY_MATCH_PIPELINE
        topo_policy_match = {
            "topology": "DAG",
            "entry_node": "step_guard",
            "exit_node": "step_telemetry",
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

        # 9. Policy Center Publish DAG Pipeline: OPC_POLICY_PUBLISH_PIPELINE
        topo_policy_publish = {
            "topology": "DAG",
            "entry_node": "step_identity",
            "exit_node": "step_telemetry",
            "enable_saga_compensation": True,
            "nodes": [
                {"id": "step_identity", "action_handler": "content.publish.identity_guard", "type": "GUARD"},
                {"id": "step_guard", "action_handler": "policy.publish.guard", "type": "GUARD"},
                {"id": "step_persist", "action_handler": "policy.publish.persist", "type": "STORAGE"},
                {"id": "step_telemetry", "action_handler": "policy.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_identity", "to": "step_guard"},
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
            "entry_node": "step_identity",
            "exit_node": "step_telemetry",
            "enable_saga_compensation": True,
            "nodes": [
                {"id": "step_identity", "action_handler": "content.publish.identity_guard", "type": "GUARD"},
                {"id": "step_guard", "action_handler": "demand.publish.guard", "type": "GUARD"},
                {"id": "step_persist", "action_handler": "demand.publish.persist", "type": "STORAGE"},
                {"id": "step_telemetry", "action_handler": "demand.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_identity", "to": "step_guard"},
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
            "entry_node": "step_identity",
            "exit_node": "step_telemetry",
            "enable_saga_compensation": True,
            "nodes": [
                {"id": "step_identity", "action_handler": "content.publish.identity_guard", "type": "GUARD"},
                {"id": "step_guard", "action_handler": "demand.bid.guard", "type": "GUARD"},
                {"id": "step_persist", "action_handler": "demand.bid.persist", "type": "STORAGE"},
                {"id": "step_telemetry", "action_handler": "demand.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_identity", "to": "step_guard"},
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
            "exit_node": "step_telemetry",
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
            "exit_node": "step_telemetry",
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
            "entry_node": "step_identity",
            "exit_node": "step_telemetry",
            "enable_saga_compensation": True,
            "nodes": [
                {"id": "step_identity", "action_handler": "content.publish.identity_guard", "type": "GUARD"},
                {"id": "step_guard", "action_handler": "perk.publish.guard", "type": "GUARD"},
                {"id": "step_persist", "action_handler": "perk.publish.persist", "type": "STORAGE"},
                {"id": "step_telemetry", "action_handler": "perk.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_identity", "to": "step_guard"},
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
            "exit_node": "step_telemetry",
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

        # 16. Content Moderation Takedown DAG Pipeline: OPC_MODERATION_TAKEDOWN_PIPELINE
        topo_moderation_takedown = {
            "topology": "DAG",
            "entry_node": "step_guard",
            "exit_node": "step_telemetry",
            "enable_saga_compensation": True,
            "nodes": [
                {"id": "step_guard", "action_handler": "moderation.takedown.guard", "type": "GUARD"},
                {"id": "step_persist", "action_handler": "moderation.takedown.persist", "type": "BIZ"},
                {"id": "step_telemetry", "action_handler": "moderation.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_guard", "to": "step_persist"},
                {"from": "step_persist", "to": "step_telemetry"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_MODERATION_TAKEDOWN_PIPELINE",
                version="v1.0.0",
                topology_graph=topo_moderation_takedown,
                status="ACTIVE",
            )
        )

        # 17. Content Moderation Restore DAG Pipeline: OPC_MODERATION_RESTORE_PIPELINE
        topo_moderation_restore = {
            "topology": "DAG",
            "entry_node": "step_guard",
            "exit_node": "step_telemetry",
            "enable_saga_compensation": True,
            "nodes": [
                {"id": "step_guard", "action_handler": "moderation.restore.guard", "type": "GUARD"},
                {"id": "step_persist", "action_handler": "moderation.restore.persist", "type": "BIZ"},
                {"id": "step_telemetry", "action_handler": "moderation.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_guard", "to": "step_persist"},
                {"from": "step_persist", "to": "step_telemetry"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_MODERATION_RESTORE_PIPELINE",
                version="v1.0.0",
                topology_graph=topo_moderation_restore,
                status="ACTIVE",
            )
        )

        # 18. Ops Dashboard DAG Pipeline: OPC_OPS_DASHBOARD_PIPELINE
        topo_ops_dashboard = {
            "topology": "DAG",
            "entry_node": "step_guard",
            "exit_node": "step_telemetry",
            "enable_saga_compensation": True,
            "nodes": [
                {"id": "step_guard", "action_handler": "telemetry.dashboard.guard", "type": "GUARD"},
                {"id": "step_collect", "action_handler": "telemetry.dashboard.collect", "type": "BIZ"},
                {"id": "step_audit", "action_handler": "telemetry.dashboard.audit", "type": "BIZ"},
                {"id": "step_telemetry", "action_handler": "telemetry.dashboard.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_guard", "to": "step_collect"},
                {"from": "step_collect", "to": "step_audit"},
                {"from": "step_audit", "to": "step_telemetry"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_OPS_DASHBOARD_PIPELINE",
                version="v1.0.0",
                topology_graph=topo_ops_dashboard,
                status="ACTIVE",
            )
        )

        # 19. User Maker Profile DAG Pipeline: OPC_USER_PROFILE_PIPELINE
        topo_user_profile = {
            "topology": "DAG",
            "entry_node": "step_guard",
            "exit_node": "step_telemetry",
            "enable_saga_compensation": True,
            "nodes": [
                {"id": "step_guard", "action_handler": "user.profile.guard", "type": "GUARD"},
                {"id": "step_load", "action_handler": "user.profile.load", "type": "BIZ"},
                {"id": "step_telemetry", "action_handler": "user.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_guard", "to": "step_load"},
                {"from": "step_load", "to": "step_telemetry"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_USER_PROFILE_PIPELINE",
                version="v1.0.0",
                topology_graph=topo_user_profile,
                status="ACTIVE",
            )
        )

        # 20. User Entitlement Activate DAG Pipeline: OPC_USER_ENTITLEMENT_ACTIVATE_PIPELINE
        topo_user_activate = {
            "topology": "DAG",
            "entry_node": "step_guard",
            "exit_node": "step_telemetry",
            "enable_saga_compensation": True,
            "nodes": [
                {"id": "step_guard", "action_handler": "user.entitlement.activate.guard", "type": "GUARD"},
                {"id": "step_persist", "action_handler": "user.entitlement.activate.persist", "type": "BIZ"},
                {"id": "step_telemetry", "action_handler": "user.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_guard", "to": "step_persist"},
                {"from": "step_persist", "to": "step_telemetry"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_USER_ENTITLEMENT_ACTIVATE_PIPELINE",
                version="v1.0.0",
                topology_graph=topo_user_activate,
                status="ACTIVE",
            )
        )

        # 21. Orchestration Control DAG Pipeline: OPC_ORCHESTRATION_CONTROL_PIPELINE
        topo_orch_control = {
            "topology": "DAG",
            "entry_node": "step_guard",
            "exit_node": "step_telemetry",
            "enable_saga_compensation": True,
            "nodes": [
                {"id": "step_guard", "action_handler": "orchestration.control.guard", "type": "GUARD"},
                {"id": "step_persist", "action_handler": "orchestration.control.persist", "type": "BIZ"},
                {"id": "step_telemetry", "action_handler": "orchestration.control.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_guard", "to": "step_persist"},
                {"from": "step_persist", "to": "step_telemetry"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_ORCHESTRATION_CONTROL_PIPELINE",
                version="v1.0.0",
                topology_graph=topo_orch_control,
                status="ACTIVE",
            )
        )

        # 22. Orchestration Operators List DAG Pipeline: OPC_ORCHESTRATION_OPERATORS_LIST_PIPELINE
        topo_orch_ops_list = {
            "topology": "DAG",
            "entry_node": "step_guard",
            "exit_node": "step_collect",
            "enable_saga_compensation": False,
            "nodes": [
                {"id": "step_guard", "action_handler": "orchestration.operators.guard", "type": "GUARD"},
                {"id": "step_collect", "action_handler": "orchestration.operators.collect", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_guard", "to": "step_collect"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_ORCHESTRATION_OPERATORS_LIST_PIPELINE",
                version="v1.0.0",
                topology_graph=topo_orch_ops_list,
                status="ACTIVE",
            )
        )

        # 23. Forum Infinite Stream Feed & Multi-tier Cache DAG Pipeline: OPC_FORUM_FEED_STREAM_PIPELINE
        #     共享缓存回写在前，观察者标注在后，保证缓存内容与具体用户无关。
        topo_forum_feed = {
            "topology": "DAG",
            "entry_node": "step_guard",
            "exit_node": "step_annotate",
            "enable_saga_compensation": False,
            "nodes": [
                {"id": "step_guard", "action_handler": "forum.feed.cursor_guard", "type": "GUARD"},
                {"id": "step_cache", "action_handler": "forum.feed.cache_read", "type": "CACHE"},
                {"id": "step_fetch", "action_handler": "forum.feed.stream_fetch", "type": "STORAGE"},
                {"id": "step_enrich", "action_handler": "forum.feed.enrich_prefetch_meta", "type": "BIZ"},
                {"id": "step_write", "action_handler": "forum.feed.cache_write", "type": "CACHE"},
                {"id": "step_annotate", "action_handler": "forum.feed.viewer_annotate", "type": "BIZ"},
                {"id": "step_telemetry", "action_handler": "forum.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_guard", "to": "step_cache"},
                {"from": "step_cache", "to": "step_fetch"},
                {"from": "step_fetch", "to": "step_enrich"},
                {"from": "step_enrich", "to": "step_write"},
                {"from": "step_write", "to": "step_annotate"},
                {"from": "step_annotate", "to": "step_telemetry"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_FORUM_FEED_STREAM_PIPELINE",
                version="v1.0.0",
                topology_graph=topo_forum_feed,
                status="ACTIVE",
            )
        )

        # 24. Compliance Publish DAG Pipeline: OPC_COMPLIANCE_PUBLISH_PIPELINE
        #     法条 / 避坑案例发布：身份 → 校验+敏感词 → 持久化 → 度量
        topo_compliance_publish = {
            "topology": "DAG",
            "entry_node": "step_identity",
            "exit_node": "step_telemetry",
            "enable_saga_compensation": True,
            "nodes": [
                {"id": "step_identity", "action_handler": "content.publish.identity_guard", "type": "GUARD"},
                {"id": "step_guard", "action_handler": "compliance.publish.guard", "type": "GUARD"},
                {"id": "step_persist", "action_handler": "compliance.publish.persist", "type": "STORAGE"},
                {"id": "step_telemetry", "action_handler": "content.publish.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_identity", "to": "step_guard"},
                {"from": "step_guard", "to": "step_persist"},
                {"from": "step_persist", "to": "step_telemetry"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_COMPLIANCE_PUBLISH_PIPELINE",
                version="v1.0.0",
                topology_graph=topo_compliance_publish,
                status="ACTIVE",
            )
        )

        # 25. Moderation User Report DAG Pipeline: OPC_MODERATION_REPORT_PIPELINE
        topo_moderation_report = {
            "topology": "DAG",
            "entry_node": "step_guard",
            "exit_node": "step_telemetry",
            "enable_saga_compensation": True,
            "nodes": [
                {"id": "step_guard", "action_handler": "moderation.report.guard", "type": "GUARD"},
                {"id": "step_persist", "action_handler": "moderation.report.persist", "type": "STORAGE"},
                {"id": "step_telemetry", "action_handler": "content.publish.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_guard", "to": "step_persist"},
                {"from": "step_persist", "to": "step_telemetry"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_MODERATION_REPORT_PIPELINE",
                version="v1.0.0",
                topology_graph=topo_moderation_report,
                status="ACTIVE",
            )
        )

        # 26. SOP Free-form Document Draft DAG Pipeline: OPC_SOP_DOCUMENT_DRAFT_PIPELINE
        topo_sop_draft = {
            "topology": "DAG",
            "entry_node": "step_identity",
            "exit_node": "step_telemetry",
            "enable_saga_compensation": True,
            "nodes": [
                {"id": "step_identity", "action_handler": "content.publish.identity_guard", "type": "GUARD"},
                {"id": "step_guard", "action_handler": "sop.document.draft.guard", "type": "GUARD"},
                {"id": "step_persist", "action_handler": "sop.document.draft.persist", "type": "STORAGE"},
                {"id": "step_telemetry", "action_handler": "content.publish.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_identity", "to": "step_guard"},
                {"from": "step_guard", "to": "step_persist"},
                {"from": "step_persist", "to": "step_telemetry"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_SOP_DOCUMENT_DRAFT_PIPELINE",
                version="v1.0.0",
                topology_graph=topo_sop_draft,
                status="ACTIVE",
            )
        )

        # 27. SOP Document Publish Review DAG Pipeline: OPC_SOP_DOCUMENT_PUBLISH_PIPELINE
        topo_sop_doc_publish = {
            "topology": "DAG",
            "entry_node": "step_identity",
            "exit_node": "step_telemetry",
            "enable_saga_compensation": True,
            "nodes": [
                {"id": "step_identity", "action_handler": "content.publish.identity_guard", "type": "GUARD"},
                {"id": "step_guard", "action_handler": "sop.document.publish.guard", "type": "GUARD"},
                {"id": "step_persist", "action_handler": "sop.document.publish.persist", "type": "STORAGE"},
                {"id": "step_telemetry", "action_handler": "content.publish.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_identity", "to": "step_guard"},
                {"from": "step_guard", "to": "step_persist"},
                {"from": "step_persist", "to": "step_telemetry"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_SOP_DOCUMENT_PUBLISH_PIPELINE",
                version="v1.0.0",
                topology_graph=topo_sop_doc_publish,
                status="ACTIVE",
            )
        )

        # 28. SOP Flow Publish Review DAG Pipeline: OPC_SOP_FLOW_PUBLISH_PIPELINE
        topo_sop_flow_publish = {
            "topology": "DAG",
            "entry_node": "step_identity",
            "exit_node": "step_telemetry",
            "enable_saga_compensation": True,
            "nodes": [
                {"id": "step_identity", "action_handler": "content.publish.identity_guard", "type": "GUARD"},
                {"id": "step_guard", "action_handler": "sop.flow.publish.guard", "type": "GUARD"},
                {"id": "step_persist", "action_handler": "sop.flow.publish.persist", "type": "STORAGE"},
                {"id": "step_telemetry", "action_handler": "content.publish.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_identity", "to": "step_guard"},
                {"from": "step_guard", "to": "step_persist"},
                {"from": "step_persist", "to": "step_telemetry"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_SOP_FLOW_PUBLISH_PIPELINE",
                version="v1.0.0",
                topology_graph=topo_sop_flow_publish,
                status="ACTIVE",
            )
        )

        # 29. Unified Content Comment DAG Pipeline: OPC_CONTENT_COMMENT_PUBLISH_PIPELINE
        topo_content_comment = {
            "topology": "DAG",
            "entry_node": "step_guard",
            "exit_node": "step_telemetry",
            "enable_saga_compensation": True,
            "nodes": [
                {"id": "step_guard", "action_handler": "content.comment.guard", "type": "GUARD"},
                {"id": "step_persist", "action_handler": "content.comment.persist", "type": "STORAGE"},
                {"id": "step_telemetry", "action_handler": "content.publish.telemetry.incr", "type": "BIZ"},
            ],
            "edges": [
                {"from": "step_guard", "to": "step_persist"},
                {"from": "step_persist", "to": "step_telemetry"},
            ],
        }
        self.save_dag_config(
            DAGConfigSaveRequest(
                scenario_code="OPC_CONTENT_COMMENT_PUBLISH_PIPELINE",
                version="v1.0.0",
                topology_graph=topo_content_comment,
                status="ACTIVE",
            )
        )

        # Default frontend layout (no hardcoded demo figures)
        self.save_frontend_layout(
            FrontendLayoutSaveRequest(
                layout_name="main_console_layout",
                version="v1.0.4",
                grid_schema={"columns": 24, "row_gap": 16, "col_gap": 16},
                widgets=[
                    {"id": "w1", "type": "stat", "span": 6, "title": "本季总创收", "value": ""},
                    {"id": "w2", "type": "stat", "span": 6, "title": "免征增值税", "value": ""},
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
        domain_persistence.write("orchestration.dag_configs", f"{req.scenario_code}@@{req.version}", record)
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
