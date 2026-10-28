"""Single-responsibility pure function operators for the SOP domain.

Only calculations / normalisation / assembly / state-transition policy live here.
Storage is handled by ``entity.*`` operators, guards by ``guard.*``, validation
by ``validate.*`` and notifications by ``notify.emit``. There is no I/O, no
orchestration, no cross-domain import and no ``execute_scenario`` call.
"""
from __future__ import annotations

import string
import uuid
from datetime import datetime, timezone
from typing import Any

from src.core.operators.sdk import operator

NODE_DOCUMENT = "document"
NODE_SUBGRAPH = "subgraph"

TARGET_DOCUMENT = "DOCUMENT"
TARGET_FLOW = "FLOW"

STATUS_READY = "READY"
STATUS_PENDING_REVIEW = "PENDING_REVIEW"
STATUS_APPROVED = "APPROVED"
STATUS_PUBLISHED = "PUBLISHED"
STATUS_REJECTED = "REJECTED"
STATUS_WITHDRAWN = "WITHDRAWN"

FLOW_STATUS_ACTIVE = "ACTIVE"

ACTION_APPROVE = "APPROVE"
ACTION_REJECT = "REJECT"
ACTION_WITHDRAW = "WITHDRAW"

#: The publish-review state machine: current state -> action -> next state.
REVIEW_TRANSITIONS: dict[str, dict[str, str]] = {
    STATUS_PENDING_REVIEW: {
        ACTION_APPROVE: STATUS_APPROVED,
        ACTION_REJECT: STATUS_REJECTED,
        ACTION_WITHDRAW: STATUS_WITHDRAWN,
    },
}

_OPTIONAL_EDGE = "optional"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _as_int(value: Any, default: int = 0) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return number


def _flatten(text: Any, limit: int = 0) -> str:
    """Collapse whitespace / newlines into one line (card summaries)."""
    flat = " ".join(str(text or "").split())
    return flat[:limit] if limit else flat


def _render(raw: str, values: dict[str, Any]) -> str:
    """Interpolate ``{placeholder}`` tokens with a safe, missing-key tolerant dict."""

    class _Safe(dict):
        def __missing__(self, key: str) -> str:  # noqa: D401 - formatter hook
            return ""

    try:
        return string.Formatter().vformat(raw, (), _Safe(values))
    except (ValueError, IndexError, KeyError):
        rendered = raw
        for key, value in values.items():
            rendered = rendered.replace("{" + str(key) + "}", str(value))
        return rendered


def _normalise_refs(raw_refs: Any) -> list[dict[str, Any]]:
    """Normalise flow template / user flow step references."""
    refs: list[dict[str, Any]] = []
    for raw in raw_refs or []:
        if isinstance(raw, str):
            refs.append({"node_id": raw, "required": True, "note": ""})
            continue
        if not isinstance(raw, dict):
            continue
        node_id = _text(raw.get("node_id") or raw.get("id"))
        if not node_id:
            continue
        refs.append(
            {
                "node_id": node_id,
                "required": bool(raw.get("required", True)),
                "note": _text(raw.get("note")),
            }
        )
    return refs


def _normalise_flow_edges(raw_edges: Any) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for raw in raw_edges or []:
        if not isinstance(raw, dict):
            continue
        source = _text(raw.get("from_ref") or raw.get("from_node"))
        target = _text(raw.get("to_ref") or raw.get("to_node"))
        if not source or not target:
            continue
        edges.append({"from_ref": source, "to_ref": target, "rationale": _text(raw.get("rationale"))})
    return edges


def _node_index(nodes: Any) -> dict[str, dict[str, Any]]:
    return {
        _text(node.get("id")): node
        for node in (nodes or [])
        if isinstance(node, dict) and _text(node.get("id"))
    }


def _topological_order(
    node_ids: list[str],
    nodes_by_id: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
) -> list[str]:
    """Order node ids so prerequisites come before dependents (stage tie-break)."""
    node_set = {node_id for node_id in node_ids if node_id}
    relevant = [
        edge
        for edge in (edges or [])
        if _text(edge.get("from_node")) in node_set
        and _text(edge.get("to_node")) in node_set
        and _text(edge.get("relation") or "prerequisite") != _OPTIONAL_EDGE
    ]

    def stage_of(node_id: str) -> int:
        return _as_int((nodes_by_id.get(node_id) or {}).get("stage"), 99)

    indegree = {node_id: 0 for node_id in node_set}
    adjacency: dict[str, list[str]] = {node_id: [] for node_id in node_set}
    for edge in relevant:
        source = _text(edge.get("from_node"))
        target = _text(edge.get("to_node"))
        adjacency[source].append(target)
        indegree[target] = indegree.get(target, 0) + 1

    ready = sorted([n for n in node_set if indegree.get(n, 0) == 0], key=lambda n: (stage_of(n), n))
    ordered: list[str] = []
    while ready:
        current = ready.pop(0)
        ordered.append(current)
        for neighbour in adjacency.get(current, []):
            indegree[neighbour] -= 1
            if indegree[neighbour] == 0:
                ready.append(neighbour)
        ready.sort(key=lambda n: (stage_of(n), n))

    if len(ordered) < len(node_set):
        remaining = sorted([n for n in node_set if n not in ordered], key=lambda n: (stage_of(n), n))
        ordered.extend(remaining)
    return ordered


