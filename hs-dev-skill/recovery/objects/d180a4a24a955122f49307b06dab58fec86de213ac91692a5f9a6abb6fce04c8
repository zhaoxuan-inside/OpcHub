"""Models and Schemas for Ops Telemetry & Cross-Platform Metrics."""
from pydantic import BaseModel


class KpiMetric(BaseModel):
    label: str
    value: str | int | float
    delta_percent: float
    trend: str = "UP"  # UP or DOWN
    sub_text: str


class ModuleHeatmap(BaseModel):
    module_name: str
    code: str
    pv_count: int
    percentage: float
    color: str


class TerminalDistribution(BaseModel):
    ios_percentage: float = 46.2
    android_percentage: float = 35.8
    desktop_web_percentage: float = 18.0


class DailyTrendPoint(BaseModel):
    date: str
    pv: int
    uv: int
    dau: int


class GatewayLogRecord(BaseModel):
    id: str
    terminal: str
    route: str
    protocol: str
    latency_ms: int
    location: str
    status: str = "200 SUCCESS"


class OpsDashboardResponse(BaseModel):
    timestamp: str
    is_live: bool = True
    dau: KpiMetric
    uv: KpiMetric
    pv: KpiMetric
    mau: KpiMetric
    retention: KpiMetric
    api_throughput: KpiMetric
    daily_trends: list[DailyTrendPoint]
    module_heatmaps: list[ModuleHeatmap]
    terminal_distribution: TerminalDistribution
    recent_gateway_logs: list[GatewayLogRecord]
