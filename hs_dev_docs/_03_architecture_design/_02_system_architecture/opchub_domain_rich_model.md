# OpcHub 后端充血模型与流程编排微内核设计 (Rich Domain Model & Pipeline Spec)

> **Document Type**: Phase 2 Tactical Architecture Specification  
> **Inherits**: `opchub_system_architecture.md`  
> **Paradigm**: DDD 轻量充血模型 (Rich Domain Model) + 动态微内核管线 (Pipeline Orchestration)

---

## [VIBE_CONTRACT] 架构执行契约 (Machine-Actionable Domain Contract)
```yaml
domain_contract:
  paradigm_tier: "B4_DDD_Rich_Domain_Model"
  core_aggregates:
    - name: "ScenarioPipeline"
      responsibilities: "维护业务场景管线定义、按序串联执行注册方法、管理上下文流转与中断回滚"
    - name: "ActionRegistry"
      responsibilities: "受限原子方法注册中心、动态 Python 脚本 AST 安全校验与沙箱加载"
    - name: "PolicyAggregate"
      responsibilities: "政策生命周期管理、白话提炼、创客画像资格审查与补贴金额自测算"
    - name: "GalleryProductAggregate"
      responsibilities: "创客产品入驻生命周期、付费状态流转、点赞防刷自增计数与置顶权重维护"
    - name: "UserAggregate"
      responsibilities: "用户三级身份封装、权限判定、操作配额与审计凭据校验"

guardrails:
  - "MUST: 严禁贫血实体 (Anemic Entity)！所有状态变更、业务校验与规则断言必须收敛于聚合根方法内部，外部严禁直接操作私有属性"
  - "MUST: 流程编排中的每一个原子方法必须保持完全相同的签名：async def (ctx: PipelineContext) -> PipelineContext"
  - "MUST: 管理员上传的 Python 脚本必须先通过 AST 静态安全审查，严禁引入 os, sys, subprocess, eval, exec 等危险系统调用"
```

---

## 1. 核心聚合根充血模型设计 (Rich Domain Entities)

### 1.1 场景流程管线聚合根 (`ScenarioPipelineAggregate`)
管线不仅是一串配置，而是一个拥有状态检查、顺序执行、异常熔断与指标度量的**充血领域聚合**：

```python
from dataclasses import dataclass, field
from typing import List, Dict, Any, Callable
import time

@dataclass
class PipelineContext:
    scenario: str
    user_id: str
    user_role: str
    input_payload: Dict[str, Any]
    state: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    next_action: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    is_halted: bool = False

    def halt(self, reason: str):
        """中断管线执行"""
        self.is_halted = True
        self.errors.append(reason)

class ScenarioPipelineAggregate:
    """管线聚合根：封装场景执行生命周期"""
    def __init__(self, scenario_code: str, steps: List[str]):
        self.scenario_code = scenario_code
        self.steps = steps  # 有序的方法名称列表
        self.is_active = True

    async def execute(self, ctx: PipelineContext, registry: "ActionRegistry") -> PipelineContext:
        """充血方法：顺序编排执行注册的方法"""
        if not self.is_active:
            ctx.halt(f"场景管线 [{self.scenario_code}] 处于禁用状态")
            return ctx

        for step_name in self.steps:
            if ctx.is_halted:
                break

            action_fn = registry.get_action(step_name)
            if not action_fn:
                ctx.halt(f"未找到已注册的原子动作: {step_name}")
                break

            try:
                # 执行原子方法（签名统一一致）
                ctx = await action_fn(ctx)
            except Exception as e:
                ctx.halt(f"执行步骤 [{step_name}] 抛出异常: {str(e)}")
                break

        return ctx
```

---

### 1.2 动态 Python 脚本注册中心与安全沙箱 (`ActionRegistry`)
允许管理员上传 Python 脚本文件，将其动态注册为系统的原子编排节点，具备严格的 **AST 语法树安全沙箱**：

