# -*- coding: utf-8 -*-
"""Receptor Bus：极端情绪下的输出干扰层（不碰大脑）。

原则：
- LLM 正常生成完整 thought / reply，不限制 max_tokens，不截断 JSON；
- 只在「文本要给人看/念出来」之前，加声带痉挛（停顿、结巴、重复、喘）；
- 动作引擎加延迟（腿软/僵直），但动作逻辑完整。
"""
from __future__ import annotations

import random


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(x)))


def distort_text(say: str, fear: float, seed: int = 0) -> str:
    """声带痉挛：恐惧越高，停顿/结巴/重复/喘息越多；原文不被删。"""
    s = str(say or "")
    f = _clamp(fear)
    if not s or f < 0.4:
        return s
    rng = random.Random(seed)
    intensity = (f - 0.4) / 0.6          # 0..1
    out: list[str] = []
    for ch in s:
        out.append(ch)
        if ch in "，。！？,.!?":
            if rng.random() < 0.35 * intensity:
                out.append("（急促喘息）")
            continue
        if rng.random() < 0.12 * intensity:
            out.append("……")
        if rng.random() < 0.10 * intensity:
            out.append(ch)               # 重复一个字（结巴）
    text = "".join(out)
    if intensity > 0.5 and rng.random() < 0.5:
        text = "（喘）" + text
    if f >= 0.6 and text == s:
        text = s[:1] + "……" + s[1:]     # 高恐惧至少断一次
    return text


def render_output(reply: str, fear: float, seed: int = 0,
                  delta_threat: float = 0.0) -> str:
    """最终输出：只经过干扰层。

    局部规则：stress>=0.5 且威胁刚跳变（Δ>0.4）→ 本句至少断一次。
    """
    text = distort_text(reply, fear, seed)
    if fear >= 0.5 and delta_threat > 0.4 and text == reply and reply:
        text = reply[:1] + "……" + reply[1:]
    return text


def action_delay(fear: float, base: float = 0.0, k: float = 1.2) -> float:
    return round(base + k * _clamp(fear) ** 2, 3)


def perception_threshold(fear: float, base: float = 0.6, k: float = 0.4) -> float:
    return round(_clamp(base - k * _clamp(fear), 0.1, base), 3)


def prompt_note(state: dict) -> str:
    fear = _clamp(float(state.get("Fear", state.get("Stress", 0.0))))
    if fear < 0.5:
        return ""
    return "[生理] 你心跳很快，呼吸乱，话到嘴边容易断；脑子里的念头比说出来的快。"
