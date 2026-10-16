"""Policy radar service matching tax exemptions and subsidies."""
import uuid
from typing import Dict, List, Optional

from src.domains.policies.models import (
    PolicyResponse,
    PolicyMatchRequest,
    PolicyMatchResponse,
)


class PolicyService:
    """Manages government incentive policies and matches maker eligibility."""

    def __init__(self):
        self._policies: Dict[str, PolicyResponse] = {}
        self._seed_default_policies()

    def _seed_default_policies(self):
        p1 = PolicyResponse(
            id="pol_vat_exemption_2026",
            title="小规模纳税人月销售额 10 万以下（季度 30 万）免征增值税",
            policy_level="国家级",
            category="TAX",
            subsidy_amount_max=9000.0,
            summary="小规模纳税人合计月销售额未超过10万元（以1个季度为纳税期限的，季度销售额未超过30万元）的，免征增值税。",
            eligible_conditions=[
                "纳税主体为小规模纳税人（个体工商户或小微企业）",
                "单一季度累计销售额不超过人民币 300,000 元",
                "开具普通增值税发票",
            ],
            legal_basis="财政部 税务总局公告 2023年第12号",
        )

        p2 = PolicyResponse(
            id="pol_rnd_deduction_100",
            title="科技型中小微企业研发费用 100% 税前加计扣除",
            policy_level="国家级",
            category="TAX",
            subsidy_amount_max=150000.0,
            summary="科技型中小企业开展研发活动中实际发生的研发费用，未形成无形资产计入当期损益的，按规定据实扣除的基础上，自2023年1月1日起，再按照实际发生额的100%在税前加计扣除。",
            eligible_conditions=[
                "入库全国科技型中小企业信息库",
                "研发费用核算真实独立且符合加计扣除研发归集规范",
            ],
            legal_basis="财政部 税务总局 科技部公告 2023年第11号",
        )

        p3 = PolicyResponse(
            id="pol_ai_compute_voucher_hz",
            title="杭州高新区超级个体与小微人工智能算力券补贴",
            policy_level="省市级",
            category="SUBSIDY",
            subsidy_amount_max=50000.0,
            summary="为注册在本区开展大模型微调、生成式AI应用独立研发的创客主体，提供最高 30% 的实际算力消费抵扣凭据。",
            eligible_conditions=[
                "在杭州市高新技术产业园区完成注册登记",
                "采购指定合规公共算力服务平台算力资源",
            ],
            legal_basis="杭高新发〔2024〕18号 人工智能产业高质量发展支持政策",
        )

        for p in [p1, p2, p3]:
            self._policies[p.id] = p

    def list_policies(self, category: Optional[str] = None) -> List[PolicyResponse]:
        policies = list(self._policies.values())
        if category:
            policies = [p for p in policies if p.category == category]
        return policies

    def match_policies(self, req: PolicyMatchRequest) -> PolicyMatchResponse:
        """Evaluate maker income against policy thresholds and calculate tax savings."""
        matched: List[PolicyResponse] = []
        is_vat_free = req.quarterly_income <= 300000.0

        if is_vat_free:
            applicable_rate = 0.0
            tax_savings = req.quarterly_income * 0.03  # 3% standard small-scale rate
            explanation = f"恭喜！您本季度申报销售额 ¥{req.quarterly_income:,.2f} 未超过 30 万元免征红线，享受国家小规模纳税人增值税全额免征，预计直接减免税额 ¥{tax_savings:,.2f}。"
            matched.append(self._policies["pol_vat_exemption_2026"])
        else:
            applicable_rate = 0.03
            tax_savings = 0.0
            explanation = f"提示：您本季度申报销售额 ¥{req.quarterly_income:,.2f} 已超出 30 万元免税门槛，全额按 3% 简易计税缴纳增值税，应纳增值税额约 ¥{req.quarterly_income * 0.03:,.2f}。"

        # If Region is Hangzhou, add local AI compute voucher
        if "杭州" in req.region:
            matched.append(self._policies["pol_ai_compute_voucher_hz"])

        # Add R&D deduction
        matched.append(self._policies["pol_rnd_deduction_100"])

        return PolicyMatchResponse(
            eligible=is_vat_free,
            applicable_tax_rate=applicable_rate,
            estimated_tax_savings=tax_savings,
            legal_basis="财政部 税务总局公告 2023年第12号 及 相关扶持政策",
            matched_policies=matched,
            explanation=explanation,
        )


policy_service = PolicyService()
