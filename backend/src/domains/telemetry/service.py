"""Telemetry calculation and query service."""
from datetime import datetime, timezone
from .models import (
    OpsDashboardResponse, KpiMetric, DailyTrendPoint, ModuleHeatmap,
    TerminalDistribution, GatewayLogRecord
)


class TelemetryService:
    """Provides operational metrics for Web, iOS, and Android clients."""

    def get_dashboard_metrics(self) -> OpsDashboardResponse:
        now_iso = datetime.now(timezone.utc).isoformat()
        return OpsDashboardResponse(
            timestamp=now_iso,
            is_live=True,
            dau=KpiMetric(
                label="DAU 日活跃创客",
                value="14,820",
                delta_percent=12.4,
                trend="UP",
                sub_text="昨日: 13,180 · 峰值: 16.9k"
            ),
            uv=KpiMetric(
                label="UV 今日独立访客",
                value="89,540",
                delta_percent=18.6,
                trend="UP",
                sub_text="移动端 68.4% · 网页 31.6%"
            ),
            pv=KpiMetric(
                label="PV 页面总浏览量",
                value="628,300",
                delta_percent=24.1,
                trend="UP",
                sub_text="人均 7.01 页 · 停留 9.4m"
            ),
            mau=KpiMetric(
                label="MAU 月活创客数",
                value="182,450",
                delta_percent=8.2,
                trend="UP",
                sub_text="长三角独立创客渗透 41%"
            ),
            retention=KpiMetric(
                label="次日 / 7日留存率",
                value="64.2% / 48.5%",
                delta_percent=4.82,
                trend="UP",
                sub_text="黑钻会员 4,316 人 (¥32.8万)"
            ),
            api_throughput=KpiMetric(
                label="微内核 API 吞吐",
                value="12.8M 次/日",
                delta_percent=0.0,
                trend="UP",
                sub_text="48 条活跃热载 DAG 链路 · P99: 28ms"
            ),
            daily_trends=[
                DailyTrendPoint(date="10-10", pv=420000, uv=62000, dau=11200),
                DailyTrendPoint(date="10-11", pv=460000, uv=68000, dau=11800),
                DailyTrendPoint(date="10-12", pv=510000, uv=74000, dau=12600),
                DailyTrendPoint(date="10-13", pv=550000, uv=79000, dau=13400),
                DailyTrendPoint(date="10-14", pv=580000, uv=83000, dau=14100),
                DailyTrendPoint(date="10-15", pv=610000, uv=86000, dau=14500),
                DailyTrendPoint(date="10-16", pv=628300, uv=89540, dau=14820),
            ],
            module_heatmaps=[
                ModuleHeatmap(module_name="政策雷达", code="POLICY", pv_count=201000, percentage=32.0, color="#0071E3"),
                ModuleHeatmap(module_name="流程文书SOP", code="SOP", pv_count=163300, percentage=26.0, color="#34C759"),
                ModuleHeatmap(module_name="创客贴吧", code="FORUM", pv_count=113000, percentage=18.0, color="#FF9500"),
                ModuleHeatmap(module_name="需求外包集市", code="MARKET", pv_count=87900, percentage=14.0, color="#AF52DE"),
                ModuleHeatmap(module_name="算力与特权", code="PERKS", pv_count=62800, percentage=10.0, color="#5AC8FA"),
            ],
            terminal_distribution=TerminalDistribution(
                ios_percentage=46.2,
                android_percentage=35.8,
                desktop_web_percentage=18.0
            ),
            recent_gateway_logs=[
                GatewayLogRecord(
                    id="log_001",
                    terminal="iOS Client",
                    route="/api/v1/policy/recommend.match",
                    protocol="HTTP/3 GET",
                    latency_ms=14,
                    location="浙江省杭州市 (高新节点)",
                    status="200 SUCCESS"
                ),
                GatewayLogRecord(
                    id="log_002",
                    terminal="Android Client",
                    route="/api/v1/forum/threads/hot_digest",
                    protocol="HTTP/2 GET",
                    latency_ms=9,
                    location="上海市浦东新区",
                    status="200 SUCCESS"
                ),
                GatewayLogRecord(
                    id="log_003",
                    terminal="Desktop Web",
                    route="/api/v1/kernel/dag/execute.tax",
                    protocol="HTTP/2 POST",
                    latency_ms=28,
                    location="江苏省苏州市工业园区",
                    status="200 SUCCESS"
                ),
                GatewayLogRecord(
                    id="log_004",
                    terminal="iOS Client",
                    route="/api/v1/demands/leads.subscribe",
                    protocol="HTTP/3 GET",
                    latency_ms=12,
                    location="广东省深圳市南山区",
                    status="200 SUCCESS"
                ),
            ]
        )


telemetry_service = TelemetryService()
