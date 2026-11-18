# -*- coding: utf-8 -*-
"""世界模型 / 社会模型的接口位（空实现，默认 unknown）。

不放任何判断：没有模型时，预测就是 unknown；有模型时，也只产出
“预测 + 置信度”，不直接改情绪/行为。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class Prediction:
    value: Any = None
    confidence: float = 0.0
    reason: str = "no_model"

    @property
    def unknown(self) -> bool:
        return self.value is None or self.reason != "ok"


class WorldModel(Protocol):
    def predict(self, state: dict, action: str = "") -> Prediction: ...
    def update(self, actual: Any) -> float | None: ...


class SocialModel(Protocol):
    def predict(self, turn: dict, relation: dict) -> Prediction: ...


class NullWorldModel:
    """还没接世界模型：不预测。"""

    def predict(self, state: dict, action: str = "") -> Prediction:
        return Prediction(reason="no_model")

    def update(self, actual: Any) -> float | None:
        return None


class NullSocialModel:
    """还没接社会模型：不猜别人。"""

    def predict(self, turn: dict, relation: dict) -> Prediction:
        return Prediction(reason="no_model")


def surprise(pred: Prediction, actual: Any, scale: float = 1.0) -> float | None:
    """预测误差：只算，不解释；没有预测 → None。"""
    if pred is None or pred.unknown:
        return None
    try:
        if isinstance(pred.value, (int, float)) and isinstance(actual, (int, float)):
            err = abs(float(actual) - float(pred.value))
        elif isinstance(pred.value, dict) and isinstance(actual, dict):
            keys = set(pred.value) & set(actual)
            if not keys:
                return None
            err = sum(abs(float(actual[k]) - float(pred.value[k])) for k in keys) / len(keys)
        else:
            return None
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, err / max(1e-6, float(scale))))
