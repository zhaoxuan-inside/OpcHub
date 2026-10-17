"""SOP Service managing workflow stages, document templates, and generated document instances."""
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from src.domains.sop.models import (
    SOPStage,
    SOPTemplate,
    SOPTemplateCreate,
    SOPTemplatesResponse,
    SOPDocumentCreate,
    SOPDocumentResponse,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SOPService:
    """Manages business registration and compliance document templates and generated instances."""

    def __init__(self):
        self._stages: List[SOPStage] = [
            SOPStage(
                stage=1,
                name="阶段 01: 主体定名与税种选型",
                code="STAGE_TAX_ENTITY",
                description="从个体工商户到一人有限责任公司的低税率架构选型与核名申请",
            ),
            SOPStage(
                stage=2,
                name="阶段 02: 银行基本户与发票授信",
                code="STAGE_BANK_INVOICE",
                description="开立企业级银行结算账户与申请小规模纳税人电子数电发票授信",
            ),
            SOPStage(
                stage=3,
                name="阶段 03: 软著申报与技术入库",
                code="STAGE_IP_COPYRIGHT",
                description="核心软件知识产权代码封包、软著加急通道与科技型中小企业入库",
            ),
            SOPStage(
                stage=4,
                name="阶段 04: 跨境结汇通道配置",
                code="STAGE_CROSS_BORDER",
                description="Stripe、Mercury、PingPong 等出海跨境资金安全合规收结汇",
            ),
        ]

        self._templates: Dict[str, SOPTemplate] = {}
        self._documents: Dict[str, SOPDocumentResponse] = {}

    def get_stages_and_templates(self) -> SOPTemplatesResponse:
        """Get all SOP stages and available active document templates."""
        return SOPTemplatesResponse(
            stages=self._stages,
            templates=list(self._templates.values()),
        )

    def get_template(self, template_id: str) -> SOPTemplate:
        """Fetch template by ID."""
        if template_id not in self._templates:
            raise KeyError(f"SOP template with ID {template_id} not found")
        return self._templates[template_id]

    def create_template(self, req: SOPTemplateCreate) -> SOPTemplate:
        """Create and register a new SOP compliance document template."""
        tid = f"tpl_{uuid.uuid4().hex[:8]}"
        template = SOPTemplate(
            id=tid,
            stage=req.stage,
            code=req.code,
            name=req.name,
            category=req.category,
            description=req.description,
            template_content=req.template_content,
            required_fields=req.required_fields,
            is_active=True,
        )
        self._templates[tid] = template
        return template

    def render_and_save_document(self, payload: SOPDocumentCreate) -> SOPDocumentResponse:
        """Render document template with maker input data and persist instance to backend."""
        template = self.get_template(payload.template_id)
        
        # Merge defaults and inputs
        merged_data: Dict[str, Any] = {}
        for field in template.required_fields:
            val = payload.form_data.get(field.key, field.default or "")
            merged_data[field.key] = val

        # Extra dynamic fields
        merged_data["verify_serial"] = "VER-" + uuid.uuid4().hex[:12].upper()

        # Render template content safely
        try:
            rendered = template.template_content.format(**merged_data)
        except Exception:
            # Fallback simple replacement if formatting tags fail
            rendered = template.template_content
            for k, v in merged_data.items():
                rendered = rendered.replace(f"{{{k}}}", str(v))

        doc_id = str(uuid.uuid4())
        now = utc_now_iso()
        company = merged_data.get("company_name", "创客主体")
        doc_title = f"{template.name} - {company}"

        document = SOPDocumentResponse(
            id=doc_id,
            template_id=template.id,
            user_id=payload.user_id,
            document_title=doc_title,
            form_data=merged_data,
            rendered_content=rendered,
            compliance_passed=True,
            status="READY",
            created_at=now,
            updated_at=now,
        )

        self._documents[doc_id] = document
        return document

    def get_document(self, doc_id: str) -> SOPDocumentResponse:
        """Retrieve persisted document by ID."""
        if doc_id not in self._documents:
            raise KeyError(f"SOP document with ID {doc_id} not found")
        return self._documents[doc_id]

    def list_documents(self, user_id: Optional[str] = None) -> List[SOPDocumentResponse]:
        """List persisted documents, optionally filtered by maker user_id."""
        docs = list(self._documents.values())
        if user_id:
            docs = [d for d in docs if d.user_id == user_id]
        docs.sort(key=lambda d: d.created_at, reverse=True)
        return docs

    def delete_document(self, doc_id: str) -> bool:
        """Physically delete persisted document by ID for Saga rollback."""
        if doc_id in self._documents:
            del self._documents[doc_id]
            return True
        return False


sop_service = SOPService()

