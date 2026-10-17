"""Data models for Unified Inbound Gateway Dispatcher."""
from typing import Any, Optional, Dict
from pydantic import BaseModel, Field


class DispatchRequest(BaseModel):
    """Unified inbound request for all business scenarios with code/protocol versioning."""
    scenario: str = Field(
        ...,
        min_length=2,
        description="业务场景标识，如 'products.list', 'products.publish', 'policies.match' 等"
    )
    version: str = Field(
        default="v1.0.0",
        description="代码/协议版本号 (如 'v1.0.0', 'v1.0.4', 'v2.0.0-beta')"
    )
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="业务请求参数负载"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="调用上下文 (如 user_id, client, trace_id 等)"
    )


class DispatchResponse(BaseModel):
    """Standardized response envelope returned by the unified dispatcher."""
    code: int = 200
    scenario: str
    version: str = "v1.0.0"
    message: str = "success"
    data: Any = None
    trace_id: str
    timestamp: str
    duration_ms: float = 0.0


class RouteRuleDescriptor(BaseModel):
    """Metadata describing a registered scenario route rule."""
    scenario: str
    version: str = "v1.0.0"
    domain: str
    description: str
    is_async: bool = True