# ---------------------------------------------------------------------------
# Document rendering & drafting
# ---------------------------------------------------------------------------
@operator(
    "calc.sop.render_document",
    category="CALC",
    description="Interpolate one document template and validate its required fields",
)
def render_document(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Render a fillable template into a persistable document instance."""
    template_id = _text(args.get("template_id"))
    template = args.get("template") if isinstance(args.get("template"), dict) else {}
    if not template:
        raise KeyError(f"SOP template with ID {template_id} not found")

    form_data = args.get("form_data") if isinstance(args.get("form_data"), dict) else {}
    merged: dict[str, Any] = {}
    missing: list[str] = []
    for field in template.get("required_fields") or []:
        if not isinstance(field, dict):
            continue
        key = _text(field.get("key"))
        if not key:
            continue
        value = form_data.get(key, field.get("default"))
        merged[key] = "" if value is None else value
        required = bool(field.get("required", True))
        if required and not _text(merged[key]) and not isinstance(merged[key], (int, float)):
            missing.append(key)

    if missing and bool(params.get("enforce_required", True)):
        raise ValueError(f"文书模板缺少必填字段：{'、'.join(missing)}")

    merged["verify_serial"] = "VER-" + uuid.uuid4().hex[:12].upper()
    rendered = _render(_text(template.get("template_content")), merged)
    company = _text(merged.get("company_name")) or "创客主体"
    document = {
        "id": _text(args.get("doc_id")) or f"doc_{uuid.uuid4().hex[:16]}",
        "template_id": template_id,
        "user_id": _text(context.get("user_id")) or _text(args.get("user_id")),
        "document_title": f"{_text(template.get('name'))} - {company}",
        "form_data": merged,
        "rendered_content": rendered,
        "compliance_passed": True,
        "category": _text(template.get("category")) or "LEGAL",
        "status": STATUS_READY,
    }
    return {
        "document": document,
        "rendered_content": rendered,
        "missing_fields": missing,
        "verify_serial": merged["verify_serial"],
    }


def _draft_title(title: Any, fallback: Any) -> str:
    clean = _text(title)
    if clean:
        return clean[:255]
    existing = _text(fallback)
    if existing:
        return existing
    return "未命名文书 " + datetime.now().strftime("%Y-%m-%d %H:%M")


def _draft_category(payload_category: Any, template: Any) -> str:
    category = _text(payload_category)
    if category:
        return category
    if isinstance(template, dict):
        category = _text(template.get("category"))
        if category:
            return category
    return "LEGAL"


@operator(
    "calc.sop.document_draft",
    category="CALC",
    description="Diff a free-form document draft (create vs update) and snapshot the previous state",
)
def document_draft(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Build the persistable draft payload plus the pre-save snapshot for rollback."""
    content = _text(args.get("content"))
    if not content:
        raise ValueError("文书正文不能为空，请先撰写内容")

    template = args.get("template") if isinstance(args.get("template"), dict) else {}
    template_id = _text(args.get("template_id"))
    category = _draft_category(args.get("category"), template)
    user_id = _text(context.get("user_id")) or _text(args.get("user_id"))
    doc_id = _text(args.get("doc_id"))
    current = args.get("current") if isinstance(args.get("current"), dict) else None

    if doc_id:
        if not current:
            raise KeyError(f"SOP document with ID {doc_id} not found")
        owner = _text(current.get("user_id"))
        if owner and user_id and owner != user_id:
            raise ValueError("只能编辑本人创建的文书")
        if _text(current.get("status")) in (STATUS_PENDING_REVIEW, STATUS_PUBLISHED):
            raise ValueError("审核中或已发布的文书不能直接修改")

        snapshot = {
            "document_title": current.get("document_title"),
            "rendered_content": current.get("rendered_content"),
            "template_id": current.get("template_id"),
            "category": current.get("category"),
            "status": current.get("status"),
            "updated_at": current.get("updated_at"),
        }
        changed = [
            name
            for name, before, after in (
                ("title", _text(current.get("document_title")), _draft_title(args.get("title"), current.get("document_title"))),
                ("content", _text(current.get("rendered_content")), content),
                ("template_id", _text(current.get("template_id")), template_id or _text(current.get("template_id"))),
                ("category", _text(current.get("category")), category),
            )
            if before != after
        ]
        document = {
            "id": doc_id,
            "template_id": template_id or _text(current.get("template_id")),
            "user_id": owner or user_id,
            "document_title": _draft_title(args.get("title"), current.get("document_title")),
            "form_data": current.get("form_data") or {},
            "rendered_content": content,
            "compliance_passed": True,
            "category": category,
            "status": STATUS_READY,
        }
        return {"action": "update", "document": document, "snapshot": snapshot, "changed": changed}

    document = {
        "id": f"doc_{uuid.uuid4().hex[:16]}",
        "template_id": template_id,
        "user_id": user_id,
        "document_title": _draft_title(args.get("title"), ""),
        "form_data": {},
        "rendered_content": content,
        "compliance_passed": True,
        "category": category,
        "status": STATUS_READY,
    }
    return {"action": "create", "document": document, "snapshot": None, "changed": ["created"]}


# ---------------------------------------------------------------------------
# Publish-review policy (submission + state machine + audit)
# ---------------------------------------------------------------------------
@operator(
    "calc.sop.review_submission",
    category="CALC",
    description="Build one publish-review submission (queue item + target status patch)",
)
def review_submission(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Project a private document / flow into a queued review submission."""
    target_type = _text(args.get("target_type") or params.get("target_type")).upper()
    target = args.get("target") if isinstance(args.get("target"), dict) else {}
    if not target:
        raise KeyError("发布审核对象不存在")
    user_id = _text(context.get("user_id")) or _text(args.get("user_id"))
    role = _text(context.get("user_role") or args.get("role")).upper()
    now = _now()

    if target_type == TARGET_DOCUMENT:
        target_id = _text(target.get("id"))
        owner = _text(target.get("user_id"))
        label = "文书"
        if owner and user_id and owner != user_id:
            raise ValueError("只能发布本人创建的文书")
        if _text(target.get("status")) in (STATUS_PENDING_REVIEW, STATUS_PUBLISHED):
            raise ValueError("该文书已在审核队列中或已发布，无需重复提交")
        title = _text(target.get("document_title"))
        body = _text(target.get("rendered_content"))
        if not body:
            raise ValueError("文书正文为空，无法提交审核")
        content = f"{title}\n{_flatten(body)}"
        message = "发布成功，文书已进入待审核状态，审核通过后将发布至标准文书库"
    elif target_type == TARGET_FLOW:
        target_id = _text(target.get("id"))
        owner = _text(target.get("owner_id"))
        label = "流程"
        if owner and user_id and owner != user_id:
            raise ValueError("只能发布本人创建的流程")
        if _text(target.get("status")) in (STATUS_PENDING_REVIEW, STATUS_PUBLISHED):
            raise ValueError("该流程已在审核队列中或已发布，无需重复提交")
        title = _text(target.get("name"))
        step_names = "、".join(_text(step.get("name")) for step in (args.get("steps") or []))
        content = f"{title}\n{_text(target.get('description'))}\n流程步骤：{step_names}"
        missing = [_text(node_id) for node_id in (args.get("missing") or []) if _text(node_id)]
        if missing:
            content = f"{content}\n失效节点：{'、'.join(missing)}"
        message = "发布成功，流程已进入待审核状态，审核通过后将发布至流程向导"
    else:
        raise ValueError(f"未知的发布审核对象类型：{target_type or '<empty>'}")

    item = {
        "id": f"rev_{uuid.uuid4().hex[:10]}",
        "target_type": target_type,
        "target_id": target_id,
        "title": title,
        "content": content,
        "author_id": user_id or owner,
        "author_name": _text(context.get("nickname")) or _text(args.get("author_name")) or "创客",
        "is_official": role == "ADMIN",
        "status": STATUS_PENDING_REVIEW,
        "submitted_at": now,
        "reviewed_at": None,
        "review_note": None,
        "moderator_id": None,
    }
    return {
        "review_item": item,
        "target_patch": {"id": target_id, "status": STATUS_PENDING_REVIEW, "updated_at": now},
        "response": {
            "item_id": item["id"],
            "target_id": target_id,
            "target_type": target_type,
            "status": STATUS_PENDING_REVIEW,
            "submitted_at": now,
            "message": message,
        },
        "target_label": label,
    }


@operator(
    "calc.sop.review_transition",
    category="CALC",
    description="Apply the publish-review state machine (PENDING/APPROVED/REJECTED/WITHDRAWN)",
)
def review_transition(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Return the review-item patch, the target patch and the notification payload."""
    action = _text(args.get("action") or params.get("action")).upper()
    current = (_text(args.get("current") or params.get("current")) or STATUS_PENDING_REVIEW).upper()
    target_type = _text(args.get("target_type")).upper()
    target_id = _text(args.get("target_id"))
    item_id = _text(args.get("item_id"))
    title = _text(args.get("title"))
    reason = _text(args.get("reason"))
    published_id = _text(args.get("published_id"))
    moderator_id = _text(args.get("moderator_id")) or _text(context.get("user_id")) or "review_engine"

    allowed = REVIEW_TRANSITIONS.get(current, {})
    if action not in allowed:
        raise ValueError(f"审核项当前状态 '{current}' 不允许执行 {action} 操作")

    status = allowed[action]
    now = _now()
    if status == STATUS_APPROVED:
        target_status = STATUS_PUBLISHED
        where = "标准文书库" if target_type == TARGET_DOCUMENT else "流程向导"
        note = f"审核通过：内容合法合规，已发布至{where}" + (f"（{published_id}）" if published_id else "")
        notification_title = f"《{title}》审核通过"
    elif status == STATUS_REJECTED:
        target_status = STATUS_REJECTED
        note = f"审核未通过：{reason or '内容不符合平台发布规范'}"
        notification_title = f"《{title}》审核未通过"
    else:
        target_status = STATUS_READY if target_type == TARGET_DOCUMENT else FLOW_STATUS_ACTIVE
        note = "创客已撤回审核提交，可继续编辑后重新提交审核"
        notification_title = f"《{title}》已撤回发布审核"

    return {
        "allowed": True,
        "action": action,
        "status": status,
        "target_status": target_status,
        "review_note": note,
        "reviewed_at": now,
        "moderator_id": moderator_id,
        "item_patch": {
            "id": item_id,
            "status": status,
            "review_note": note,
            "reviewed_at": now,
            "moderator_id": moderator_id,
        },
        "target_patch": {"id": target_id, "status": target_status, "updated_at": now},
        "notification": {
            "title": notification_title,
            "body": note,
            "link": "sop",
        },
    }


@operator(
    "calc.sop.screen_content",
    category="CALC",
    description="Declarative sensitive-word pre-screen for a publish submission",
)
def screen_content(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Match a declared keyword list against one submission body (fast, local, pure)."""
    content = _text(args.get("content"))
    keywords = [_text(word) for word in (params.get("keywords") or args.get("keywords") or []) if _text(word)]
    hits = [word for word in keywords if word in content]
    return {
        "passed": not hits,
        "hit_words": hits,
        "reason": (
            f"内容合规校验未通过：命中敏感词 {'、'.join(hits)}" if hits else ""
        ),
    }


@operator(
    "calc.sop.review_audit",
    category="CALC",
    description="Audit one queued submission for compliance completeness (legality / structure)",
)
def review_audit(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Decide APPROVE / REJECT from the content-safety gate and completeness checks."""
    target_type = _text(args.get("target_type")).upper()
    gate_passed = args.get("gate_passed")
    gate_reason = _text(args.get("gate_reason"))
    screen_passed = args.get("screen_passed")

    def _reject(reason: str) -> dict[str, Any]:
        return {"action": ACTION_REJECT, "passed": False, "reason": reason}

    if gate_passed is False:
        return _reject(gate_reason or "内容未通过平台敏感词校验")
    if screen_passed is False:
        return _reject(_text(args.get("screen_reason")) or "内容未通过平台敏感词校验")

    if target_type == TARGET_DOCUMENT:
        document = args.get("document") if isinstance(args.get("document"), dict) else {}
        if not document:
            return _reject("文书不存在或已删除")
        if not bool(document.get("compliance_passed", True)):
            return _reject("文书合规校验未通过，无法发布")
        if len(_flatten(document.get("rendered_content"))) < 10:
            return _reject("文书正文内容过短，缺少可发布的合规条款")
    elif target_type == TARGET_FLOW:
        flow = args.get("flow") if isinstance(args.get("flow"), dict) else {}
        if not flow:
            return _reject("流程不存在或已删除")
        missing = [_text(node_id) for node_id in (args.get("missing") or []) if _text(node_id)]
        if missing:
            return _reject(f"流程包含失效节点：{'、'.join(missing)}")
        if not (args.get("steps") or []):
            return _reject("流程未包含任何文书步骤，无法发布")
    else:
        return _reject(f"未知的审核对象类型：{target_type or '<empty>'}")

    return {"action": ACTION_APPROVE, "passed": True, "reason": ""}


# ---------------------------------------------------------------------------
# Flow / template projections
# ---------------------------------------------------------------------------
@operator(
    "calc.sop.steps",
    category="CALC",
    description="Resolve flow node references into ordered document steps",
)
def steps(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Expand subgraphs and order the resulting documents (topology or reference order)."""
    refs = _normalise_refs(args.get("refs"))
    nodes = args.get("nodes") or []
    edges = args.get("edges") or []
    nodes_by_id = _node_index(nodes)

    plan: list[dict[str, Any]] = []
    missing: list[str] = []
    seen: set[str] = set()

    def collect(node_id: str, required: bool, note: str, parent_id: str | None, depth: int) -> None:
        if node_id in seen:
            return
        seen.add(node_id)
        node = nodes_by_id.get(node_id)
        if node is None:
            missing.append(node_id)
            return
        if _text(node.get("kind")) == NODE_SUBGRAPH:
            for child_id in node.get("children") or []:
                collect(_text(child_id), required, note, node_id, depth + 1)
            return
        plan.append(
            {
                "node_id": _text(node.get("id")),
                "name": _text(node.get("name")),
                "kind": _text(node.get("kind")) or NODE_DOCUMENT,
                "stage": _as_int(node.get("stage"), 1),
                "category": _text(node.get("category")),
                "description": _text(node.get("description")),
                "outcome": _text(node.get("outcome")),
                "next_hint": _text(node.get("next_hint")),
                "note": note,
                "required": required,
                "order": 0,
                "depth": depth,
                "parent_id": parent_id,
                "required_fields": node.get("required_fields") or [],
            }
        )

    for ref in refs:
        collect(ref["node_id"], ref["required"], ref["note"], None, 0)

    order_mode = _text(params.get("order") or "TOPOLOGY").upper()
    if order_mode == "REFERENCE":
        for index, item in enumerate(plan):
            item["order"] = index + 1
    else:
        ordered = _topological_order([item["node_id"] for item in plan], nodes_by_id, edges)
        rank = {node_id: index for index, node_id in enumerate(ordered)}
        for item in plan:
            item["order"] = rank.get(item["node_id"], 0) + 1
        plan.sort(key=lambda item: (item["order"], item["node_id"]))

    return {"items": plan, "missing_nodes": missing, "node_ids": [item["node_id"] for item in plan]}


@operator(
    "calc.sop.query",
    category="CALC",
    description="Normalise a SOP list query into generic entity-store filters",
)
def query(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Translate catalog / workspace query parameters into store filters + paging."""
    filters: dict[str, Any] = dict(params.get("filters") or {})

    category = _text(args.get("category"))
    if category and category.upper() != "ALL":
        filters["category"] = category

    kind = _text(args.get("kind") or params.get("kind"))
    if kind:
        filters["kind"] = kind

    status = _text(args.get("status"))
    if status and status.upper() != "ALL":
        filters["status"] = status.upper()

    owner_field = _text(params.get("owner_field"))
    owner_id = _text(args.get("owner_id")) or (_text(args.get("user_id")) if owner_field else "")
    if owner_field and owner_id:
        filters[owner_field] = owner_id

    return {
        "filters": filters,
        "search": _text(args.get("search")) or None,
        "order": _text(args.get("order") or params.get("order")) or None,
        "page": max(1, _as_int(args.get("page"), 1)),
        "page_size": max(1, min(200, _as_int(args.get("page_size") or params.get("default_page_size"), 20))),
        "limit": params.get("limit"),
    }


@operator(
    "calc.sop.page",
    category="CALC",
    description="Derive pagination metadata from a SOP document list",
)
def page(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    items = args.get("items") or []
    total = _as_int(args.get("total"), len(items))
    page_no = max(1, _as_int(args.get("page"), 1))
    page_size = max(1, min(200, _as_int(args.get("page_size"), 20)))
    total_pages = max(1, -(-total // page_size))
    start = (page_no - 1) * page_size
    return {
        "items": items[start : start + page_size],
        "total": total,
        "page": page_no,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_more": start + page_size < total,
    }


@operator(
    "calc.sop.flow_create",
    category="CALC",
    description="Normalise a maker-owned flow creation payload",
)
def flow_create(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    name = _text(args.get("name"))
    if len(name) < 2:
        raise ValueError("流程名称至少需要 2 个字符")
    now = _now()
    flow = {
        "id": f"flow_{uuid.uuid4().hex[:10]}",
        "name": name,
        "description": _text(args.get("description")),
        "owner_id": _text(context.get("user_id")) or _text(args.get("owner_id")),
        "goal_id": args.get("goal_id") or None,
        "node_refs": _normalise_refs(args.get("node_refs")),
        "edges": _normalise_flow_edges(args.get("edges")),
        "status": (_text(args.get("status")) or FLOW_STATUS_ACTIVE).upper(),
        "created_at": now,
        "updated_at": now,
    }
    return {"flow": flow}


@operator(
    "calc.sop.flow_update",
    category="CALC",
    description="Diff a maker-owned flow update and reset its publish state",
)
def flow_update(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    current = args.get("current") if isinstance(args.get("current"), dict) else {}
    if not current:
        raise KeyError(f"SOP flow with ID {_text(args.get('flow_id'))} not found")
    name = _text(args.get("name")) or _text(current.get("name"))
    if len(name) < 2:
        raise ValueError("流程名称至少需要 2 个字符")

    status = (_text(args.get("status")) or _text(current.get("status")) or FLOW_STATUS_ACTIVE).upper()
    # Editing a published / rejected / pending flow produces a fresh editable draft.
    if status in (STATUS_PUBLISHED, STATUS_REJECTED, STATUS_PENDING_REVIEW):
        status = FLOW_STATUS_ACTIVE

    flow = {
        "id": _text(current.get("id")),
        "name": name,
        "description": _text(args.get("description")),
        "owner_id": _text(current.get("owner_id")),
        "goal_id": args.get("goal_id") if "goal_id" in args else current.get("goal_id"),
        "node_refs": _normalise_refs(args.get("node_refs")),
        "edges": _normalise_flow_edges(args.get("edges")),
        "status": status,
        "created_at": _text(current.get("created_at")) or _now(),
        "updated_at": _now(),
    }
    return {"flow": flow}


@operator(
    "calc.sop.template_publish",
    category="CALC",
    description="Normalise a document template publish payload into template + graph node",
)
def template_publish(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    stage = _as_int(args.get("stage"), 0)
    if stage < 1 or stage > 4:
        raise ValueError("模板阶段（stage）必须在 1-4 之间")
    code = _text(args.get("code"))
    if len(code) < 2:
        raise ValueError("模板编码（code）至少需要 2 个字符")
    name = _text(args.get("name"))
    if len(name) < 2:
        raise ValueError("模板名称（name）至少需要 2 个字符")
    description = _text(args.get("description"))
    if len(description) < 5:
        raise ValueError("模板说明（description）至少需要 5 个字符")
    template_content = str(args.get("template_content") or "")
    if len(template_content) < 5:
        raise ValueError("模板正文（template_content）至少需要 5 个字符")

    category = _text(args.get("category")) or "TAX"
    required_fields = [field for field in (args.get("required_fields") or []) if isinstance(field, dict)]
    template_id = _text(args.get("template_id")) or f"tpl_{uuid.uuid4().hex[:8]}"
    template = {
        "id": template_id,
        "stage": stage,
        "code": code,
        "name": name,
        "category": category,
        "description": description,
        "template_content": template_content,
        "required_fields": required_fields,
        "is_active": True,
    }
    node = {
        "id": template_id,
        "kind": NODE_DOCUMENT,
        "code": code,
        "name": name,
        "stage": stage,
        "category": category,
        "description": description,
        "template_content": template_content,
        "required_fields": required_fields,
        "is_active": True,
    }
    return {"template": template, "node": node, "template_id": template_id}


@operator(
    "calc.sop.published_document",
    category="CALC",
    description="Project an approved document into the standard document catalog entries",
)
def published_document(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    document = args.get("document") if isinstance(args.get("document"), dict) else {}
    if not document:
        raise KeyError("待发布的文书不存在")
    item = args.get("item") if isinstance(args.get("item"), dict) else {}
    template = args.get("template") if isinstance(args.get("template"), dict) else {}

    body = _flatten(document.get("rendered_content"))
    is_official = bool(item.get("is_official"))
    stage = _as_int(template.get("stage"), 1)
    category = _text(document.get("category")) or _text(template.get("category")) or "LEGAL"
    title = _text(document.get("document_title"))
    author_name = _text(item.get("author_name")) or "创客"
    node_id = f"tpl_pub_{uuid.uuid4().hex[:8]}"
    code = f"PUB_{uuid.uuid4().hex[:6].upper()}"

    node = {
        "id": node_id,
        "kind": NODE_DOCUMENT,
        "code": code,
        "name": title,
        "stage": stage,
        "category": category,
        "description": body[:120],
        "outcome": "官方发布的标准文书，可直接查看与复用" if is_official else "由创客发布的标准文书，可直接查看与复用",
        "next_hint": "查看文书正文，按需用于商事与合规申报。",
        "summary": body[:90] or "创客发布的合规文书",
        "author_name": author_name,
        "author_title": "官方发布" if is_official else "创客发布",
        "publisher_org": "官方发布" if is_official else "创客发布",
        "is_official": is_official,
        "published_at": _now(),
        "template_content": _text(document.get("rendered_content")),
        "required_fields": [],
        "is_active": True,
    }
    template_doc = {
        "id": node_id,
        "stage": stage,
        "code": code,
        "name": title,
        "category": category,
        "description": body[:120],
        "template_content": _text(document.get("rendered_content")),
        "required_fields": [],
        "is_active": True,
    }
    return {"node": node, "template": template_doc, "published_id": node_id}


_FLOW_CATEGORY_MAP = {"ENTITY": "ENTITY", "IP": "IP", "CROSS_BORDER": "CROSS_BORDER"}


def _flow_category(steps: list[dict[str, Any]]) -> str:
    counts: dict[str, int] = {}
    for step in steps:
        category = _FLOW_CATEGORY_MAP.get(_text(step.get("category")), "COMPLIANCE")
        counts[category] = counts.get(category, 0) + 1
    if not counts:
        return "COMPLIANCE"
    return max(counts, key=counts.get)


@operator(
    "calc.sop.published_flow",
    category="CALC",
    description="Project an approved flow into the platform flow-template catalog entry",
)
def published_flow(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    flow = args.get("flow") if isinstance(args.get("flow"), dict) else {}
    if not flow:
        raise KeyError("待发布的流程不存在")
    item = args.get("item") if isinstance(args.get("item"), dict) else {}
    steps = [step for step in (args.get("steps") or []) if isinstance(step, dict)]
    is_official = bool(item.get("is_official"))

    description = _text(flow.get("description"))
    summary = description.split("。")[0] if description else _text(flow.get("name"))
    template_id = f"flowpub_{uuid.uuid4().hex[:8]}"
    flow_template = {
        "id": template_id,
        "code": f"USER_PUB_{uuid.uuid4().hex[:6].upper()}",
        "name": _text(flow.get("name")),
        "summary": summary or "创客发布的办事流程",
        "description": description or summary,
        "category": _flow_category(steps),
        "stages": sorted({_as_int(step.get("stage"), 1) for step in steps}),
        "node_refs": _normalise_refs(flow.get("node_refs")),
        "outcome": f"{'官方' if is_official else '由创客'}编排的办事流程，共 {len(steps)} 个步骤",
        "unlocks": [],
        "author_name": _text(item.get("author_name")) or "创客",
        "author_title": "官方发布" if is_official else "创客发布",
        "publisher_org": "官方发布" if is_official else "创客发布",
        "is_official": is_official,
        "published_at": _now(),
    }
    return {"flow_template": flow_template, "published_id": template_id}


# ---------------------------------------------------------------------------
# Assemblers
# ---------------------------------------------------------------------------
@operator(
    "assemble.sop.template_cards",
    category="ASSEMBLE",
    description="Assemble the document template catalog (stages + fillable templates)",
)
def template_cards(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Project document graph nodes into the legacy template catalog shape.

    Document nodes double as renderable templates, so the catalog is a projection
    of the graph rather than a second copy of the data.
    """
    stages = [stage for stage in (args.get("stages") or []) if isinstance(stage, dict)]
    templates = []
    for node in args.get("nodes") or []:
        if not isinstance(node, dict) or _text(node.get("kind")) != NODE_DOCUMENT:
            continue
        templates.append(
            {
                "id": _text(node.get("id")),
                "stage": _as_int(node.get("stage"), 1),
                "code": _text(node.get("code")),
                "name": _text(node.get("name")),
                "category": _text(node.get("category")) or "TAX",
                "description": _text(node.get("description")),
                "template_content": _text(node.get("template_content")),
                "required_fields": node.get("required_fields") or [],
                "is_active": bool(node.get("is_active", True)),
            }
        )
    templates.sort(key=lambda template: (template["stage"], template["name"]))
    return {"stages": stages, "templates": templates}


@operator(
    "assemble.sop.document_cards",
    category="ASSEMBLE",
    description="Project standard document nodes as workbench cards with live usage counts",
)
def document_cards(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    nodes = [node for node in (args.get("nodes") or []) if isinstance(node, dict)]
    usage: dict[str, int] = {}
    for document in args.get("documents") or []:
        if isinstance(document, dict):
            template_id = _text(document.get("template_id"))
            if template_id:
                usage[template_id] = usage.get(template_id, 0) + 1

    cards = []
    for node in nodes:
        if _text(node.get("kind")) != NODE_DOCUMENT or not bool(node.get("is_active", True)):
            continue
        node_id = _text(node.get("id"))
        cards.append(
            {
                "id": node_id,
                "name": _text(node.get("name")),
                "summary": _text(node.get("summary")) or _text(node.get("description")),
                "author_name": _text(node.get("author_name")),
                "author_title": _text(node.get("author_title")),
                "publisher_org": _text(node.get("publisher_org")),
                "is_official": bool(node.get("is_official")),
                "published_at": _text(node.get("published_at")),
                "stage": _as_int(node.get("stage"), 1),
                "category": _text(node.get("category")) or "TAX",
                "like_count": _as_int(node.get("like_count")),
                "favorite_count": _as_int(node.get("favorite_count")),
                "usage_count": _as_int(node.get("usage_count")) + usage.get(node_id, 0),
                "field_count": len(node.get("required_fields") or []),
            }
        )
    cards.sort(key=lambda card: (card["like_count"], card["published_at"]), reverse=True)
    return {"items": cards, "total": len(cards)}


@operator(
    "assemble.sop.flow_template_cards",
    category="ASSEMBLE",
    description="Project platform flow templates as flow-guide cards",
)
def flow_template_cards(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    templates = [template for template in (args.get("templates") or []) if isinstance(template, dict)]
    nodes = args.get("nodes") or []
    nodes_by_id = _node_index(nodes)

    usage: dict[str, int] = {}
    for flow in args.get("flows") or []:
        if isinstance(flow, dict):
            template_id = _text(flow.get("template_id"))
            if template_id:
                usage[template_id] = usage.get(template_id, 0) + 1

    cards = []
    for template in templates:
        step_list = _resolve_steps(_normalise_refs(template.get("node_refs")), nodes_by_id)
        doc_count = sum(1 for step in step_list if step["kind"] == NODE_DOCUMENT)
        template_id = _text(template.get("id"))
        cards.append(
            {
                "id": template_id,
                "name": _text(template.get("name")),
                "summary": _text(template.get("summary")),
                "description": _text(template.get("description")),
                "category": _text(template.get("category")) or "ENTITY",
                "stages": template.get("stages") or sorted({step["stage"] for step in step_list}),
                "step_count": len(step_list),
                "doc_count": doc_count,
                "outcome": _text(template.get("outcome")),
                "unlocks": template.get("unlocks") or [],
                "author_name": _text(template.get("author_name")),
                "author_title": _text(template.get("author_title")),
                "publisher_org": _text(template.get("publisher_org")),
                "is_official": bool(template.get("is_official")),
                "published_at": _text(template.get("published_at")),
                "like_count": _as_int(template.get("like_count")),
                "favorite_count": _as_int(template.get("favorite_count")),
                "usage_count": _as_int(template.get("usage_count")) + usage.get(template_id, 0),
            }
        )
    cards.sort(key=lambda card: (card["like_count"], card["published_at"]), reverse=True)
    return {"items": cards, "total": len(cards)}


def _resolve_steps(
    refs: list[dict[str, Any]],
    nodes_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Flatten references (expanding subgraphs) in reference order."""
    steps: list[dict[str, Any]] = []
    seen: set[str] = set()

    def walk(node_id: str, required: bool, note: str) -> None:
        if node_id in seen:
            return
        seen.add(node_id)
        node = nodes_by_id.get(node_id)
        if node is None:
            return
        if _text(node.get("kind")) == NODE_SUBGRAPH:
            for child_id in node.get("children") or []:
                walk(_text(child_id), required, note)
            return
        steps.append(
            {
                "node_id": node_id,
                "name": _text(node.get("name")),
                "kind": _text(node.get("kind")) or NODE_DOCUMENT,
                "stage": _as_int(node.get("stage"), 1),
                "category": _text(node.get("category")),
                "description": _text(node.get("description")),
                "outcome": _text(node.get("outcome")),
                "note": note,
                "required": required,
                "required_fields": node.get("required_fields") or [],
            }
        )

    for ref in refs:
        walk(ref["node_id"], ref["required"], ref["note"])
    for index, step in enumerate(steps):
        step["order"] = index + 1
    return steps


@operator(
    "assemble.sop.flow_template_detail",
    category="ASSEMBLE",
    description="Assemble one platform flow template with its resolved step list",
)
def flow_template_detail(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    template = args.get("template") if isinstance(args.get("template"), dict) else {}
    if not template:
        raise KeyError("SOP flow template 不存在")
    return {
        "template": template,
        "steps": [step for step in (args.get("steps") or []) if isinstance(step, dict)],
        "missing_nodes": [node_id for node_id in (args.get("missing_nodes") or []) if _text(node_id)],
    }


@operator(
    "assemble.sop.flow_detail",
    category="ASSEMBLE",
    description="Assemble one maker flow with its resolved document list and edges",
)
def flow_detail(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    flow = args.get("flow") if isinstance(args.get("flow"), dict) else {}
    if not flow:
        raise KeyError("SOP flow 不存在")
    items = [item for item in (args.get("items") or []) if isinstance(item, dict)]
    node_ids = {item.get("node_id") for item in items}
    edges = [
        edge
        for edge in (args.get("edges") or [])
        if isinstance(edge, dict)
        and _text(edge.get("from_node")) in node_ids
        and _text(edge.get("to_node")) in node_ids
    ]
    return {
        "flow": flow,
        "items": items,
        "edges": edges,
        "missing_nodes": [node_id for node_id in (args.get("missing_nodes") or []) if _text(node_id)],
    }


@operator(
    "assemble.sop.my_flow_cards",
    category="ASSEMBLE",
    description="Project a maker's own flows as my-flow cards",
)
def my_flow_cards(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    flows = [flow for flow in (args.get("flows") or []) if isinstance(flow, dict)]
    nodes_by_id = _node_index(args.get("nodes"))

    cards = []
    for flow in flows:
        steps = _resolve_steps(_normalise_refs(flow.get("node_refs")), nodes_by_id)
        description = _text(flow.get("description"))
        cards.append(
            {
                "id": _text(flow.get("id")),
                "name": _text(flow.get("name")),
                "summary": description.split("。")[0] if description else "",
                "description": description,
                "goal_id": flow.get("goal_id"),
                "category": "MY",
                "stages": sorted({step["stage"] for step in steps}),
                "step_count": len(steps),
                "doc_count": len(steps),
                "status": _text(flow.get("status")),
                "author_name": "我",
                "publisher_org": "私有流程",
                "is_official": False,
                "published_at": _text(flow.get("created_at")),
            }
        )
    cards.sort(key=lambda card: card["published_at"], reverse=True)
    return {"items": cards, "total": len(cards)}


@operator(
    "assemble.sop.node_context",
    category="ASSEMBLE",
    description="Assemble one workflow node with its children and prerequisite rationale",
)
def node_context(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    node = args.get("node") if isinstance(args.get("node"), dict) else {}
    if not node:
        raise KeyError(f"SOP node with ID {_text(args.get('node_id'))} not found")
    node_id = _text(node.get("id"))
    nodes_by_id = _node_index(args.get("nodes"))
    children = [
        nodes_by_id[child_id]
        for child_id in (node.get("children") or [])
        if _text(child_id) in nodes_by_id
    ]
    prerequisites = []
    for edge in args.get("edges") or []:
        if not isinstance(edge, dict) or _text(edge.get("to_node")) != node_id:
            continue
        if _text(edge.get("relation") or "prerequisite") == _OPTIONAL_EDGE:
            continue
        dependency = nodes_by_id.get(_text(edge.get("from_node")))
        if dependency is None:
            continue
        prerequisites.append(
            {
                "node_id": _text(dependency.get("id")),
                "name": _text(dependency.get("name")),
                "kind": _text(dependency.get("kind")) or NODE_DOCUMENT,
                "rationale": _text(edge.get("rationale")),
            }
        )
    return {"node": node, "children": children, "prerequisites": prerequisites}


@operator(
    "assemble.sop.review_queue",
    category="ASSEMBLE",
    description="Assemble the publish review queue with its status breakdown",
)
def review_queue(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    items = [item for item in (args.get("items") or []) if isinstance(item, dict)]
    all_items = [item for item in (args.get("all_items") or []) if isinstance(item, dict)]
    statuses = [_text(item.get("status")).upper() for item in all_items]
    items = sorted(items, key=lambda item: _text(item.get("submitted_at")), reverse=True)
    queue = {
        "items": items,
        "total": len(items),
        "pending": statuses.count(STATUS_PENDING_REVIEW),
        "approved": statuses.count(STATUS_APPROVED),
        "rejected": statuses.count(STATUS_REJECTED),
    }
    return {**queue, "response": dict(queue)}


@operator(
    "assemble.sop.review_submission_result",
    category="ASSEMBLE",
    description="Project one queued publish submission as the publish response",
)
def review_submission_result(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    submission = args.get("submission") or {}
    return {
        "review_submission": submission,
        "review_item": args.get("item") or {},
        "response": submission,
        "orchestrated_by": _text(params.get("pipeline")),
    }


@operator(
    "assemble.sop.review_result",
    category="ASSEMBLE",
    description="Project one processed review item as the review-queue process result",
)
def review_result(params: dict[str, Any], args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    item_id = _text(args.get("item_id"))
    status = _text(args.get("status"))
    target_type = _text(args.get("target_type"))
    target_id = _text(args.get("target_id"))
    note = _text(args.get("review_note"))
    published_id = _text(args.get("published_id"))
    title = _text(args.get("title"))

    processed = 1 if item_id and status else 0
    approved = 1 if status == STATUS_APPROVED else 0
    rejected = 1 if status == STATUS_REJECTED else 0
    published_documents = [target_id] if approved and target_type == TARGET_DOCUMENT and target_id else []
    published_flows = [target_id] if approved and target_type == TARGET_FLOW and target_id else []

    decision = {
        "item_id": item_id,
        "target_id": target_id,
        "target_type": target_type,
        "status": status,
        "review_note": note,
        "published_id": published_id,
    }
    summary = {
        "processed": processed,
        "approved": approved,
        "rejected": rejected,
        "published_documents": published_documents,
        "published_flows": published_flows,
        "details": (
            [{"item_id": item_id, "title": title, "status": status, "note": note}]
            if processed
            else []
        ),
        "review_decision": decision,
    }
    return {
        **summary,
        "response": dict(summary),
        "orchestrated_by": _text(params.get("pipeline")),
    }
