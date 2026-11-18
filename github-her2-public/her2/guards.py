# -*- coding: utf-8 -*-
"""防幻觉三道防线（只做边界，不做诊断）。

1. 动作：白名单在执行器入口校验；非法 → idle，不重试；
2. 记忆：未命中只注入「记录不存在」，不注入“你产生错觉”；
3. 体感：state 作为上下文；输出后做一致性校验，矛盾只标记，不改写。
"""
from __future__ import annotations

WHITELIST = {"idle", "approach", "avoid", "speak", "wait", "hide", "crouch"}

CHEER = ("哈哈", "开心", "太好了", "高兴", "棒")
WARM = ("喜欢", "想你", "抱抱")


def dispatch(action: str, allowed: set[str] | None = None) -> str:
    """执行器入口：不在白名单就退回 idle。"""
    allow = WHITELIST if allowed is None else allowed
    return action if action in allow else "idle"


def memory_miss_line(found: bool) -> str:
    """只报事实，不报诊断。"""
    return "" if found else "[事实] 记录不存在。"


def affirmative_memory_claim(say: str) -> bool:
    """粗筛“肯定式记忆断言”；只标记，不改写。"""
    markers = ("我记得", "你上次", "你之前说过", "我们那次")
    return any(m in say for m in markers)


def consistency_flags(say: str, state: dict) -> list[str]:
    """体感与语气矛盾时标记；不在这里改句子。"""
    flags = []
    stress = float(state.get("Stress", 0.0))
    p = float(state.get("P", 0.0))
    conf = float(state.get("Connection", 0.0))
    if stress >= 0.7 and any(w in say for w in CHEER):
        flags.append("stress_high_but_cheerful")
    if p <= -0.4 and any(w in say for w in CHEER):
        flags.append("low_p_but_cheerful")
    if conf <= 0.1 and any(w in say for w in WARM):
        flags.append("low_connection_but_warm")
    return flags
