"""复习状态机测试。

状态机是纯函数，所以可以把每条分支都单测一遍，
这类边界正是"背单词节奏对不对"的关键。
"""

from __future__ import annotations

from datetime import date

import pytest

from vocab_agent.srs.engine import next_state
from vocab_agent.srs.ladder import (
    GRADUATED_CHECK_DAYS,
    RATING_FUZZY,
    RATING_KNOWN,
    RATING_UNKNOWN,
    STAGE_GRADUATED,
    STAGE_LEARNING,
    STAGE_NEW,
    STAGE_REVIEW,
)

# 固定一个日期，断言才能写成确定值
TODAY = date(2026, 10, 14)


def run(stage: str, step: int, rating: str, streak: int = 0, lapses: int = 0):
    """简化调用：只关心状态、级别和作答结果。"""
    return next_state(
        stage=stage,
        step=step,
        correct_streak=streak,
        lapses=lapses,
        rating=rating,
        today=TODAY,
    )


# --------------------------------------------------------------------------
# 新词第一次学
# --------------------------------------------------------------------------


def test_新词答对_进入复习阶梯第一级():
    result = run(STAGE_NEW, 0, RATING_KNOWN)
    assert result.stage == STAGE_REVIEW
    assert result.step == 1
    assert result.due_at == "2026-10-15"      # 明天复习


def test_新词答错_当天还要再见一次():
    result = run(STAGE_NEW, 0, RATING_UNKNOWN)
    assert result.stage == STAGE_LEARNING
    # 到期日就是今天，所以组装队列时它会被再次选出来 —— 这就是"当天双轮"
    assert result.due_at == "2026-10-14"
    # 学习阶段的错误不计入 lapse 统计，避免新词一上手就被打上"难词"标签
    assert result.lapses == 0


# --------------------------------------------------------------------------
# 复习阶梯
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "step, expected_next_step, expected_due",
    [
        (1, 2, "2026-10-16"),   # 2 天后
        (2, 3, "2026-10-18"),   # 4 天后
        (3, 4, "2026-10-21"),   # 7 天后
        (4, 5, "2026-10-29"),   # 15 天后
        (5, 6, "2026-11-13"),   # 30 天后
        (6, 7, "2026-12-13"),   # 60 天后
    ],
)
def test_复习答对_按阶梯往后推(step, expected_next_step, expected_due):
    result = run(STAGE_REVIEW, step, RATING_KNOWN)
    assert result.stage == STAGE_REVIEW
    assert result.step == expected_next_step
    assert result.due_at == expected_due


def test_最高级答对_毕业():
    result = run(STAGE_REVIEW, 7, RATING_KNOWN)
    assert result.stage == STAGE_GRADUATED
    # 毕业不等于永远不见，隔一段时间会抽查一次
    assert result.due_at == "2026-12-13"


def test_复习答错_退两级():
    result = run(STAGE_REVIEW, 5, RATING_UNKNOWN)
    assert result.step == 3
    assert result.stage == STAGE_REVIEW
    assert result.due_at == "2026-10-15"   # 明天再见
    assert result.lapses == 1
    assert result.correct_streak == 0      # 连续答对的计数归零


def test_第一级答错_不会退到零级():
    """退到 0 级会让这个词掉出复习队列，所以这里必须兜住。"""
    result = run(STAGE_REVIEW, 1, RATING_UNKNOWN)
    assert result.step == 1


def test_模糊_不升级也不降级_明天再来():
    result = run(STAGE_REVIEW, 4, RATING_FUZZY)
    assert result.stage == STAGE_REVIEW
    assert result.step == 4                 # 级别不动
    assert result.due_at == "2026-10-15"    # 但明天要再看一眼
    assert result.lapses == 0               # 模糊不算错


# --------------------------------------------------------------------------
# 毕业后
# --------------------------------------------------------------------------


def test_毕业后答对_隔规定天数再抽查():
    result = run(STAGE_GRADUATED, 7, RATING_KNOWN)
    assert result.stage == STAGE_GRADUATED
    assert result.due_at == "2026-12-13"
    assert GRADUATED_CHECK_DAYS == 60


def test_毕业后答错_掉回复习队列():
    result = run(STAGE_GRADUATED, 7, RATING_UNKNOWN)
    assert result.stage == STAGE_REVIEW
    assert result.step == 5                 # 退两级
    assert result.lapses == 1
