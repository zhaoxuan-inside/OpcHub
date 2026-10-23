"""NLP Pre-Screen Operator (本地 NLP 前置审核算子).

A lightweight, dependency-free NLP pre-screener that runs locally (no network, no
third-party model) and classifies text into one of three high-confidence verdicts:

* ``CONFIRMED_SAFE``     —— 肯定没问题：有把握放行，无需外呼，省延迟与成本。
* ``CONFIRMED_VIOLATION``—— 肯定有问题：有把握拦截，无需外呼。
* ``UNCERTAIN``          —— 不确定：证据不足，交由外部审核服务裁决。

Design rationale
----------------
External content-moderation services are authoritative but slow/costly and can be
unreachable (ADR-002/003 graceful degradation). A local NLP pre-screen lets the
platform answer the *high-confidence majority* itself and only defer the genuinely
ambiguous minority to the external gate. This keeps availability high while the
external service still owns the final word on uncertain content.

How the verdict is reached
--------------------------
The engine combines three signals and only commits to a confident verdict when the
evidence is *unambiguous*:

1. **Sensitive-lexicon severity** — a curated local lexicon of high-severity
   violation tokens (illegal trade, fraud, scam, money-laundering …). Any hit with
   enough aggregate severity → CONFIRMED_VIOLATION.

2. **High-confidence scam / fraud patterns** — co-occurrence heuristics such as
   ``contact channel + money + urgency`` or ``guaranteed ROI + money``. These encode
   the *structure* of common fraud, not just keywords, so it behaves like a small
   NLP classifier rather than a plain keyword matcher.

3. **Safe-lexicon + benign profile** — a whitelist of normal business / tech /
   compliance vocabulary. When the text is short, contains safe tokens and has *no*
   sensitive signals, it is a confident pass.

Anything that does not reach a confident threshold falls through to ``UNCERTAIN`` and
is handed to the external service.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.core.telemetry import get_current_trace_id

# ---------------------------------------------------------------------------
# Verdicts
# ---------------------------------------------------------------------------
VERDICT_SAFE = "CONFIRMED_SAFE"
VERDICT_VIOLATION = "CONFIRMED_VIOLATION"
VERDICT_UNCERTAIN = "UNCERTAIN"

# ---------------------------------------------------------------------------
# Curated local lexicons (independent from the external service's keyword list).
# These are *high-severity* tokens only; anything lower severity is deliberately
# left to the external service so the pre-screen never over-blocks.
# ---------------------------------------------------------------------------
SENSITIVE_LEXICON: Dict[str, int] = {
    # 非法交易 / 走私 / 违禁品
    "代开发票": 3, "代开发票": 3, "虚开发票": 3, "倒卖发票": 3, "假发票": 3,
    "走私": 3, "地下钱庄": 3, "洗钱": 3, "跑分": 3, "资金盘": 3,
    "非法集资": 3, "非法吸收公众存款": 3, "传销": 3, "庞氏": 3,
    "诈骗": 3, "电信诈骗": 3, "网络诈骗": 3, "杀猪盘": 3, "博彩": 3, "赌博": 3,
    "裸聊": 3, "色情": 3, "代孕": 3, "伪造证件": 3, "伪造公章": 3,
    "售卖枪支": 3, "毒品": 3, "冰毒": 3, "买卖个人信息": 3, "出售个人信息": 3,
    "盗卖": 3, "内鬼": 3, "黑客工具": 3, "木马": 3, "钓鱼网站": 3,
    "泄露内网": 3, "私钥": 3, "外挂": 3, "刷单返利": 3, "套现": 3,
    # 涉税违法 / 骗补
    "偷逃税": 3, "逃税": 3, "骗补": 3, "骗税": 3, "空壳公司": 3,
    "注册空壳": 3, "虚假申报": 3, "骗取补贴": 3,
}

# 高置信安全的日常商业 / 技术 / 合规词汇：出现即显著拉低风险分。
SAFE_LEXICON: Dict[str, int] = {
    "软件开发": 0, "技术咨询": 0, "人工智能": 0, "算法": 0, "大数据": 0,
    "云计算": 0, "区块链研发": 0, "数字营销": 0, "品牌设计": 0, "版权": 0,
    "知识产权": 0, "专利": 0, "软件著作权": 0, "营业执照": 0, "税务登记": 0,
    "银行开户": 0, "章程": 0, "经营范围": 0, "注册资本": 0, "信用代码": 0,
    "申报": 0, "备案": 0, "核名": 0, "结汇": 0, "合规": 0, "合同": 0,
    "发票": 0, "纳税": 0, "社保": 0, "经营场所": 0, "出资": 0,
}

# 高置信诈骗 / 违规模式：结构化特征，而非单纯关键词。
# 每项为 (pattern_name, regex, penalty) —— 命中即累计高违规分。
VIOLATION_PATTERNS = [
    # 联系方式 + 钱 + 急迫 = 典型引流诈骗
    ("contact_money_urgency",
     re.compile(r"(加\s*[Vv微信]|加\s*微|微信|加\s*V|V信|企鹅|q\s*q)\s*[:：]?[A-Za-z0-9０-９:：]{3,}|(微信|VX|V信)\s*[:：]?\s*[A-Za-z0-9０-９:：]{3,}", re.UNICODE), 1),
    ("money_guarantee",
     re.compile(r"(保证|承诺|百分百|稳赚|日入|月入|躺赚|无风险|零风险|稳\s*赚|回报率|高回报)\s*.{0,8}(千|万|元|块|收益|返利|佣金|翻倍|倍)", re.UNICODE), 2),
    ("illegal_guarantee",
     re.compile(r"(包过|包办|包注册|代持|虚增|调税|免税方案|节税方案)\s*.{0,6}(费|千|万|元|酬劳)", re.UNICODE), 2),
]

# 命中以下即"强烈确认有问题"的信号：与违规关键词不同，这些是行为级标志。
_STRONG_VIOLATION_TOKENS = {"洗钱", "非法集资", "诈骗", "传销", "走私", "地下钱庄", "毒品", "代开发票", "虚开发票", "私钥", "泄露内网", "博彩", "赌博"}


def _normalize(text: str) -> str:
    return (text or "").replace(" ", "").replace("\u3000", "").lower()


def _contains_any(text: str, tokens: "set[str]") -> List[str]:
    return [t for t in tokens if t in text]


def prescreen_text(content: str) -> Dict[str, Any]:
    """Run the local NLP pre-screen over a piece of text.

    Returns a verdict dict with an explicit three-way ``verdict`` plus evidence, so
    callers can decide whether to short-circuit or defer to the external service.

    Returns:
        dict with:
            - verdict: VERDICT_SAFE | VERDICT_VIOLATION | VERDICT_UNCERTAIN
            - confirmed_issue (bool): True only when verdict is CONFIRMED_VIOLATION
            - confirmed_clean (bool): True only when verdict is CONFIRMED_SAFE
            - should_defer_to_external (bool): True only when verdict is UNCERTAIN
            - violation_score / safe_score: explainable evidence scores
            - hit_sensitive (list): matched high-severity sensitive tokens
            - matched_patterns (list): matched structural fraud-pattern names
            - trace_id: current request trace for observability
    """
    raw = content or ""
    text = _normalize(raw)
    if not text:
        return _verdict(VERDICT_SAFE, raw, 0, 0, [], [], "empty or whitespace-only")

    violation_score = 0
    safe_score = 0
    hit_sensitive: List[str] = []
    matched_patterns: List[str] = []

    # 1) Sensitive lexicon
    for tok, sev in SENSITIVE_LEXICON.items():
        if tok in text:
            violation_score += sev
            hit_sensitive.append(tok)

    # 2) Structural fraud / scam patterns
    for pname, regex, penalty in VIOLATION_PATTERNS:
        if regex.search(text):
            violation_score += penalty
            matched_patterns.append(pname)

    # 3) Safe lexicon (benign business / tech / compliance vocabulary)
    for tok in SAFE_LEXICON:
        if tok in text:
            safe_score += 1

    # ---------- Decide ----------
    # Strong violation: any high-severity token, a clear structural pattern set,
    # or the co-occurrence of a contact channel AND a money/guarantee hook (the
    # structural fingerprint of common online scams).
    is_strong_scam_signal = (
        "contact_money_urgency" in matched_patterns and "money_guarantee" in matched_patterns
    )
    if (any(t in text for t in _STRONG_VIOLATION_TOKENS)
            or violation_score >= 4 or is_strong_scam_signal):
        return _verdict(VERDICT_VIOLATION, raw, violation_score, safe_score,
                        hit_sensitive, matched_patterns, "high-severity sensitive signal")

    # Confident safe: short text, benign vocabulary present, and no sensitive signal.
    if (violation_score == 0 and safe_score >= 3 and len(raw) <= 240
            and not matched_patterns):
        return _verdict(VERDICT_SAFE, raw, violation_score, safe_score,
                        hit_sensitive, matched_patterns, "benign business/compliance profile")

    # Otherwise: not confident either way → defer to the external service.
    return _verdict(VERDICT_UNCERTAIN, raw, violation_score, safe_score,
                    hit_sensitive, matched_patterns,
                    "insufficient local evidence; defer to external moderation")


def _verdict(verdict: str, content: str, violation_score: int, safe_score: int,
             hit_sensitive: List[str], matched_patterns: List[str],
             reason: str) -> Dict[str, Any]:
    return {
        "verdict": verdict,
        "confirmed_issue": verdict == VERDICT_VIOLATION,
        "confirmed_clean": verdict == VERDICT_SAFE,
        "should_defer_to_external": verdict == VERDICT_UNCERTAIN,
        "violation_score": violation_score,
        "safe_score": safe_score,
        "hit_sensitive": sorted(set(hit_sensitive)),
        "matched_patterns": matched_patterns,
        "reason": reason,
        "trace_id": get_current_trace_id(),
    }