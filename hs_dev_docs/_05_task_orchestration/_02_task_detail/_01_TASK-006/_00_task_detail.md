# 任务详细设计与执行记录：TASK-006

- **任务名称**：产品开发合规专区与需求集市法律求助引擎
- **变更分级**：`M`
- **当前状态**：`COMPLETED`
- **优先级**：P0
- **负责人**：hardstone
- **开始时间**：`2026-10-17T01:45:00Z`
- **完成时间**：`2026-10-17T01:53:00Z`
- **最后更新**：`2026-10-17T01:53:00Z`

---

## 1. 任务背景与目标
- 用户明确要求增加合规页面，展示产品开发的合规问题（隐私、二清、资质备案、开源许可证感染、数据出境与UGC内容安全），避免开发者踩坑。
- 需求外包集市支持发布法律求助帖子，并为创客对接涉外律所及合规顾问。
- 合规自检雷达在线计算安全评分（0~100），并可一键直通需求集市法律求助专区。
- 全站按钮严格遵守 $\le 4$ 汉字与 VisionOS 流体毛玻璃设计规范。

---

## 2. 验收标准
1. 单元测试 100% 通过（45/45 PASS）。
2. 98 个按钮字符全部 $\le 4$ 汉字，0 换行，带微图标与 Tooltip。
3. 创客工作区包含 8 个业务页，管理端与创客端物理隔离与互斥保护正常生效。
4. 需求集市支持筛选并发布 `LEGAL` 法律合规需求与竞标。
5. 验收单 `hs_dev_docs/_03_acceptance/task_006_acceptance.md` 通过。

---

## 3. 执行步骤 (Checklist)
- [x] 1. 更新词典与 PRD (`_02_project_word.dict.yaml`, `opchub_mvp_prd.md` REQ-05 & REQ-07)
- [x] 2. 实现后端合规知识与自检服务 (`backend/src/domains/compliance/`)
- [x] 3. 扩展需求集市模型与服务以支持 `LEGAL` 类别与种子数据 (`backend/src/domains/demands/`)
- [x] 4. 挂载 FastAPI 合规 API 与首页快捷入口 (`backend/src/main.py`)
- [x] 5. 编写全覆盖单测 (`backend/tests/test_compliance_and_legal_demand.py`，全量 45 个用例全部 PASS)
- [x] 6. 完成 HTML5 响应式原型与 JavaScript 自检雷达及直通跳转 (`opchub_all_pages_demo.html`)
- [x] 7. 本地质量门禁与验收确认完成

---

## 4. 涉及文件修改清单 (Diff Tracking)
```text
backend/src/domains/compliance/__init__.py
backend/src/domains/compliance/models.py
backend/src/domains/compliance/service.py
backend/src/domains/demands/models.py
backend/src/domains/demands/service.py
backend/src/main.py
backend/tests/test_compliance_and_legal_demand.py
backend/tests/test_all_domains_persistence.py
hs_dev_docs/_00_project_foundation/_02_dictionary/_02_project_word.dict.yaml
hs_dev_docs/_02_feature_spec/_01_human_prd/opchub_mvp_prd.md
hs_dev_docs/_02_feature_spec/_03_prototype_html/opchub_all_pages_demo.html
hs_dev_docs/_03_acceptance/task_006_acceptance.md
hs_dev_docs/_05_task_orchestration/_01_task_brief/_01_task_brief_001.md
hs_dev_docs/_05_task_orchestration/_02_task_detail/_01_TASK-006/_00_task_detail.md
hs_dev_docs/_05_task_orchestration/_03_task_context_pack/_01_TASK-006/_00_context_pack.md
```
