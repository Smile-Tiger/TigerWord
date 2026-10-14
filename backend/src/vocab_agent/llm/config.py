"""LLM 配置的解析。

【为什么要单独一层】
    配置有两个来源：后端 .env（开发者自己用）和用户在网页上填的（带用户通道后）。
    规则是：**用户填的优先，没填就回退到 .env**。
    把这条规则收在这一个文件里，调用方（补全、接口层）就不用各自判断。

【关于密钥怎么存】
    用户填的 Key 存在本地数据库的 settings 表里（明文），
    这是单机自用应用的常见做法：库文件在用户自己电脑上。
    接口返回给前端时会打码（见 api/routes/settings.py），不会原样吐回去。
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from ..config import get_settings
from ..db import repo

# 存在 settings 表里的键名，集中在这里避免写错
KEY_BASE_URL = "llm_base_url"
KEY_API_KEY = "llm_api_key"
KEY_MODEL = "llm_model"
KEY_PROVIDER = "llm_provider"


@dataclass(frozen=True)
class LLMConfig:
    """一次 LLM 调用需要的全部参数。"""

    base_url: str
    api_key: str
    model: str
    timeout: float = 60.0
    provider: str = "deepseek"

    @property
    def is_ready(self) -> bool:
        """配好 Key 了没有。没配就跳过 AI 补全，导入照样能跑。"""
        return bool(self.api_key.strip())


def default_llm_config() -> LLMConfig:
    """只用 .env 里的配置（不查数据库）。"""
    settings = get_settings()
    return LLMConfig(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        timeout=settings.llm_timeout_seconds,
        provider=settings.llm_provider,
    )


def resolve_llm_config(conn: sqlite3.Connection | None = None) -> LLMConfig:
    """合并两个来源：用户在界面上填的 > .env 里的默认值。"""
    if conn is None:
        return default_llm_config()

    fallback = default_llm_config()
    return LLMConfig(
        base_url=repo.get_setting(conn, KEY_BASE_URL) or fallback.base_url,
        api_key=repo.get_setting(conn, KEY_API_KEY) or fallback.api_key,
        model=repo.get_setting(conn, KEY_MODEL) or fallback.model,
        timeout=fallback.timeout,
        provider=repo.get_setting(conn, KEY_PROVIDER) or fallback.provider,
    )


def save_llm_config(
    conn: sqlite3.Connection,
    *,
    base_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    provider: str | None = None,
) -> None:
    """保存用户在界面上填的配置。

    只写传进来的字段。api_key 传空字符串表示"我要清掉它"，
    传 None 表示"这次不改它"——两者含义不同，注意区分。
    """
    pairs = (
        (KEY_BASE_URL, base_url),
        (KEY_API_KEY, api_key),
        (KEY_MODEL, model),
        (KEY_PROVIDER, provider),
    )
    for key, value in pairs:
        if value is None:
            continue
        repo.set_setting(conn, key, value.strip())
