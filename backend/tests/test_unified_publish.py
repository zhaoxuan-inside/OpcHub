"""Unified content publishing across boards (统一创建发布功能).

平台契约：所有注册用户可发布；平台只做两级敏感词门禁（本地预筛对「肯定没问题 /
肯定有问题」高置信短接，仅「不确定」内容外呼外部审核服务）；平台不确认信息真实性，
由用户互动（点赞/点踩/举报）维护有效性，举报进入平台审核队列；官方发布的条目由
服务端按发布者角色自动打官方标签（is_official），客户端传入值一律忽略。
"""
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.core.security import create_session_token
from conftest import dispatch, gw_data


MAKER_TOKEN = create_session_token({
    "uid": "usr_maker_pub",
    "email": "maker_pub@opchub.cn",
    "nickname": "发布测试创客",
    "role": "MAKER",
    "must_change_password": False,
})

POLICY_PAYLOAD = {
    "title": "园区创客住房补贴申领指引",
    "policy_level": "园区级",
    "category": "RENT",
    "subsidy_amount_max": 12000.0,
    "summary": "面向园区创客的住房补贴申领流程、材料清单与常见退回原因说明。",
    "eligible_conditions": ["园区注册且正常经营"],
    "legal_basis": "《园区人才安居实施办法》",
}

PERK_PAYLOAD = {
    "name": "云服务器创客代金券",
    "provider": "云原生科技",
    "value_cny": 500.0,
    "category": "SERVER",
    "summary": "创客认证后可领取的云服务器采购代金券，有效期三个月。",
}

PRODUCT_PAYLOAD = {
    "title": "创客发票对账助手",
    "tagline": "面向一人公司的本地优先票据核对工具",
    "description": "自动归集进销项票据，辅助完成税务登记与合规申报前的账目核对。",
    "category": "TAX",
    "pricing_model": "FREE",
    "price_cny": 0.0,
}

FORUM_PAYLOAD = {
    "title": "一人公司报税季的踩坑复盘",
    "content": "记录首次申报增值税与个人所得税时踩过的坑，以及准备材料的完整清单。",
    "category_code": "TAX",
}

DEMAND_PAYLOAD = {
    "title": "寻找长期合作的代理记账与税务合规顾问",
    "description": "一人公司需要每月记账、季度申报与年度汇算清缴的长期合规支持。",
    "budget_cny": 6000.0,
    "category": "TAX",
    "deadline_days": 20,
}

# (scenario, payload, author field, display label) for every UGC publish board.
PUBLISH_BOARDS = [
    ("policies.publish", POLICY_PAYLOAD, "author_id", "政策"),
    ("perks.publish", PERK_PAYLOAD, "author_id", "生态特权"),
    ("products.publish", PRODUCT_PAYLOAD, "author_id", "产品橱窗"),
    ("forum.threads.publish", FORUM_PAYLOAD, "author_id", "头脑风暴"),
    ("demands.publish", DEMAND_PAYLOAD, "creator_id", "需求集市"),
]


@pytest.fixture
def client():
    return TestClient(app)


def _maker_dispatch(client, scenario, payload=None):
    return dispatch(client, scenario, payload, token=MAKER_TOKEN)


# --------------------------------------------------------------- 谁能发布
def test_registered_maker_can_publish_policy(client):
    """政策中心此前仅管理员可发布，统一后所有注册用户可发布。"""
    resp = _maker_dispatch(client, "policies.publish", POLICY_PAYLOAD)
    body = resp.json()
    assert body["code"] == 200, body
    data = body["data"]
    assert data["author_id"] == "usr_maker_pub"
    assert data["author_name"] == "发布测试创客"
    assert data["is_official"] is False
    ids = [p["id"] for p in gw_data(client, "policies.list", {})]
    assert data["id"] in ids


def test_registered_maker_can_publish_perk(client):
    resp = _maker_dispatch(client, "perks.publish", PERK_PAYLOAD)
    body = resp.json()
    assert body["code"] == 200, body
    assert body["data"]["is_official"] is False


