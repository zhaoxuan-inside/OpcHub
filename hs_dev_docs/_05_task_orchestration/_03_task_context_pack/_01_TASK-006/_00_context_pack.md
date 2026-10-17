# 任务上下文信息包：TASK-006

- **任务编号**：`TASK-006`
- **任务名称**：产品开发合规专区与需求集市法律求助引擎
- **变更分级**：`M`
- **创建时间**：`2026-10-17T01:45:00Z`
- **当前状态**：`COMPLETED`

---

## 1. 核心需求输入
用户指示：
> "还需要增加一个合规页面，用来展示产品开发的合规问题，避免大家踩坑；需求集市中也支持法律求助之类的帖子；"

---

## 2. 架构与依赖设计
- 后端新增 `compliance` 领域，导出 6 维度合规准则、3 项避坑案例文档与 10 项上线前自检清单，并提供带加权评分的体检接口。
- 需求集市领域 `demands` 扩展类别枚举支持 `LEGAL`，并内置种子数据。
- 前端原型 View 13 全景落地合规指南、踩坑剖析及自检雷达，打通直接跳转至需求集市发起法律合规委托。

---

## 3. 关联文件
- `backend/src/domains/compliance/`
- `backend/src/domains/demands/`
- `backend/src/main.py`
- `backend/tests/test_compliance_and_legal_demand.py`
- `hs_dev_docs/_02_feature_spec/_03_prototype_html/opchub_all_pages_demo.html`
