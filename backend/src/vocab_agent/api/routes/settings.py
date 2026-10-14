"""设置接口：每日新词量、补全开关、LLM 配置。

用户在前端填自己的 API Key 和模型，就通过这里的 PUT 写进数据库，
之后导入时的 AI 补全会优先用这份配置（见 llm/config.py 的解析规则）。
"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from ... import runtime_settings as runtime
from ...config import get_settings
from ...llm import config as llm_config
from ..deps import get_db
from ..schemas import LLMSettingsOut, SettingsOut, SettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _mask(api_key: str) -> str:
    """把 Key 打码后再返回给前端。

    前端只需要知道"配没配、是不是我上次填的那把"，
    不需要拿到明文——少一次泄露机会。
    """
    if not api_key:
        return ""
    tail = api_key[-4:] if len(api_key) >= 4 else api_key
    return f"{api_key[:3]}****{tail}"


def _read(conn: sqlite3.Connection) -> SettingsOut:
    llm = llm_config.resolve_llm_config(conn)
    return SettingsOut(
        daily_new_limit=runtime.daily_new_limit(conn),
        enrich_enabled=runtime.enrich_enabled(conn),
        llm=LLMSettingsOut(
            provider=llm.provider,
            base_url=llm.base_url,
            model=llm.model,
            api_key_set=llm.is_ready,
            api_key_hint=_mask(llm.api_key),
        ),
    )


@router.get("", response_model=SettingsOut)
def read_settings(conn: sqlite3.Connection = Depends(get_db)) -> SettingsOut:
    """读当前设置。返回的 Key 是打码的。"""
    return _read(conn)


@router.put("", response_model=SettingsOut)
def update_settings(
    payload: SettingsUpdate, conn: sqlite3.Connection = Depends(get_db)
) -> SettingsOut:
    """改设置。只改传过来的字段，没传的保持原样。"""
    if payload.daily_new_limit is not None:
        runtime.set_daily_new_limit(conn, payload.daily_new_limit)
    if payload.enrich_enabled is not None:
        runtime.set_enrich_enabled(conn, payload.enrich_enabled)

    llm_config.save_llm_config(
        conn,
        base_url=payload.llm_base_url,
        api_key=payload.llm_api_key,
        model=payload.llm_model,
        provider=payload.llm_provider,
    )
    return _read(conn)


@router.get("/defaults", response_model=SettingsOut)
def read_defaults(conn: sqlite3.Connection = Depends(get_db)) -> SettingsOut:
    """看 .env 里的默认配置，界面上可以提示用户"没填就用这个"。"""
    settings = get_settings()
    llm = llm_config.default_llm_config()
    return SettingsOut(
        daily_new_limit=settings.daily_new_limit,
        enrich_enabled=settings.enrich_enabled,
        llm=LLMSettingsOut(
            provider=llm.provider,
            base_url=llm.base_url,
            model=llm.model,
            api_key_set=llm.is_ready,
            api_key_hint=_mask(llm.api_key),
        ),
    )
