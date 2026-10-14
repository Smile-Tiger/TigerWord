"""状态机：一次作答之后，这个词的下一个状态是什么。

这是纯函数，不碰数据库，所以可以单独测试各种边界情况
（比如"第 1 级答错"和"最高级答对"分别会走到哪）。

状态流转规则：
    new        答对 -> 进入复习阶梯第 1 级，明天再见
               模糊 / 不认识 -> 落到 learning，今天还要再过一次
    learning   答对 -> 进入复习阶梯第 1 级，明天再见
               模糊 / 不认识 -> 留在 learning，当天队列末尾再来一遍
    review     答对 -> 升级；已经是最高级再答对就毕业
               模糊 -> 不升级，明天再来（今天先放过它）
               不认识 -> 退 LAPSE_DEMOTE_STEPS 级，明天再见
    graduated  答对 -> 隔 GRADUATED_CHECK_DAYS 天再抽查
               不认识 -> 掉回复习队列的中间级别，重新走
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from .ladder import (
    GRADUATE_STEP,
    GRADUATED_CHECK_DAYS,
    LAPSE_DEMOTE_STEPS,
    RATING_FUZZY,
    RATING_UNKNOWN,
    STAGE_GRADUATED,
    STAGE_LEARNING,
    STAGE_NEW,
    STAGE_REVIEW,
    interval_for_step,
)


@dataclass(frozen=True)
class NextState:
    """作答之后该词的新状态。调用方拿去写库即可。"""

    stage: str
    step: int
    due_at: str | None     # 下次到期日 YYYY-MM-DD
    correct_streak: int    # 连续答对次数
    lapses: int            # 累计答错次数


def next_state(
    *,
    stage: str,
    step: int,
    correct_streak: int,
    lapses: int,
    rating: str,
    today: date | None = None,
) -> NextState:
    """按当前状态和本次作答结果，算出下一个状态。"""
    today = today or date.today()

    # ---------- 答错：统一降级回炉 ----------
    if rating == RATING_UNKNOWN:
        if stage in (STAGE_REVIEW, STAGE_GRADUATED):
            # 退两级，但最低退到第 1 级；从"毕业"掉下来也按复习队列处理
            new_step = max(1, step - LAPSE_DEMOTE_STEPS)
            return NextState(
                stage=STAGE_REVIEW,
                step=new_step,
                due_at=_iso(today + timedelta(days=1)),
                correct_streak=0,
                lapses=lapses + 1,
            )
        # 还在 new / learning 阶段答错：今天先过关，不计入复习失败次数
        return NextState(
            stage=STAGE_LEARNING,
            step=0,
            due_at=_iso(today),   # 到期日就是今天，表示"本场还要再见一次"
            correct_streak=0,
            lapses=lapses,
        )

    # ---------- 模糊：不升级也不降级，明天再来 ----------
    if rating == RATING_FUZZY:
        if stage in (STAGE_REVIEW, STAGE_GRADUATED):
            return NextState(
                stage=STAGE_REVIEW,
                step=max(1, step),
                due_at=_iso(today + timedelta(days=1)),
                correct_streak=0,   # 模糊会打断"连续答对"的计数
                lapses=lapses,
            )
        # 学习阶段模糊：留在当天队列里再过一次
        return NextState(
            stage=STAGE_LEARNING,
            step=0,
            due_at=_iso(today),
            correct_streak=0,
            lapses=lapses,
        )

    # ---------- 认识（答对）----------
    if stage in (STAGE_NEW, STAGE_LEARNING):
        # 当天过关，进入复习阶梯第 1 级，明天开始复习
        return NextState(
            stage=STAGE_REVIEW,
            step=1,
            due_at=_iso(today + timedelta(days=1)),
            correct_streak=correct_streak + 1,
            lapses=lapses,
        )

    if stage == STAGE_GRADUATED:
        # 毕业后的抽查，答对就再往后推一轮
        return NextState(
            stage=STAGE_GRADUATED,
            step=step,
            due_at=_iso(today + timedelta(days=GRADUATED_CHECK_DAYS)),
            correct_streak=correct_streak + 1,
            lapses=lapses,
        )

    # 复习阶梯里答对：升级；已经到最高级就毕业
    next_step = step + 1
    if next_step > GRADUATE_STEP:
        return NextState(
            stage=STAGE_GRADUATED,
            step=GRADUATE_STEP,
            due_at=_iso(today + timedelta(days=GRADUATED_CHECK_DAYS)),
            correct_streak=correct_streak + 1,
            lapses=lapses,
        )

    return NextState(
        stage=STAGE_REVIEW,
        step=next_step,
        due_at=_iso(today + timedelta(days=interval_for_step(next_step))),
        correct_streak=correct_streak + 1,
        lapses=lapses,
    )


def _iso(value: date) -> str:
    return value.isoformat()
