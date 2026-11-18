# -*- coding: utf-8 -*-
"""L3 匮乏 → L4 四维动机；连续，无阈值。"""
from __future__ import annotations

from .action_arbiter import Motives


def motives(h) -> Motives:
    connection = h.value("Connection")
    trust = h.value("Trust")
    safety = h.value("Safety")
    threat = h.value("Threat")
    boredom = h.value("Boredom")
    fatigue = h.value("Fatigue")
    energy = h.value("Energy")
    return Motives(
        approach=(1.0 - connection) * (0.5 + 0.5 * trust),
        avoid=max(1.0 - safety, threat),
        explore=boredom * (1.0 - fatigue),
        idle=max(1.0 - energy, fatigue),
    )
