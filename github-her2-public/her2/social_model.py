# -*- coding: utf-8 -*-
"""关系预测器：预测基于锚点（承诺/模式），误差喂回内稳态。

注意：Surprise 不直接加到 Stress（Stress 是派生量）；
它先改 Safety/Trust，Stress 由公式自己涨。
"""
from __future__ import annotations

from .anchors import Anchors
from .predictors import Prediction


class RelationalPredictor:
    def __init__(self, anchors: Anchors | None = None) -> None:
        self.anchors = anchors or Anchors()
        self.last: dict | None = None

    def predict(self, turn: dict, relation: dict) -> Prediction:
        who = str((relation or {}).get("id") or "")
        if not who:
            return Prediction(reason="no_who")
        pending = self.anchors.pending(who)
        if pending:
            p = pending[0]
            self.last = {"who": who, "pid": p.id, "check": "promise"}
            return Prediction(value={"check": "promise", "id": p.id,
                                     "what": p.what, "who": who},
                              confidence=0.75, reason="ok")
        n = self.anchors.pattern(who, "reply")
        if n >= 3:
            self.last = {"who": who, "check": "pattern"}
            return Prediction(value={"check": "pattern", "who": who,
                                     "expected": "reply"}, confidence=0.5, reason="ok")
        self.last = None
        return Prediction(reason="no_anchor")

    def observe(self, actual: dict) -> float | None:
        """actual = {"who":..., "came": bool}；返回 0..1 的误差。"""
        if not self.last or not isinstance(actual, dict):
            return None
        if actual.get("who") != self.last.get("who"):
            return None
        if self.last.get("check") != "promise":
            return None
        came = bool(actual.get("came"))
        self.anchors.mark(self.last["pid"], "kept" if came else "broken")
        return 0.0 if came else 1.0


def apply_surprise(h, surprise: float, trust: float) -> tuple[float, float]:
    """误差 → Safety/Trust 变化（连续）；Stress 由 homeostat 派生。"""
    s = max(0.0, min(1.0, float(surprise)))
    t = max(0.0, min(1.0, float(trust)))
    impact = s * (1.2 - 0.5 * t)
    d_safety = -0.15 * impact
    d_trust = -0.10 * impact
    h.change("Safety", d_safety)
    h.change("Trust", d_trust)
    return round(d_safety, 4), round(d_trust, 4)
