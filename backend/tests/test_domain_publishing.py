"""Tests for publishing capabilities across Policies, Perks, SOP Templates, Products, and Demands."""
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_publish_policy():
    payload = {
        "title": "AI 算力与开源模型专项扶持基金",
        "policy_level": "国家级",
        "category": "SUBSIDY",
        "subsidy_amount_max": 200000.0,
        "summary": "重点扶持个人开发者及微型企业自研开源模型与智算应用部署。",
        "eligible_conditions": [
            "年营业额在500万以内",
            "代码拥有完全自主知识产权",
        ],
        "legal_basis": "工信部 2026 年算力普惠专项推进方案",
    }
    resp = client.post("/api/v1/policies", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == payload["title"]
    assert data["id"].startswith("pol_")
    assert data["subsidy_amount_max"] == 200000.0

    # Verify presence in list
    list_resp = client.get("/api/v1/policies")
    assert list_resp.status_code == 200
    ids = [p["id"] for p in list_resp.json()]
    assert data["id"] in ids


def test_publish_perk():
    payload = {
        "name": "Supabase 创客加速专属包",
        "provider": "Supabase",
        "value_cny": 2400.0,
        "category": "INFRA",
        "summary": "免费获得 12 个月 Pro 级 Postgres 数据库与 Auth 身份验证支持。",
        "quota_remaining": 50,
    }
    resp = client.post("/api/v1/perks", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == payload["name"]
    assert data["id"].startswith("perk_")
    assert data["quota_remaining"] == 50

    # Verify presence in list
    list_resp = client.get("/api/v1/perks")
    assert list_resp.status_code == 200
    ids = [p["id"] for p in list_resp.json()]
    assert data["id"] in ids


def test_publish_sop_template():
    payload = {
        "stage": 2,
        "code": "BANK_CROSS_BORDER_ACCOUNT",
        "name": "商业银行离岸离港账户开户指南与材料清单",
        "category": "FINANCE",
        "description": "一人企业与跨境创客开设离港多币种资金结算账户的标准合规指引。",
        "template_content": "离岸账户开户申请材料\\n公司名: {company_name}\\n法人: {founder_name}",
        "required_fields": [
            {"key": "company_name", "label": "企业名称", "type": "string", "required": True},
            {"key": "founder_name", "label": "法定代表人", "type": "string", "required": True},
        ],
    }
    resp = client.post("/api/v1/sop/templates", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == payload["name"]
    assert data["code"] == "BANK_CROSS_BORDER_ACCOUNT"
    assert data["id"].startswith("tpl_")

    # Verify presence in stages and templates
    list_resp = client.get("/api/v1/sop/templates")
    assert list_resp.status_code == 200
    tpl_ids = [t["id"] for t in list_resp.json()["templates"]]
    assert data["id"] in tpl_ids


def test_publish_product():
    payload = {
        "title": "ZenFlow 独立开发者任务管理器",
        "tagline": "基于极简键盘流的本地优先 GTD 工具",
        "description": "通过轻量 SQLite 与本地 CRDT 实现完全自主可控的研发进度追踪。",
        "category": "DEV",
        "pricing_model": "ONE_TIME",
        "price_cny": 99.0,
        "demo_url": "https://zenflow.dev",
        "author_id": "usr_maker_test_01",
    }
    resp = client.post("/api/v1/products", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == payload["title"]
    assert data["price_cny"] == 99.0

    # Verify presence in list
    list_resp = client.get("/api/v1/products")
    assert list_resp.status_code == 200
    ids = [p["id"] for p in list_resp.json()]
    assert data["id"] in ids


def test_publish_demand():
    payload = {
        "title": "需要一人公司跨境结汇报关与税务合规咨询",
        "description": "自研出海 SaaS 月流水超 $10,000，需要专业会计师出具合规完税与资金入境合规路径方案。",
        "budget_cny": 8000.0,
        "category": "TAX",
        "deadline_days": 10,
        "creator_id": "usr_maker_test_02",
    }
    resp = client.post("/api/v1/demands", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == payload["title"]
    assert data["budget_cny"] == 8000.0
    assert data["category"] == "TAX"

    # Verify presence in list
    list_resp = client.get("/api/v1/demands")
    assert list_resp.status_code == 200
    ids = [d["id"] for d in list_resp.json()]
    assert data["id"] in ids
