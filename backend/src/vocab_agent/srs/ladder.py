"""复习间隔阶梯（对标不背单词的行为逻辑）。

【为什么不照抄不背单词的具体天数】
它的间隔是内部参数、没有公开。硬猜它的数字没有意义，
所以我们还原的是它的行为逻辑：
    新词 -> 当天学会 -> 间隔逐级拉长 -> 连续答对到顶级就毕业
    答错就降级回炉
参数全部集中在下面几个常量里，觉得太快或太慢，直接改这里。
"""

from __future__ import annotations

# 复习阶梯：第 N 级表示"这次答对之后，隔多少天再见面"。
# 下标 0 是占位（不存在"0 级"），真正用到的是 1 到 7。
# 语义上就是 1 天 -> 2 天 -> 4 天 -> 一周 -> 半月 -> 一月 -> 两月
REVIEW_INTERVALS_DAYS: tuple[int, ...] = (0, 1, 2, 4, 7, 15, 30, 60)

# 最高级别。到达这一级并且答对，就算毕业（离开主队列）
GRADUATE_STEP = len(REVIEW_INTERVALS_DAYS) - 1

# 答错时往回退几级。退太多容易挫败，退太少又记不牢，取 2 是个折中
LAPSE_DEMOTE_STEPS = 2

# 毕业之后的抽查间隔（天）。毕业不等于永远不见，偶尔回来看一眼
GRADUATED_CHECK_DAYS = 60

# 学习阶段的四种状态，含义写清楚，避免各模块理解不一致：
#   new        还没学过，等第一次学习
#   learning   今天正在学、还没过关（当天要再过一次）
#   review     已进入复习阶梯
#   graduated  已毕业，之后只做不定期抽查
STAGE_NEW = "new"
STAGE_LEARNING = "learning"
STAGE_REVIEW = "review"
STAGE_GRADUATED = "graduated"

# 三种作答结果：
#   known     认识（答对）
#   fuzzy     模糊（有印象但不确定：不升级，明天再来）
#   unknown   不认识（答错：降级回炉）
RATING_KNOWN = "known"
RATING_FUZZY = "fuzzy"
RATING_UNKNOWN = "unknown"


def interval_for_step(step: int) -> int:
    """第 step 级对应的间隔天数。超出范围时按最低或最高级处理，不抛异常。"""
    if step < 1:
        return REVIEW_INTERVALS_DAYS[1]
    if step > GRADUATE_STEP:
        return REVIEW_INTERVALS_DAYS[GRADUATE_STEP]
    return REVIEW_INTERVALS_DAYS[step]