# --------------------------------------------------------------- 官方标签
def test_admin_publish_stamps_official_tag(client):
    data = gw_data(client, "policies.publish", POLICY_PAYLOAD)
    assert data["is_official"] is True

    case = gw_data(client, "compliance.publish", {
        "kind": "case",
        "title": "二清违规资金冻结案例",
        "industry": "电商服务",
        "violation": "平台二次清算商户结算资金",
        "consequence": "监管处罚并冻结结算账户",
        "lesson": "结算资金必须持牌机构托管",
    })
    assert case["is_official"] is True


def test_client_supplied_official_tag_is_ignored(client):
    """官方标签只认服务端角色，客户端伪造 is_official 一律无效。"""
    spoofed = dict(POLICY_PAYLOAD, is_official=True)
    resp = _maker_dispatch(client, "policies.publish", spoofed)
    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["is_official"] is False


def test_curated_content_is_official(client):
    """平台策展内容可标记为官方发布（测试夹具模拟策展数据）。"""
    from src.domains.policies.service import policy_service
    from src.domains.compliance.service import compliance_service
    from tests.catalog_fixtures import seed_compliance, seed_policies

    if not policy_service._policies:
        seed_policies(policy_service)
    if not compliance_service._laws:
        seed_compliance(compliance_service)

    policies = {p["id"]: p for p in gw_data(client, "policies.list", {})}
    seed = policies.get("pol_vat_exemption_2026")
    assert seed, "curated policy pol_vat_exemption_2026 missing"
    assert seed["is_official"] is True

    laws = {l["id"]: l for l in gw_data(client, "compliance.laws", {})}
    for law_id in ("law_privacy", "law_payment", "law_filing", "law_ip_oss"):
        assert laws[law_id]["is_official"] is True, law_id


# --------------------------------------------------------------- 敏感词门禁
def test_compliance_publish_requires_login(client):
    client.headers.pop("Authorization", None)
    resp = dispatch(client, "compliance.publish", {
        "kind": "law",
        "title": "未登录发布尝试",
        "summary": "未登录用户不应能通过合规知识库发布内容。",
    })
    assert resp.json()["code"] in (401, 403)


def test_compliance_publish_maker_and_moderation(client):
    """登录创客可发布法条；命中本地预筛强违规词的内容被直接拦截。"""
    ok = _maker_dispatch(client, "compliance.publish", {
        "kind": "law",
        "title": "个人信息保护合规要点",
        "summary": "处理个人信息应取得同意并遵循最小必要原则，注意数据合规。",
        "content": "收集个人信息前须明示处理目的、方式与保存期限。",
        "level": "法律",
    })
    body = ok.json()
    assert body["code"] == 200, body
    assert body["data"]["author_id"] == "usr_maker_pub"
    assert body["data"]["is_official"] is False

    blocked = _maker_dispatch(client, "compliance.publish", {
        "kind": "case",
        "title": "资金流转通道推荐",
        "industry": "支付服务",
        "violation": "该方法可帮助商户洗钱且难以被追踪",
        "consequence": "涉嫌刑事犯罪",
        "lesson": "切勿尝试",
    })
    assert blocked.json()["code"] == 400
    assert "moderation" in str(blocked.json()).lower() or "敏感" in str(blocked.json())


def test_comment_sensitive_word_rejected(client):
    """评论同样走统一敏感词门禁：强违规词直接 400。"""
    policies = gw_data(client, "policies.list", {})
    target_id = policies[0]["id"]
    resp = _maker_dispatch(client, "content.comments.create", {
        "target_type": "POLICY",
        "target_id": target_id,
        "content": "需要洗钱通道的可以联系我",
    })
    assert resp.json()["code"] == 400


# --------------------------------------------------------------- 用户举报
def test_user_report_enters_moderation_queue_and_dedups(client):
    policies = gw_data(client, "policies.list", {})
    target = next(p for p in policies if not p.get("is_official"))
    payload = {
        "target_type": "POLICY",
        "target_id": target["id"],
        "target_title": target["title"],
        "reason": "补贴信息已过期失实",
    }

    first = _maker_dispatch(client, "moderation.report", payload).json()
    assert first["code"] == 200, first
    assert first["data"]["status"] == "FLAGGED"
    assert first["data"]["report_count"] == 1

    second = _maker_dispatch(client, "moderation.report", payload).json()
    assert second["code"] == 200
    assert second["data"]["id"] == first["data"]["id"]
    assert second["data"]["report_count"] == 2

    flagged = gw_data(client, "moderation.items.list", {"status": "FLAGGED"})
    assert any(it["target_id"] == target["id"] and it["violation_type"] == "USER_REPORT"
               for it in flagged)


