# 验收规则

| ID | 内部活动 | 通过标准 |
|---|---|---|
| E8.1 | 配置定义 | 配置项有类型、默认、必填、来源及校验；业务常量枚举与运行参数区分 |
| E8.2 | 环境分级 | env.dev、env.dev.mock、env.test、env.test.mock、env.sandbox、env.online明确且可加载 |
| E8.3 | 隔离与凭证 | 预发正式禁止Mock，真实凭证注入，环境不明或配置无效立即失败 |
