# -*- coding: utf-8 -*-
"""L4 前额叶：冲动计算 + 时间衰减（无硬编码动作）。

白皮书 §4。取最大值只是“谁最响”，不是“必须做”。
"""
from __future__ import annotations

import math


def impulses(h: "Homeostat", stress_norm: float | None = None) -> dict[str, float]:
    c = h.value("Connection")
    t = h.value("Trust")
    s = h.value("Safety")
    a = h.value("Autonomy")
    e = h.value("Energy")
    P, A, D = h.pad()
    st = h.stress() if stress_norm is None else max(0.0, min(1.0, stress_norm))

    approach = (0.4 * c + 0.3 * t + 0.3 * (P + 1) / 2) * (1 - st)
    avoid = (0.4 * (1 - s) + 0.3 * (1 - t) + 0.3 * A) * (1 - st)
    idle = 0.6 * st + 0.4 * (1 - e)
    return {"approach": max(0.0, approach),
            "avoid": max(0.0, avoid),
            "idle": max(0.0, idle)}


def decay(weights: dict[str, float], dt: float, tau: float = 60.0) -> dict[str, float]:
    factor = math.exp(-max(0.0, dt) / max(1e-6, tau))
    return {k: v * factor for k, v in weights.items()}
