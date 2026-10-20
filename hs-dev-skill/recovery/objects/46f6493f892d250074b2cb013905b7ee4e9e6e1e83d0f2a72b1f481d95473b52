# 任务上下文信息包：TASK-007

- **任务编号**：`TASK-007`
- **任务名称**：低代码可组合微内核双模调度器与全域领域算子聚合流水线
- **change_size**：`M`
- **创建时间**：`2026-10-17T02:10:00Z`
- **当前状态**：`COMPLETED`
- **继承规约**：
  - `hs_dev_docs/_03_architecture_design/_02_system_architecture/opchub_composable_framework_architecture.md`
  - `hs_dev_docs/_03_architecture_design/_02_system_architecture/opchub_fullstack_lowcode_engine_spec.md`
  - `DESIGN.md`

---

## 1. 核心接口与数据模型契约

### 1.1 双模调度枚举与调度请求
```python
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel

class DispatchMode(str, Enum):
    IN_PROCESS = "IN_PROCESS"    # 单体架构：直接内存方法调用
    HTTP_REMOTE = "HTTP_REMOTE"  # 微服务演进：远程 HTTP API 派发

class OperatorDescriptor(BaseModel):
    name: str                    # 如 "policy.calculate_tax"
    domain: str                  # 如 "policy", "sop", "compliance", "external"
    description: str             # 算子大白话说明
    dispatch_mode: DispatchMode = DispatchMode.IN_PROCESS
    remote_endpoint: Optional[str] = None
```

### 1.2 场景编排流水线执行契约
```python
class ScenarioExecuteRequest(BaseModel):
    scenario_code: str           # 如 "OPC_COMPLIANCE_STARTUP_FLOW"
    inputs: Dict[str, Any]       # 输入参数字典
    override_dispatch_mode: Optional[DispatchMode] = None

class ScenarioExecuteResponse(BaseModel):
    scenario_code: str
    status: str                  # "SUCCESS" / "FAILED"
    execution_time_ms: float
    trace_id: str
    dispatch_mode: DispatchMode
    node_traces: list[dict]
    final_output: dict
```

---

## 2. 算子命名空间规划
- `policy.calculate_tax`: 政策增值税免征与实际纳税测算
- `policy.match_subsidies`: 根据创客画像多条件智能匹配政策补贴
- `sop.render_document`: 渲染标准化申报公文并签发核验流水号
- `compliance.evaluate_audit`: 根据上线前检查项实时计算综合合规指数
- `moderation.inspect_content`: UGC敏感词与违规内容审查与处置
- `external.ai.generate_charter`: 统一外部网关代理生成一人有限责任公司章程
- `external.crawler.fetch_policy`: 统一外部网关低速采集官方政务政策公文
- `external.payment.split_order`: 统一外部网关执行分账指令
- `external.sms.send_auth_code`: 统一外部网关发送实名核验验证码

---

## 3. 约束与安全门禁
1. 严禁破坏已有的 45 个单测用例。
2. 双模调度器必须在单体模式下 0 网络开销，在微服务模式下能够无缝对接外部 HTTP。
3. 纯静态 HTML 原型中增加的按钮必须 $\le 4$ 汉字。
