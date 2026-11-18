# -*- coding: utf-8 -*-
"""巩固：睡眠/挂机时，把高频负面经验固化成 L0 反射。"""
from __future__ import annotations


def consolidate(events: list[dict], l0, min_count: int = 3,
                max_add: int = 10) -> list[str]:
    """events = [{text, P, weight, charge}]。

    - 弱事件：同一文本高频 >= min_count 才固化；
    - 强事件：|charge| >= 0.8，单次就固化（创伤通道）。
    """
    counts: dict[str, int] = {}
    strong: dict[str, float] = {}
    for e in events or []:
        t = str(e.get("text") or "").strip()
        if not t or len(t) > 6:
            continue
        charge = abs(float(e.get("charge", 0.0)))
        if charge >= 0.8:
            strong[t] = max(strong.get(t, 0.0), charge)
            continue
        if float(e.get("P", 0.0)) < 0 or float(e.get("weight", 0.0)) >= 0.6:
            counts[t] = counts.get(t, 0) + 1
    added = []
    for t, charge in sorted(strong.items(), key=lambda kv: kv[1], reverse=True):
        if t not in l0.dict:
            l0.add(t, min(1.0, 0.5 + 0.3 * charge))
            added.append(t)
        if len(added) >= max_add:
            return added
    for t, n in sorted(counts.items(), key=lambda kv: kv[1], reverse=True):
        if n >= min_count and t not in l0.dict:
            l0.add(t, min(1.0, 0.3 + 0.1 * n))
            added.append(t)
        if len(added) >= max_add:
            break
    return added
