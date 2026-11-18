# -*- coding: utf-8 -*-
"""教她：老师只能安排「经历」，不能直接写权重/感受。

- 一条 Lesson = 一串结构化事件 + 间隔；
- 她照旧用 L2 的赫布规则学；
- 教出来的痕迹标 source="taught"，和真实经历分开记账。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Step:
    kind: str                 # 事件类型（如 harm_from_distance / comfort）
    base_delta: float = -0.05  # 未学习时的身体变化
    dt_after: float = 600.0    # 事件后让基线回归跑多久


@dataclass
class Lesson:
    name: str
    steps: list[Step] = field(default_factory=list)
    stories: list[str] = field(default_factory=list)   # 只记场景，不记感受


# 示例课程：被冷落几次，然后被安抚
LESSON_COLD_THEN_COMFORT = Lesson("被冷落再被安抚", [
    Step("hp_decrease", -0.05, 600),
    Step("hp_decrease", -0.05, 600),
    Step("hp_decrease", -0.05, 600),
    Step("healed_by_owner", +0.06, 600),
])


def teach(l2, lesson: Lesson) -> list[dict]:
    """按课程喂事件；不直接改 w，只让 l2 自己学。"""
    out = []
    for st in lesson.steps:
        rec = l2.event(st.kind, st.base_delta, source="taught")
        rec["source"] = "taught"
        out.append(rec)
        l2.tick(st.dt_after)
    return out
