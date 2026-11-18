# -*- coding: utf-8 -*-
"""L1 感知层：客观特征 + 粒度污染（不看语义、不贴情绪标签）。

白皮书 §1。
"""


def detail_level(P: float, base: float = 1.0, k: float = 0.5,
                 low: float = 0.3) -> float:
    """越痛苦（P<0）看得越粗；夹在 [low, base]。"""
    P = max(-1.0, min(1.0, float(P)))
    polluted = base * (1.0 - max(0.0, -P) * k)
    return max(low, min(base, polluted))


def facts(schema: dict, P: float) -> dict:
    """按粒度裁掉细节：只留置信度够的特征，不给情绪标签。"""
    keep = detail_level(P)
    out = {}
    for mod, feats in (schema or {}).items():
        if not isinstance(feats, dict):
            continue
        picked = {}
        for k, v in feats.items():
            conf = v if isinstance(v, (int, float)) else 1.0
            if conf >= (1.0 - keep):
                picked[k] = v
        out[mod] = picked
    return out

from dataclasses import dataclass, field


@dataclass
class Signal:
    """通用：一帧感知到的数值事件（身体适配层负责产生）。"""
    kind: str
    value: float = 0.0
    meta: dict = field(default_factory=dict)


def classify_by(rules: list, signals: list[Signal]) -> str:
    """通用规则引擎：rules = [(判定函数, 事件名), ...]，谁先中谁赢。"""
    for pred, name in rules:
        try:
            if pred(signals):
                return str(name)
        except Exception:
            continue
    return "neutral"
