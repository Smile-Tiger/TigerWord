"""调用 LLM 的最小客户端。

【为什么直接用 httpx，而不引入 openai 之类的 SDK】
    接口本身就是一个 POST /chat/completions，代码量很小。
    手写的好处：少一个依赖，而且"到底发了什么、收回了什么"一眼能看清，
    排查"AI 补的内容不对"这类问题时特别有用。

【只在这里发网络请求】
    其它模块不直接碰网络，方便以后换服务商、加缓存、加限速。
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from ..config import get_settings
from .config import LLMConfig, default_llm_config


class LLMError(RuntimeError):
    """调用 LLM 失败。调用方统一按"补全失败"处理，不要把整个导入搞崩。"""


def is_configured(config: LLMConfig | None = None) -> bool:
    """有没有配好 Key。没配就跳过补全，导入照样能跑。"""
    return (config or default_llm_config()).is_ready


def chat_json(
    system_prompt: str,
    user_prompt: str,
    *,
    config: LLMConfig | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """发一次对话请求，要求模型返回 JSON，解析后返回 dict。

    关键设置：
        temperature = 0          补全要的是稳定，不是创意
        response_format json     强制返回 JSON，省去从散文里抠 JSON 的麻烦

    config 不传时用 .env 里的配置；接口层会传入"用户在界面上填的那份"。
    """
    settings = get_settings()
    active = config or default_llm_config()
    if not active.is_ready:
        raise LLMError("没有配置 LLM_API_KEY，无法调用 AI 补全")

    url = active.base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model or active.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {active.api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = httpx.post(
            url,
            json=payload,
            headers=headers,
            timeout=active.timeout,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise LLMError(f"LLM 返回错误状态 {exc.response.status_code}: {exc.response.text[:200]}") from exc
    except httpx.HTTPError as exc:
        raise LLMError(f"调用 LLM 失败：{exc}") from exc

    try:
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)
    except (KeyError, IndexError, ValueError, TypeError) as exc:
        raise LLMError(f"LLM 返回内容无法解析成 JSON：{exc}") from exc
