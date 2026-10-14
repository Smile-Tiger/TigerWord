"""补全：给缺音标、缺释义的词条补上内容。

【优先级】本地缓存 -> 在线词典（只补音标）-> LLM
    音标优先走词典：词典是权威来源而且免费，LLM 只在查不到时兜底。
    释义只能走 LLM：在线词典给的是英文释义，而用户词库里存的是中文释义，
    只有 LLM 能给出对得上的中文。

【铁律】补不到就留空，绝不编造。
    音标尤其不能猜——编错的音标会直接带偏发音记忆。
    提示词里已经明确要求"不确定就返回 null"。

【为什么要缓存】
    同一个词只查一次。用户反复导入时不会重复花钱，离线也能用。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from ..config import get_settings
from ..contracts import EntryDraft
from ..llm import client as llm
from ..llm.config import LLMConfig, default_llm_config

# 在线词典（免费、不需要 Key）。只用来取音标，它的释义是英文的，我们不采用。
DICTIONARY_API = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "enrich_system.md"


@dataclass
class EnrichReport:
    """补全结果统计，用于导入报告。"""

    total: int = 0
    filled_phonetic: int = 0
    filled_definition: int = 0
    from_cache: int = 0
    from_dictionary: int = 0
    from_llm: int = 0
    low_confidence: int = 0
    failed: int = 0
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 缓存
# ---------------------------------------------------------------------------


def _load_cache() -> dict[str, dict]:
    """读取本地缓存。文件损坏时按空处理，不能因为缓存把导入搞崩。"""
    path = get_settings().dictionary_cache_path
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(cache: dict[str, dict]) -> None:
    path = get_settings().dictionary_cache_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# 在线词典（只取音标）
# ---------------------------------------------------------------------------


def lookup_phonetic(word: str) -> tuple[str | None, str | None]:
    """查免费在线词典拿音标，返回（英式, 美式）。

    查不到、网络不通、超时，一律返回 (None, None)，
    让上层回退到 LLM，而不是抛异常打断导入。
    """
    # 短语（含空格）词典一般查不到，直接跳过省一次请求
    if " " in word.strip():
        return None, None

    try:
        response = httpx.get(
            DICTIONARY_API.format(word=word.strip().lower()),
            timeout=10.0,
            headers={"User-Agent": "TigerWord/0.1"},
        )
        if response.status_code != 200:
            return None, None
        entries = response.json()
    except (httpx.HTTPError, ValueError):
        return None, None

    if not isinstance(entries, list) or not entries:
        return None, None

    # 这个接口不区分英式/美式，取到一个可用音标就英美共用
    first = entries[0] if isinstance(entries[0], dict) else {}
    phonetic = first.get("phonetic")
    if not phonetic:
        for item in first.get("phonetics") or []:
            if isinstance(item, dict) and item.get("text"):
                phonetic = item["text"]
                break

    if phonetic:
        return phonetic, phonetic
    return None, None


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

# 一次发给 LLM 多少个词。太多容易超时，太少浪费请求，20 是个折中。
LLM_BATCH_SIZE = 20


def enrich_drafts(
    drafts: list[EntryDraft],
    *,
    llm_config: LLMConfig | None = None,
    enabled: bool | None = None,
    allow_llm: bool = True,
) -> tuple[list[EntryDraft], EnrichReport]:
    """给一批词条补齐缺失的音标和释义。

    注意：**只填空缺字段**。用户文件里已经有的内容一律不动。

    参数：
        llm_config 用哪份 LLM 配置。不传就用 .env 里的；
                  接口层会传入"用户在前端填的那份"。
        enabled    None 表示看配置（.env 或用户设置）；False 直接跳过。
        allow_llm  False 时只走缓存和词典（测试或不想花钱时用）。
    """
    settings = get_settings()
    active_config = llm_config or default_llm_config()
    report = EnrichReport(total=len(drafts))

    if enabled is False or (enabled is None and not settings.enrich_enabled):
        report.notes.append("补全功能已关闭，音标与释义的空缺保持原样")
        return drafts, report

    cache = _load_cache()
    cache_dirty = False
    pending: list[EntryDraft] = []

    # ---- 第一步：缓存 + 在线词典，能补的先补上 ----
    for draft in drafts:
        before_uk, before_def = draft.phonetic_uk, draft.definition

        cached = cache.get(draft.headword)
        if cached:
            _fill_from_cache(draft, cached)
            report.from_cache += 1

        # 音标还缺，并且允许联网查词典，就去查一次
        if not draft.phonetic_uk and settings.enrich_use_dictionary_api:
            uk, us = lookup_phonetic(draft.display)
            if uk or us:
                draft.phonetic_uk = draft.phonetic_uk or uk
                draft.phonetic_us = draft.phonetic_us or us
                report.from_dictionary += 1

        # 统计这一步补上了什么
        if not before_uk and draft.phonetic_uk:
            report.filled_phonetic += 1
        if not before_def and draft.definition:
            report.filled_definition += 1

        # 还有缺的，攒起来交给 LLM
        if _needs_more(draft):
            pending.append(draft)

    # ---- 第二步：剩下的交给 LLM 批量补 ----
    if pending and allow_llm:
        if not active_config.is_ready:
            report.notes.append(
                f"没有配置 LLM_API_KEY，{len(pending)} 条词条的缺失字段没有补全"
            )
            report.failed += len(pending)
        else:
            system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
            for batch in _chunks(pending, LLM_BATCH_SIZE):
                try:
                    payload = llm.chat_json(
                        system_prompt, _build_user_prompt(batch), config=active_config
                    )
                except llm.LLMError as exc:
                    # 补全失败不影响导入：空着的字段就空着
                    report.notes.append(f"AI 补全失败：{exc}")
                    report.failed += len(batch)
                    continue
                _apply_llm_results(batch, payload, report)
    elif pending:
        report.failed += len(pending)

    # ---- 第三步：把结果写回缓存，下次同样的词直接命中 ----
    for draft in drafts:
        if not (draft.phonetic_uk or draft.definition):
            continue
        snapshot = {
            "phonetic_uk": draft.phonetic_uk,
            "phonetic_us": draft.phonetic_us,
            "definition": draft.definition,
            "confidence": draft.confidence,
        }
        if cache.get(draft.headword) != snapshot:
            cache[draft.headword] = snapshot
            cache_dirty = True

    if cache_dirty:
        _save_cache(cache)

    return drafts, report


def _needs_more(draft: EntryDraft) -> bool:
    """这条词条还有没有值得补的字段。

    短语不补音标（本来就没有），所以短语只看释义。
    """
    if draft.kind == "word" and not draft.phonetic_uk:
        return True
    return not draft.definition


def _fill_from_cache(draft: EntryDraft, cached: dict) -> None:
    """用缓存里的内容填空缺，已有的字段不动。"""
    if not draft.phonetic_uk and cached.get("phonetic_uk"):
        draft.phonetic_uk = cached["phonetic_uk"]
        draft.phonetic_us = draft.phonetic_us or cached.get("phonetic_us")
    if not draft.definition and cached.get("definition"):
        draft.definition = cached["definition"]
        draft.confidence = draft.confidence or cached.get("confidence")


def _build_user_prompt(batch: list[EntryDraft]) -> str:
    """把这一批词拼成给模型的输入。只给词本身，不给多余信息，减少干扰。"""
    words = "\n".join(draft.display for draft in batch)
    return f"请补齐下面 {len(batch)} 个词：\n{words}"


def _apply_llm_results(
    batch: list[EntryDraft], payload: dict, report: EnrichReport
) -> None:
    """把模型返回的结果写回词条。

    两道防线：
        1. 按词做映射，模型多返回或少返回都不会串行
        2. 仍然是"只填空缺"，模型给的值不会覆盖用户文件里的内容
    """
    items = payload.get("items")
    if not isinstance(items, list):
        report.notes.append("AI 返回的格式不符合预期，本批跳过")
        report.failed += len(batch)
        return

    by_word = {
        str(item.get("word", "")).strip().lower(): item
        for item in items
        if isinstance(item, dict)
    }

    for draft in batch:
        item = by_word.get(draft.display.lower()) or by_word.get(draft.headword)
        if not item:
            report.failed += 1
            continue

        changed = False
        if draft.kind == "word" and not draft.phonetic_uk and item.get("phonetic_uk"):
            draft.phonetic_uk = item["phonetic_uk"]
            draft.phonetic_us = draft.phonetic_us or item.get("phonetic_us")
            report.filled_phonetic += 1
            changed = True
        if not draft.definition and item.get("definition"):
            draft.definition = item["definition"]
            report.filled_definition += 1
            changed = True

        confidence = item.get("confidence")
        if confidence in ("high", "medium", "low"):
            draft.confidence = confidence
            if confidence == "low":
                report.low_confidence += 1

        # 标注这几项是 AI 补的，方便在导入页复核
        if changed:
            draft.source = "ai"
            report.from_llm += 1


def _chunks(items: list[EntryDraft], size: int) -> list[list[EntryDraft]]:
    """把长列表切成小批。"""
    return [items[i : i + size] for i in range(0, len(items), size)]
