"""Demands service managing corporate outsourcing requirements and maker bids."""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from src.domains.demands.models import (
    DemandCreate,
    DemandResponse,
    BidCreate,
    BidResponse,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DemandService:
    """Manages demands and bids."""

    def __init__(self):
        self._demands: Dict[str, DemandResponse] = {}
        self._bids: Dict[str, List[BidResponse]] = {}
        self._seed_default_demands()

    def _seed_default_demands(self):
        now = datetime.now(timezone.utc)
        items = [
            (
                "出海独立站多语言 SEO 与 Stripe 支付接入",
                "需要资深独立全栈创客，完成 Shopify / Next.js 独立站的全球 CDN 部署与多币种结汇通道打通。",
                18000.0,
                "DEV",
                7,
                "usr_client_corp_101",
            ),
            (
                "企业内网私有化 DeepSeek-R1 编排微内核部署",
                "基于 Ollama 与 vLLM 搭建内网知识库 RAG 检索问答系统，要求输出 DAG 拓扑执行链。",
                35000.0,
                "AI",
                14,
                "usr_client_corp_102",
            ),
            (
                "小微科技企业增值税零申报全套代办与合规辅导",
                "个体工商户季度 30 万以下免税申报代办，输出标准完税证明与财务留痕文件。",
                3000.0,
                "TAX",
                3,
                "usr_client_corp_103",
            ),
            (
                "出海独立 SaaS 平台隐私协议与 GDPR 合规审查求助",
                "寻求资深涉外法务或合规律师，起草符合欧盟 GDPR 与美区 CCPA 标准的隐私政策、服务条款及用户数据出境评估报告。",
                12000.0,
                "LEGAL",
                5,
                "usr_client_corp_104",
            ),
            (
                "生成式 AI 算法备案与大模型境内上线合规辅导",
                "针对平台接入的 LLM 智能体及文书生成服务，辅导完成网信办生成式人工智能服务上线备案与算法安全自评估报告。",
                18000.0,
                "LEGAL",
                10,
                "usr_client_corp_105",
            ),
        ]
        for title, desc, budget, cat, days, creator in items:
            did = str(uuid.uuid4())
            deadline = (now + timedelta(days=days)).isoformat()
            self._demands[did] = DemandResponse(
                id=did,
                creator_id=creator,
                title=title,
                description=desc,
                budget_cny=budget,
                category=cat,
                bidders_count=2,
                status="OPEN",
                deadline_at=deadline,
                created_at=now.isoformat(),
            )
            self._bids[did] = []

    def create_demand(self, payload: DemandCreate) -> DemandResponse:
        did = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        deadline = (now + timedelta(days=payload.deadline_days)).isoformat()
        demand = DemandResponse(
            id=did,
            creator_id=payload.creator_id,
            title=payload.title,
            description=payload.description,
            budget_cny=payload.budget_cny,
            category=payload.category,
            bidders_count=0,
            status="OPEN",
            deadline_at=deadline,
            created_at=now.isoformat(),
        )
        self._demands[did] = demand
        self._bids[did] = []
        return demand

    def list_demands(self, category: Optional[str] = None) -> List[DemandResponse]:
        demands = list(self._demands.values())
        if category:
            demands = [d for d in demands if d.category == category]
        demands.sort(key=lambda d: d.created_at, reverse=True)
        return demands

    def submit_bid(self, demand_id: str, payload: BidCreate) -> BidResponse:
        if demand_id not in self._demands:
            raise KeyError(f"Demand {demand_id} not found")
        demand = self._demands[demand_id]

        bid_id = str(uuid.uuid4())
        now = utc_now_iso()
        bid = BidResponse(
            id=bid_id,
            demand_id=demand_id,
            bidder_id=payload.bidder_id,
            bid_amount_cny=payload.bid_amount_cny,
            delivery_days=payload.delivery_days,
            proposal_text=payload.proposal_text,
            status="SUBMITTED",
            created_at=now,
        )
        if demand_id not in self._bids:
            self._bids[demand_id] = []
        self._bids[demand_id].append(bid)
        demand.bidders_count += 1
        return bid


demand_service = DemandService()
