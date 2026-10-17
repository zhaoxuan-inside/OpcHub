"""SOP Service managing workflow stages, document templates, and generated document instances."""
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from src.domains.sop.models import (
    SOPStage,
    SOPField,
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

        self._seed_default_templates()

    def _seed_default_templates(self):
        """Seed predefined standard government and bank document templates."""
        t1 = SOPTemplate(
            id="tpl_individual_biz_reg",
            stage=1,
            code="INDIVIDUAL_BIZ_REG",
            name="个体工商户设立登记标准申请书",
            category="TAX",
            description="符合全国政务标准的个体户开办材料，支持商务秘书集群托管地址与增值税季度30万免征申报。",
            template_content="""个体工商户设立登记申请书
---------------------------------------------
登记机关：{registration_office}
主体全称：{company_name}
经营者：{founder_name}
出资资金：人民币 {capital_cny} 元整
经营场所：{address_type}
主营范围：{biz_scope}

申报承诺：
本人保证所提交的身份证明文件、经营场所证明及申报材料真实、合法、有效，
且承诺严格遵从《个体工商户财务制度》及小微纳税人免税合规管理规约。
---------------------------------------------
[电子印签] 状态: READY FOR SUBMISSION
核验流水号: {verify_serial}""",
            required_fields=[
                SOPField(key="company_name", label="拟定经营主体字号 / 全称", default="极客视界（杭州）信息技术工作室"),
                SOPField(key="founder_name", label="法定代表创客姓名及身份证", default="赵玄 (33010619920101XXXX)"),
                SOPField(key="biz_scope", label="主营经营范围描述", default="软件开发；信息技术咨询服务；人工智能应用软件开发"),
                SOPField(
                    key="address_type",
                    label="注册地址类型",
                    type="select",
                    options=[
                        "集群租赁商务秘书地址 (免实际租赁)",
                        "自有/承租独立办公研发场地合同",
                        "科技孵化器集中托管工位",
                    ],
                    default="集群租赁商务秘书地址 (免实际租赁)",
                ),
                SOPField(key="capital_cny", label="出资金额(元)", default="100,000"),
                SOPField(key="registration_office", label="登记市场监管部门", default="杭州市市场监督管理局高新区分局"),
            ],
        )

        t2 = SOPTemplate(
            id="tpl_opc_charter",
            stage=1,
            code="OPC_CHARTER",
            name="一人有限责任公司章程与股东决定",
            category="LEGAL",
            description="标准《中华人民共和国公司法》单人独资设立章程，明确财产独立与股东有限责任隔离。",
            template_content="""{company_name} 章程（一人有限公司）
---------------------------------------------
第一条 公司名称：{company_name}
第二条 住所地址：{address_type}
第三条 注册资本：人民币 {capital_cny} 元整
第四条 股东姓名：{founder_name}（持有 100% 股权）
第五条 经营范围：{biz_scope}

第六条 财务财产独立性声明：
股东保证公司财产独立于股东个人财产，建立规范完整的独立会计账簿，
依法承担以其认缴的出资额为限对公司承担的有限责任。
---------------------------------------------
唯一股东签署：{founder_name}""",
            required_fields=[
                SOPField(key="company_name", label="一人公司全称", default="极客视界（杭州）科技有限公司"),
                SOPField(key="founder_name", label="独资股东姓名", default="赵玄"),
                SOPField(key="capital_cny", label="注册资本(元)", default="500,000"),
                SOPField(key="biz_scope", label="公司经营范围", default="人工智能算力服务；信息技术咨询"),
                SOPField(key="address_type", label="公司注册住所", default="杭州市高新技术产业园区集群登记地址"),
            ],
        )

        t3 = SOPTemplate(
            id="tpl_soft_copyright",
            stage=3,
            code="SOFT_COPYRIGHT",
            name="计算机软件著作权登记申请鉴别材料",
            category="IP",
            description="中国版权保护中心标准软著申请表与前后连续30页源码鉴别封包说明书。",
            template_content="""计算机软件著作权登记申请表
---------------------------------------------
软件全称：{software_name}
软件简称：{software_short_name}
版本号：{software_version}
著作权人：{company_name}
开发完成日期：{complete_date}
主要功能概述：{feature_summary}
源代码鉴别行数：连续前 30 页及后 30 页，共计 3,000 行
---------------------------------------------
版权代理核验状态：PASS""",
            required_fields=[
                SOPField(key="company_name", label="著作权申请主体", default="极客视界（杭州）信息技术工作室"),
                SOPField(key="software_name", label="软件全称", default="OpcHub 微内核编排执行引擎软件"),
                SOPField(key="software_short_name", label="软件简称", default="OpcHub-Kernel"),
                SOPField(key="software_version", label="软件版本号", default="V1.0.0"),
                SOPField(key="complete_date", label="开发完成日期", default="2026-10-15"),
                SOPField(key="feature_summary", label="核心技术特征", default="基于有向无环图的高并发算子微内核与轻量AST沙箱执行系统"),
            ],
        )

        t4 = SOPTemplate(
            id="tpl_cross_border_fx",
            stage=4,
            code="CROSS_BORDER_FX",
            name="跨境收结汇贸易真实性承诺与备案书",
            category="FINANCE",
            description="适用于中国银行或跨境支付通道（PingPong/Stripe）的软件出口真实性备案与还原申报。",
            template_content="""跨境电商及软件服务出口收结汇真实性承诺书
---------------------------------------------
备案企业：{company_name}
法定代表人：{founder_name}
结汇合作银行 / 机构：{settlement_channel}
业务模式：独立开发者自研 SaaS / 软件出海订阅收款
主要服务市场：北美、欧洲、东南亚

承诺事项：
本创客主体承诺所办理的跨境资金收结汇具有真实、合法的服务贸易背景，
单笔收结汇资金与海外应用商城 / SaaS平台订阅结算流水一一对应。
---------------------------------------------
承诺主体公章/签名：{founder_name}""",
            required_fields=[
                SOPField(key="company_name", label="出海主体名称", default="极客视界（杭州）信息技术工作室"),
                SOPField(key="founder_name", label="法人创客姓名", default="赵玄"),
                SOPField(key="settlement_channel", label="结汇渠道", default="Stripe / PingPong 跨境资金通道"),
            ],
        )

        for t in [t1, t2, t3, t4]:
            self._templates[t.id] = t

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

