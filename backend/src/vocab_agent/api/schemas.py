"""接口的请求 / 响应模型。

用 Pydantic 定义的好处：前端传错字段会直接给出清楚的报错，
而不是到业务代码里才炸。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 设置
# ---------------------------------------------------------------------------


class LLMSettingsOut(BaseModel):
    """返回给前端的 LLM 配置。**不回传明文 Key**，只告诉前端"配没配"。"""

    provider: str
    base_url: str
    model: str
    api_key_set: bool          # 有没有配置 Key
    api_key_hint: str          # 打码后的样子，如 "sk-****abcd"


class SettingsOut(BaseModel):
    daily_new_limit: int
    enrich_enabled: bool
    llm: LLMSettingsOut


class SettingsUpdate(BaseModel):
    """前端提交的设置。只提交想改的字段即可，没提交的保持原样。

    api_key 的语义要分清：
        不传（None）  -> 不改动
        传空字符串    -> 清空（用户想删掉自己的 Key）
        传新字符串    -> 换成新的
    """

    daily_new_limit: int | None = Field(default=None, ge=0, le=500)
    enrich_enabled: bool | None = None
    llm_provider: str | None = None
    llm_base_url: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = None


# ---------------------------------------------------------------------------
# 词条与学习
# ---------------------------------------------------------------------------


class EntryOut(BaseModel):
    """一条要背的词。字段名和数据库列名保持一致，减少一层心智负担。"""

    id: int
    display: str
    kind: str
    phonetic_uk: str | None = None
    phonetic_us: str | None = None
    definition: str | None = None
    stage: str | None = None
    step: int | None = None
    due_at: str | None = None


class TodayQueueOut(BaseModel):
    new: list[EntryOut]
    review: list[EntryOut]
    daily_new_limit: int


class AnswerIn(BaseModel):
    entry_id: int
    rating: Literal["known", "fuzzy", "unknown"]
    mode: Literal["choice", "self_report"] = "choice"


class AnswerOut(BaseModel):
    stage: str
    step: int
    due_at: str | None
    again_today: bool          # True 表示这个词本场还要再出现一次
    remaining: int             # 本场还剩多少张卡（前端用来画进度条）
