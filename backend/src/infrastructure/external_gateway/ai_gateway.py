"""Unified SiliconFlow AI Large Language Model Gateway Adapter (DeepSeek / Qwen / Gemini)."""
from typing import Any, Dict, List, Optional
import json
from src.core.config import settings
from .base_client import BaseOutboundClient


class SiliconFlowGateway(BaseOutboundClient):
    """Outbound gateway for SiliconFlow (硅基流动) and OpenAI-compatible LLM inference APIs."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key_env: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout: Optional[float] = None,
        mock_mode: Optional[bool] = None,
    ):
        super().__init__(
            service_name="SILICONFLOW_AI",
            base_url=base_url or settings.siliconflow_base_url,
            timeout=timeout or settings.siliconflow_timeout,
            mock_mode=mock_mode if mock_mode is not None else settings.siliconflow_mock_mode,
            api_key_env=api_key_env or settings.siliconflow_api_key_env
        )
        self.default_model = default_model or settings.siliconflow_default_model

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1024
    ) -> Dict[str, Any]:
        """Invoke chat completions endpoint compatible with OpenAI / SiliconFlow standards."""
        target_model = model or self.default_model

        def mock_chat(_):
            last_prompt = messages[-1].get("content", "") if messages else ""
            reply_content = f"【SiliconFlow 智能体响应】已收到指令：{last_prompt[:60]}...（模型：{target_model}）"
            return {
                "status": "SUCCESS",
                "id": "chatcmpl_mock_sf_001",
                "object": "chat.completion",
                "model": target_model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": reply_content
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 120,
                    "completion_tokens": 85,
                    "total_tokens": 205
                }
            }

        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }

        res = await self.execute_request(
            method="POST",
            path="/chat/completions",
            payload=payload,
            mock_handler=mock_chat
        )

        # Extract text reply cleanly
        if res.get("status") == "SUCCESS" and "choices" in res:
            res["reply_text"] = res["choices"][0]["message"]["content"]
        elif res.get("status") == "SUCCESS" and isinstance(res.get("data"), dict) and "choices" in res["data"]:
            choices = res["data"]["choices"]
            if choices:
                res["reply_text"] = choices[0]["message"]["content"]
                res["model"] = res["data"].get("model", target_model)
        else:
            res["reply_text"] = res.get("error", "模型生成失败")

        return res

    async def summarize_policy(
        self,
        policy_title: str,
        policy_full_text: str,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Summarize lengthy bureaucratic policy into ~100 Chinese characters plain-text action points."""
        target_model = model or self.default_model

        def mock_summary(_):
            return {
                "status": "SUCCESS",
                "policy_title": policy_title,
                "model_used": target_model,
                "plain_summary": (
                    f"【政策要点】针对小微企业与一人创客，本通知明确符合条件的主体可享受阶段性增值税减按1%征收，"
                    f"月销售额10万元以下免征，重点支持科技软件与出海数字化研发申报。"
                ),
                "target_audience": "个体工商户 / 一人有限公司 / 科技型小微企业",
                "max_benefit": "年减免最高 15 万元",
                "tokens_consumed": 260
            }

        prompt = (
            f"请将以下官方政策提炼为针对【一人公司/独立创客】的100字以内大白话要点：\n"
            f"政策标题：{policy_title}\n"
            f"公文全文：{policy_full_text[:1500]}"
        )
        messages = [
            {"role": "system", "content": "你是一位专精中国一人公司与小微财税政策的精炼助手，擅长把官样文章转为大白话硬核收益。"},
            {"role": "user", "content": prompt}
        ]

        chat_res = await self.chat_completion(messages=messages, model=target_model, temperature=0.2)
        if chat_res.get("mocked"):
            return mock_summary(None)

        return {
            "status": chat_res.get("status", "SUCCESS"),
            "policy_title": policy_title,
            "model_used": target_model,
            "plain_summary": chat_res.get("reply_text", ""),
            "tokens_consumed": chat_res.get("data", {}).get("usage", {}).get("total_tokens", 250),
            "trace_id": chat_res.get("trace_id", "")
        }

    async def generate_charter_text(
        self,
        company_name: str,
        biz_scope: str,
        registered_capital_cny: float = 100000.0,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate standard corporate charter strictly conforming to PRC Company Law for OPCs."""
        target_model = model or self.default_model

        def mock_charter(_):
            return {
                "status": "SUCCESS",
                "model": target_model,
                "company_name": company_name,
                "charter_text": (
                    f"【{company_name}章程】\n"
                    f"第一章 总则：依据《中华人民共和国公司法》及国家商事主体登记规定，设立一人有限责任公司（自然人独资）。\n"
                    f"第二章 经营范围：{biz_scope}。\n"
                    f"第三章 注册资本：人民币 {registered_capital_cny:,.2f} 元。\n"
                    f"第四章 治理结构：公司不设董事会与监事会，设执行董事一人兼任法定代表人与经理，行使公司法规定的全部职权。\n"
                    f"第五章 财务核算：严格区分公司法人财产与个人个人财产，每个会计年度编制财务会计报告并经依法审计，严防法人人格否认连带责任。"
                ),
                "tokens_consumed": 420
            }

        prompt = (
            f"为一人有限责任公司（自然人独资）起草一份完备的公司章程核心条款。\n"
            f"公司名称：{company_name}\n"
            f"经营范围：{biz_scope}\n"
            f"注册资本：{registered_capital_cny} 元人民币"
        )
        messages = [
            {"role": "system", "content": "你是一位资深中国商事律政AI，严格依据新公司法起草自然人独资一人公司章程。"},
            {"role": "user", "content": prompt}
        ]

        chat_res = await self.chat_completion(messages=messages, model=target_model, temperature=0.1)
        if chat_res.get("mocked"):
            return mock_charter(None)

        return {
            "status": chat_res.get("status", "SUCCESS"),
            "model": target_model,
            "company_name": company_name,
            "charter_text": chat_res.get("reply_text", ""),
            "tokens_consumed": chat_res.get("data", {}).get("usage", {}).get("total_tokens", 450),
            "trace_id": chat_res.get("trace_id", "")
        }


# Aliases & Singletons for export
AIGateway = SiliconFlowGateway
ai_gateway = SiliconFlowGateway()
siliconflow_gateway = ai_gateway
