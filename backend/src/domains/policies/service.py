"""Policy radar service matching tax exemptions and subsidies."""
import uuid
from typing import Dict, List, Optional

from src.domains.policies.models import (
    PolicyCreate,
    PolicyResponse,
    PolicyMatchRequest,
    PolicyMatchResponse,
)


class PolicyService:
    """Manages government incentive policies and matches maker eligibility."""

    def __init__(self):
        self._policies: Dict[str, PolicyResponse] = {}

    def list_policies(self, category: Optional[str] = None) -> List[PolicyResponse]:
        policies = list(self._policies.values())
        if category:
            policies = [p for p in policies if p.category == category]
        return policies

    def create_policy(self, req: PolicyCreate) -> PolicyResponse:
        """Create and publish a new government policy/subsidy rule."""
        pid = f"pol_{uuid.uuid4().hex[:8]}"
        policy = PolicyResponse(
            id=pid,
            title=req.title,
            policy_level=req.policy_level,
            category=req.category,
            subsidy_amount_max=req.subsidy_amount_max,
            summary=req.summary,
            eligible_conditions=req.eligible_conditions,
            legal_basis=req.legal_basis,
        )
        self._policies[pid] = policy
        return policy

    def match_policies(self, req: PolicyMatchRequest) -> PolicyMatchResponse:
        """Evaluate maker income against policy thresholds and calculate tax savings with semantic relevance ranking."""
        matched: List[PolicyResponse] = []
        is_vat_free = req.quarterly_income <= 300000.0

        if is_vat_free:
            applicable_rate = 0.0
            tax_savings = req.quarterly_income * 0.03  # 3% standard small-scale rate
            explanation = f"恭喜！您本季度申报销售额 ¥{req.quarterly_income:,.2f} 未超过 30 万元免征红线，享受国家小规模纳税人增值税全额免征，预计直接减免税额 ¥{tax_savings:,.2f}。"
            if "pol_vat_exemption_2026" in self._policies:
                matched.append(self._policies["pol_vat_exemption_2026"])
        else:
            applicable_rate = 0.03
            tax_savings = 0.0
            explanation = f"提示：您本季度申报销售额 ¥{req.quarterly_income:,.2f} 已超出 30 万元免税门槛，全额按 3% 简易计税缴纳增值税，应纳增值税额约 ¥{req.quarterly_income * 0.03:,.2f}。"

        # If Region is Hangzhou, add local AI compute voucher
        if "杭州" in req.region and "pol_ai_compute_voucher_hz" in self._policies:
            matched.append(self._policies["pol_ai_compute_voucher_hz"])

        # Add R&D deduction
        if "pol_rnd_deduction_100" in self._policies:
            matched.append(self._policies["pol_rnd_deduction_100"])

        # Semantic & Keyword Matching against all policies
        relevance_scores: dict[str, float] = {}
        all_policies = list(self._policies.values())

        search_tokens = set()
        if req.search_query:
            for part in req.search_query.replace("，", " ").replace(",", " ").replace("、", " ").split():
                if len(part) >= 2:
                    search_tokens.add(part.lower())
        if req.industry_keywords:
            for kw in req.industry_keywords:
                search_tokens.add(kw.strip().lower())

        for p in all_policies:
            score = 0.5  # Baseline score
            if is_vat_free and p.category == "TAX":
                score += 0.3
            if "杭州" in req.region and ("杭州" in p.title or "杭州" in p.summary):
                score += 0.2

            if search_tokens:
                text_corpus = (f"{p.title} {p.summary} {' '.join(p.eligible_conditions)} {p.legal_basis}").lower()
                matched_tokens = [tok for tok in search_tokens if tok in text_corpus]
                if matched_tokens:
                    score += 0.4 * (len(matched_tokens) / len(search_tokens))
                    if p not in matched:
                        matched.append(p)

            relevance_scores[p.id] = min(1.0, round(score, 2))

        # Sort matched policies by relevance score descending
        matched.sort(key=lambda x: (relevance_scores.get(x.id, 0.0), x.subsidy_amount_max), reverse=True)

        return PolicyMatchResponse(
            eligible=is_vat_free,
            applicable_tax_rate=applicable_rate,
            estimated_tax_savings=tax_savings,
            legal_basis="财政部 税务总局公告 2023年第12号 及 相关扶持政策",
            matched_policies=matched,
            explanation=explanation,
            relevance_scores=relevance_scores,
        )


    def delete_policy(self, policy_id: str) -> bool:
        """Physically delete policy for Saga reverse compensation."""
        if policy_id in self._policies:
            del self._policies[policy_id]
            return True
        return False

    def clear(self) -> None:
        """Reset policies for isolated testing."""
        self._policies.clear()


policy_service = PolicyService()
