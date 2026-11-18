# -*- coding: utf-8 -*-
"""MC 身体适配：把 MC 的数值（血/饥饿/距离/物品）变成事件类型。

通用件在 perception.py；这里只放「这副身体」的规则。
换屏幕/机械身体时，另写 body_screen.py，不改心智层。
"""
from __future__ import annotations

from .perception import Signal, classify_by


# [先天] MC 身体的感官分类（掉血/距离/物品）
def diff_signals(prev: dict, curr: dict) -> list[Signal]:
    """MC 两帧状态 → 数值事件（掉血/掉饥饿/距离/物品）。"""
    out: list[Signal] = []
    if not isinstance(prev, dict) or not isinstance(curr, dict):
        return out
    hp0, hp1 = float(prev.get("hp", 0)), float(curr.get("hp", 0))
    if hp1 < hp0:
        out.append(Signal("damage", round(hp0 - hp1, 2), {"hp": hp1}))
    elif hp1 > hp0:
        src = "owner" if curr.get("heal_from") == "owner" else "natural"
        out.append(Signal("heal", round(hp1 - hp0, 2),
                          {"hp": hp1, "source": src}))
    f0, f1 = float(prev.get("food", 0)), float(curr.get("food", 0))
    if f1 < f0:
        out.append(Signal("hunger", round(f0 - f1, 2), {"food": f1}))
    p0 = prev.get("players") or {}
    p1 = curr.get("players") or {}
    for name in set(p0) | set(p1):
        d0, d1 = p0.get(name), p1.get(name)
        if d0 is None and d1 is not None:
            out.append(Signal("player_join", float(d1), {"name": name}))
        elif d0 is not None and d1 is None:
            out.append(Signal("player_leave", 0.0, {"name": name}))
        elif d0 is not None and d1 is not None and abs(float(d1) - float(d0)) >= 2:
            out.append(Signal("player_distance", round(float(d1) - float(d0), 2),
                              {"name": name, "dist": float(d1)}))
    i0 = prev.get("items") or {}
    i1 = curr.get("items") or {}
    for item in set(i0) | set(i1):
        c0, c1 = int(i0.get(item, 0)), int(i1.get(item, 0))
        if c1 > c0:
            out.append(Signal("item_gain", c1 - c0, {"item": item}))
        elif c1 < c0:
            out.append(Signal("item_loss", c0 - c1, {"item": item}))
    return out


def classify(signals: list[Signal], far: float = 5.0, near: float = 2.0) -> str:
    """只报客观事件；回血按来源分：生理自愈 vs 主人照顾。"""
    def has(k: str) -> bool:
        return any(s.kind == k for s in signals)

    if has("damage"):
        return "hp_decrease"
    if has("heal"):
        src = next((s.meta.get("source") for s in signals if s.kind == "heal"),
                   "natural")
        return "healed_by_owner" if src == "owner" else "body_regen"
    if has("item_gain"):
        return "item_gain"
    if has("item_loss"):
        return "item_loss"
    for s in signals:
        if s.kind == "player_distance":
            return "distance_increase" if s.value > 0 else "distance_decrease"
    return "neutral"
