"""Compliance Service managing legal provisions (法条) and pitfall cases (避坑案例).

数据、配置、代码三分离：
- 数据（Data）: backend/data/seeds/compliance.json —— 法条 / 案例 全部持久化至 PostgreSQL
  (domain_snapshots JSONB)，运行时通过 hydrate 从数据库重建索引。
- 配置（Config）: backend/config/application.yaml `compliance` 段 —— 评分阈值等参数化。
- 代码（Code）: 本服务仅承担加载、索引、发布与查询逻辑，零业务数据硬编码。
"""
import json
import logging
import uuid
from pathlib import Path
from typing import List

from src.core.config import settings
from src.domains.compliance.models import (
    ComplianceLaw,
    ComplianceCase,
    CompliancePublishRequest,
    AuditCheckItem,
    AuditEvaluateRequest,
    AuditReportResponse,
)
from src.infrastructure.database.persistence import domain_persistence

logger = logging.getLogger("opchub.compliance")


def _load_compliance_seeds() -> dict:
    """Load compliance knowledge base (laws / cases / checkpoints) from external data file."""
    search_paths = [
        Path("backend/data/seeds/compliance.json"),
        Path("data/seeds/compliance.json"),
        Path(__file__).resolve().parent.parent.parent.parent / "data" / "seeds" / "compliance.json",
    ]
    for p in search_paths:
        if p.is_file():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Failed to load compliance seeds from %s: %s", p, e)
    return {}


DEFAULT_COMPLIANCE_SEEDS: dict = _load_compliance_seeds()


