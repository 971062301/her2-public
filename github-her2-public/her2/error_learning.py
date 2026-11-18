# -*- coding: utf-8 -*-
"""L2 潜意识层：Surprise → 结果 的赫布学习（独立模块）。

白皮书 §2。只调映射权重，不直接发情绪。
"""
from __future__ import annotations


class ErrorLearning:
    """简化赫布：w += lr * surprise * outcome，夹在 [w_min, w_max]。"""

    def __init__(self, lr: float = 0.01,
                 bounds: tuple[float, float] = (0.05, 0.8),
                 init: float = 0.2) -> None:
        self.lr = float(lr)
        self.lo, self.hi = bounds
        self.w = float(init)          # 映射权重先验
        self.traces: list[tuple[float, float, float]] = []

    def learn(self, surprise: float, outcome: float) -> float:
        s = max(0.0, min(1.0, float(surprise)))
        o = max(-1.0, min(1.0, float(outcome)))
        self.w += self.lr * s * o
        self.w = max(self.lo, min(self.hi, self.w))
        self.traces.append((s, o, round(self.w, 6)))
        self.traces = self.traces[-200:]
        return self.w

    def apply(self, surprise: float) -> float:
        """Surprise 经权重映射后才允许影响内稳态。"""
        return self.w * max(0.0, min(1.0, float(surprise)))
