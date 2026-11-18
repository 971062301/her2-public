# -*- coding: utf-8 -*-
"""客观回应质量：只读可测事实，不读 LLM 文本。

LLM 无权读写 quality；它只能产生台词，quality 由外部规则引擎算。
"""
from __future__ import annotations


def _clamp(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(x)))


def objective_quality(latency_s: float = 0.0, reply_len: int = 0,
                      asked_back: bool = False, left: bool = False) -> float:
    """返回 -1..1；只依赖延迟/长度/是否追问/是否离开。"""
    if left:
        return -1.0
    slow = min(1.0, max(0.0, float(latency_s)) / 3600.0)
    rich = min(1.0, max(0, int(reply_len)) / 50.0)
    q = 0.6 - 0.8 * slow + 0.4 * rich + (0.3 if asked_back else 0.0)
    return _clamp(q)