def test_report_rejects_unknown_target_type(client):
    resp = _maker_dispatch(client, "moderation.report", {
        "target_type": "NOT_A_TYPE",
        "target_id": "whatever",
    })
    assert resp.json()["code"] == 400


# --------------------------------------------------------------- 全板块统一契约
@pytest.mark.parametrize("scenario,payload,author_field,label", PUBLISH_BOARDS)
def test_registered_maker_can_publish_every_board(client, scenario, payload, author_field, label):
    """政策 / 生态特权 / 产品橱窗 / 头脑风暴 / 需求集市 走同一套发布契约。"""
    data = _maker_dispatch(client, scenario, payload).json()["data"]
    assert data[author_field] == "usr_maker_pub", label
    assert data["is_official"] is False, label


@pytest.mark.parametrize("scenario,payload,author_field,label", PUBLISH_BOARDS)
def test_maker_cannot_spoof_author_identity(client, scenario, payload, author_field, label):
    """普通创客不能借 payload 里的 author_id 冒充他人发布。"""
    spoofed = dict(payload, **{author_field: "usr_victim_account"})
    data = _maker_dispatch(client, scenario, spoofed).json()["data"]
    assert data[author_field] == "usr_maker_pub", label


def test_maker_cannot_spoof_display_name(client):
    """展示名称为客户端输入，同样不能冒充官方或他人。"""
    spoofed = dict(FORUM_PAYLOAD, author_name="官方发布")
    data = _maker_dispatch(client, "forum.threads.publish", spoofed).json()["data"]
    assert data["author_name"] == "发布测试创客"


@pytest.mark.parametrize("scenario,payload,author_field,label", PUBLISH_BOARDS)
def test_client_supplied_official_tag_is_ignored_everywhere(client, scenario, payload, author_field, label):
    """所有板块的官方标签只认服务端角色，客户端伪造一律无效。"""
    spoofed = dict(payload, is_official=True)
    data = _maker_dispatch(client, scenario, spoofed).json()["data"]
    assert data["is_official"] is False, label


@pytest.mark.parametrize("scenario,payload", [
    ("policies.publish", dict(POLICY_PAYLOAD, title="代开发票与洗钱通道对接",
                              summary="提供代开发票与洗钱通道对接服务，保证月入十万。")),
    ("products.publish", dict(PRODUCT_PAYLOAD, title="代开发票神器")),
    ("forum.threads.publish", dict(FORUM_PAYLOAD, content="出售未经脱敏的企业内网访问私钥与洗钱通道。")),
    ("demands.publish", dict(DEMAND_PAYLOAD, description="需要能够提供洗钱与地下钱庄资金通道的合作方。")),
    ("perks.publish", dict(PERK_PAYLOAD, name="代开发票返利特权")),
])
def test_every_board_uses_the_same_sensitive_word_gate(client, scenario, payload):
    resp = _maker_dispatch(client, scenario, payload)
    body = resp.json()
    assert body["code"] == 400, body
    assert "敏感" in str(body) or "moderation" in str(body).lower()


def test_admin_can_attribute_content_and_still_gets_official_tag(client):
    """管理员可代发并归属原作者，官方标签仍由服务端角色决定。"""
    data = gw_data(client, "products.publish", dict(PRODUCT_PAYLOAD, author_id="usr_curated_author"))
    assert data["author_id"] == "usr_curated_author"
    assert data["is_official"] is True


def test_report_works_for_non_policy_targets(client):
    """举报覆盖所有可交互内容类型，而不只是政策。"""
    product = _maker_dispatch(client, "products.publish", PRODUCT_PAYLOAD).json()["data"]
    body = _maker_dispatch(client, "moderation.report", {
        "target_type": "PRODUCT",
        "target_id": product["id"],
        "target_title": product["title"],
        "reason": "下载链接失效，信息已失实",
    }).json()
    assert body["code"] == 200, body
    assert body["data"]["violation_type"] == "USER_REPORT"