```python
import ast
from typing import Dict, Callable

class ActionRegistry:
    """方法注册中心与沙箱加载器"""
    _builtins_actions: Dict[str, Callable] = {}
    _dynamic_actions: Dict[str, Callable] = {}

    FORBIDDEN_MODULES = {"os", "sys", "subprocess", "shutil", "socket", "pty"}
    FORBIDDEN_CALLS = {"eval", "exec", "__import__", "open"}

    @classmethod
    def register_builtin(cls, name: str):
        """内置方法装饰器"""
        def decorator(fn: Callable):
            cls._builtins_actions[name] = fn
            return fn
        return decorator

    @classmethod
    def load_dynamic_script(cls, action_name: str, python_code: str):
        """充血方法：安全审查并热加载管理员上传的 Python 脚本"""
        # 1. AST 语法树安全静态扫描
        tree = ast.parse(python_code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split('.')[0] in cls.FORBIDDEN_MODULES:
                        raise SecurityError(f"安全违规：脚本禁止导入危险系统模块 {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split('.')[0] in cls.FORBIDDEN_MODULES:
                    raise SecurityError(f"安全违规：脚本禁止导入危险系统模块 {node.module}")
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in cls.FORBIDDEN_CALLS:
                    raise SecurityError(f"安全违规：脚本禁止调用危险内置函数 {node.func.id}")

        # 2. 隔离命名空间动态编译执行
        safe_globals = {
            "__builtins__": {
                "range": range, "len": len, "min": min, "max": max,
                "dict": dict, "list": list, "str": str, "int": int, "float": float, "bool": bool
            }
        }
        safe_locals = {}
        compiled_code = compile(tree, filename=f"<dynamic_action_{action_name}>", mode="exec")
        exec(compiled_code, safe_globals, safe_locals)

        # 3. 校验方法导出与签名
        if "action_entry" not in safe_locals or not callable(safe_locals["action_entry"]):
            raise ValueError("动态脚本必须包含顶层导出的 async def action_entry(ctx) 入口函数")

        cls._dynamic_actions[action_name] = safe_locals["action_entry"]

    @classmethod
    def get_action(cls, name: str) -> Callable:
        return cls._dynamic_actions.get(name) or cls._builtins_actions.get(name)
```

---

### 1.3 业务聚合根充血封装示例：政策与产品橱窗
所有领域对象自己守护自己的业务不变量，拒绝外部直接篡改状态：

```python
class PolicyAggregate:
    """政策聚合根 (充血模型)"""
    def __init__(self, id: str, title: str, status: str, deadline: datetime, criteria: dict):
        self.id = id
        self.title = title
        self._status = status
        self.deadline = deadline
        self.criteria = criteria  # 门槛要求

    def publish(self, operator_role: str):
        """发布政策"""
        if operator_role != "ADMIN":
            raise PermissionError("只有平台管理员有权发布政策")
        if self._status == "PUBLISHED":
            raise InvalidStateError("政策已处于发布状态")
        self._status = "PUBLISHED"

    def match_user_profile(self, user_city: str, entity_type: str, annual_revenue: float) -> bool:
        """政策自身评估是否命中用户画像"""
        if self._status != "PUBLISHED":
            return False
        if self.criteria.get("city") and self.criteria["city"] != user_city:
            return False
        if self.criteria.get("allowed_entities") and entity_type not in self.criteria["allowed_entities"]:
            return False
        if annual_revenue > self.criteria.get("max_revenue", float("inf")):
            return False
        return True
```

---

## 2. 统一单入口网关执行流 (Gateway Dispatcher)

所有客户端请求统一打到 `/api/v1/gateway`，分发器自动装配 Context 并驱动编排管线：

```python
# FastAPI 单入口网关路由
@router.post("/gateway")
async def unified_gateway_handler(
    envelope: GatewayRequestEnvelope,
    current_user: UserIdentity = Depends(get_current_user),
    pipeline_service: PipelineService = Depends()
):
    # 1. 组装初始管线上下文
    ctx = PipelineContext(
        scenario=envelope.scenario,
        user_id=current_user.user_id,
        user_role=current_user.role,
        input_payload=envelope.payload
    )

    # 2. 调度场景流程管线
    result_ctx = await pipeline_service.dispatch_scenario(ctx)

    if result_ctx.is_halted:
        raise HTTPException(status_code=400, detail={"errors": result_ctx.errors})

    # 3. 统一返回数据与下一动作指令 (Next Action)
    return {
        "code": 200,
        "scenario": envelope.scenario,
        "data": result_ctx.output_data,
        "next_action": result_ctx.next_action
    }
```
