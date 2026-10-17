"""Telemetry calculation and query service.

Aggregates real platform metrics from live domain services.
Metrics without a real data source (DAU/UV/PV/MAU/retention/throughput) return 0,
never fabricated numbers.
"""
from datetime import datetime, timezone
from .models import (
    OpsDashboardResponse, KpiMetric, DailyTrendPoint, ModuleHeatmap,
    TerminalDistribution
)


class TelemetryService:
    """Provides operational metrics aggregated from live platform state."""

    def get_dashboard_metrics(self) -> OpsDashboardResponse:
        """Aggregate real operational metrics from domain services.

        KPIs without an instrumentation source report 0; module heatmaps are
        derived from live record counts so the dashboard always reflects
        real platform state instead of hardcoded demo numbers.
        """
        # Gather live record counts from domain services (zero-coupling: import
        # inside method to avoid import cycles at module load time).
        from src.domains.forum.service import forum_service
        from src.domains.products.service import product_service
        from src.domains.policies.service import policy_service
        from src.domains.demands.service import demand_service
        from src.domains.perks.service import perk_service
        from src.domains.sop.service import sop_service
        from src.domains.compliance.service import compliance_service
        from src.domains.user.service import user_service

        forum_count = len(forum_service.list_threads())
        product_count = len(product_service.list_products())
        policy_count = len(policy_service.list_policies())
        demand_count = len(demand_service.list_demands())
        perk_count = len(perk_service.list_perks())
        sop_template_count = len(sop_service.get_stages_and_templates().templates)
        compliance_count = len(compliance_service.get_dimensions())
        maker_count = len([
            u for u in user_service._users_by_uid.values() if u.get("role") != "GUEST"
        ])

        module_counts = [
            ("政策雷达", "POLICY", policy_count),
            ("流程文书SOP", "SOP", sop_template_count),
            ("头脑风暴", "FORUM", forum_count),
            ("需求外包集市", "MARKET", demand_count),
            ("产品橱窗", "GALLERY", product_count),
            ("算力与特权", "PERKS", perk_count),
            ("合规指南", "COMPLIANCE", compliance_count),
        ]
        total_count = sum(c for _, _, c in module_counts) or 1

        module_heatmaps = [
            ModuleHeatmap(
                module_name=name,
                code=code,
                pv_count=count,
                percentage=round(count / total_count * 100.0, 1) if count else 0.0,
                color="#0071E3",
            )
            for name, code, count in module_counts
            if count > 0
        ]

        now_iso = datetime.now(timezone.utc).isoformat()
        return OpsDashboardResponse(
            timestamp=now_iso,
            is_live=True,
            dau=KpiMetric(
                label="DAU 日活跃创客",
                value="0",
                delta_percent=0.0,
                trend="UP",
                sub_text="暂无埋点数据源，等待接入真实统计",
            ),
            uv=KpiMetric(
                label="UV 今日独立访客",
                value="0",
                delta_percent=0.0,
                trend="UP",
                sub_text="暂无埋点数据源，等待接入真实统计",
            ),
            pv=KpiMetric(
                label="PV 页面总浏览量",
                value="0",
                delta_percent=0.0,
                trend="UP",
                sub_text="暂无埋点数据源，等待接入真实统计",
            ),
            mau=KpiMetric(
                label="MAU 月活创客数",
                value="0",
                delta_percent=0.0,
                trend="UP",
                sub_text="暂无埋点数据源，等待接入真实统计",
            ),
            retention=KpiMetric(
                label="次日 / 7日留存率",
                value="0% / 0%",
                delta_percent=0.0,
                trend="UP",
                sub_text="暂无埋点数据源，等待接入真实统计",
            ),
            api_throughput=KpiMetric(
                label="微内核 API 吞吐",
                value="0 次/日",
                delta_percent=0.0,
                trend="UP",
                sub_text="暂无埋点数据源，等待接入真实统计",
            ),
            daily_trends=[
                DailyTrendPoint(
                    date=datetime.now(timezone.utc).strftime("%m-%d"),
                    pv=0,
                    uv=0,
                    dau=maker_count,
                )
            ],
            module_heatmaps=module_heatmaps,
            terminal_distribution=TerminalDistribution(
                ios_percentage=0.0,
                android_percentage=0.0,
                desktop_web_percentage=0.0,
            ),
            recent_gateway_logs=[],
        )


telemetry_service = TelemetryService()