class ComplianceService:
    """Provides compliance legal knowledge, pitfall cases and (legacy) self-audit checklists."""

    def __init__(self):
        self._laws: List[ComplianceLaw] = []
        self._cases: List[ComplianceCase] = []
        self._checkpoints: List[AuditCheckItem] = []
        self._init_seeds()

    def _init_seeds(self) -> None:
        """Initialize in-memory catalog from external data seeds and queue DB persistence."""
        for data in DEFAULT_COMPLIANCE_SEEDS.get("laws", []):
            data = dict(data)
            # Seed laws/cases are platform-curated legal knowledge → official.
            data.setdefault("is_official", True)
            data.setdefault("author_name", "官方发布")
            law = ComplianceLaw(**data)
            if not any(l.id == law.id for l in self._laws):
                self._laws.append(law)
                self._persist("law", law)
        for data in DEFAULT_COMPLIANCE_SEEDS.get("cases", []):
            data = dict(data)
            data.setdefault("is_official", True)
            data.setdefault("author_name", "官方发布")
            case = ComplianceCase(**data)
            if not any(c.id == case.id for c in self._cases):
                self._cases.append(case)
                self._persist("case", case)
        for data in DEFAULT_COMPLIANCE_SEEDS.get("checkpoints", []):
            chk = AuditCheckItem(**data)
            if not any(c.id == chk.id for c in self._checkpoints):
                self._checkpoints.append(chk)
                self._persist("checkpoint", chk)

    @staticmethod
    def _persist(kind: str, entity: object) -> None:
        """Persist a compliance entity with an explicit kind marker for DB rebuild."""
        doc = dict(entity.model_dump(mode="json"))
        doc["_kind"] = kind
        domain_persistence.write_raw("compliance.items", str(entity.id), doc)

    # ---------------------------------------------------------------- read
    def get_laws(self) -> List[ComplianceLaw]:
        return self._laws

    def get_cases(self) -> List[ComplianceCase]:
        return self._cases

    def get_checkpoints(self) -> List[AuditCheckItem]:
        return self._checkpoints

    # Backward-compatible alias (existing callers / telemetry)
    def get_dimensions(self) -> List[ComplianceLaw]:
        return self._laws

    # ---------------------------------------------------------------- publish
    def publish_entry(self, payload: dict) -> dict:
        """Publish a new legal provision (kind=law) or pitfall case (kind=case).

        登录用户即可发布：写入内存索引并持久化至 PostgreSQL。
        """
        req = payload if isinstance(payload, CompliancePublishRequest) else CompliancePublishRequest(**payload)
        if req.kind == "law":
            entity_id = req.id or f"law_{uuid.uuid4().hex[:8]}"
            law = ComplianceLaw(
                id=entity_id,
                code=req.code or f"LAW-{uuid.uuid4().hex[:4].upper()}",
                name=req.name,
                title=req.title,
                summary=req.summary or req.title,
                content=req.content,
                level=req.level or "国家级",
                issuer=req.issuer,
                published_at=req.published_at,
                penalties=req.penalties,
                law_ref=req.law_ref,
                icon_name=req.icon_name or "shield",
                hot_score=0,
                author_id=req.author_id,
                author_name=req.author_name,
                is_official=req.is_official,
            )
            if not any(l.id == law.id for l in self._laws):
                self._laws.append(law)
                self._persist("law", law)
            return law.model_dump(mode="json")

        if req.kind == "case":
            entity_id = req.id or f"case_{uuid.uuid4().hex[:8]}"
            case = ComplianceCase(
                id=entity_id,
                title=req.title,
                badge=req.badge or "新增避坑案例",
                industry=req.industry or "综合行业",
                violation=req.violation,
                consequence=req.consequence,
                lesson=req.lesson,
                badge_color=req.badge_color or "#5B6472",
                hot_score=0,
                author_id=req.author_id,
                author_name=req.author_name,
                is_official=req.is_official,
            )
            if not any(c.id == case.id for c in self._cases):
                self._cases.append(case)
                self._persist("case", case)
            return case.model_dump(mode="json")

        raise ValueError(f"Unsupported compliance publish kind: {req.kind}")

    def delete_entry(self, kind: str, entity_id: str) -> bool:
        """Physically remove a published law/case (Saga compensation)."""
        kind = str(kind or "").strip().lower()
        eid = str(entity_id or "")
        if not eid:
            return False
        if kind == "law":
            before = len(self._laws)
            self._laws = [l for l in self._laws if l.id != eid]
            deleted = len(self._laws) < before
        elif kind == "case":
            before = len(self._cases)
            self._cases = [c for c in self._cases if c.id != eid]
            deleted = len(self._cases) < before
        else:
            return False
        if deleted:
            domain_persistence.delete("compliance.items", eid)
        return deleted

    # ---------------------------------------------------------------- audit (legacy backend capability)
    def evaluate_audit(self, req: AuditEvaluateRequest) -> AuditReportResponse:
        passed_set = set(req.passed_item_ids)
        total_weight = sum(item.weight for item in self._checkpoints)
        earned_weight = sum(item.weight for item in self._checkpoints if item.id in passed_set)

        score = int(round((earned_weight / total_weight) * 100)) if total_weight > 0 else 0
        failed_items = [item for item in self._checkpoints if item.id not in passed_set]

        if score >= settings.compliance_grade_excellent:
            grade = "EXCELLENT"
        elif score >= settings.compliance_grade_good:
            grade = "GOOD"
        elif score >= settings.compliance_grade_warning:
            grade = "WARNING"
        else:
            grade = "CRITICAL"

        suggestions = [item.advice for item in failed_items]
        legal_help_needed = None
        if failed_items:
            # Generate tailored demand recommendation
            legal_help_needed = f"检测到 {len(failed_items)} 个合规风险点（特别是 {failed_items[0].title}），建议前往需求集市发布专项法律求助或咨询法务服务商。"

        return AuditReportResponse(
            score=score,
            grade=grade,
            total_items=len(self._checkpoints),
            passed_items_count=len(self._checkpoints) - len(failed_items),
            failed_items_count=len(failed_items),
            risk_items=failed_items,
            remedy_suggestions=suggestions,
            legal_help_recommendation=legal_help_needed,
        )

    # ---------------------------------------------------------------- hydration
    def hydrate_items(self, rows: List[dict]) -> int:
        """Rebuild in-memory indexes from persisted PostgreSQL snapshots (restart durability)."""
        if rows:
            for r in rows:
                kind = r.get("_kind") or _infer_entity_kind(r)
                if kind == "law":
                    law = ComplianceLaw(**r)
                    if not any(l.id == law.id for l in self._laws):
                        self._laws.append(law)
                elif kind == "case":
                    case = ComplianceCase(**r)
                    if not any(c.id == case.id for c in self._cases):
                        self._cases.append(case)
                elif kind == "checkpoint":
                    chk = AuditCheckItem(**r)
                    if not any(c.id == chk.id for c in self._checkpoints):
                        self._checkpoints.append(chk)
            return len(rows)
        # If DB is empty, persist baseline seeds to PostgreSQL snapshots
        self._init_seeds()
        return len(self._laws) + len(self._cases) + len(self._checkpoints)

    def clear(self) -> None:
        """Reset compliance catalog for isolated testing."""
        self._laws.clear()
        self._cases.clear()
        self._checkpoints.clear()


def _infer_entity_kind(row: dict) -> str:
    """Infer persisted entity kind from its payload shape."""
    if "content" in row and "law_ref" in row:
        return "law"
    if "lesson" in row and "consequence" in row:
        return "case"
    if "weight" in row and "legal_basis" in row:
        return "checkpoint"
    return "law"


compliance_service = ComplianceService()

domain_persistence.register("compliance.items", compliance_service.hydrate_items)
