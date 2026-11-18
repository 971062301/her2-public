# -*- coding: utf-8 -*-
"""Calibration 是**评测仪器**，不是她的记忆/规则。

它回答："R0 对这句话的判断，和人类共识差多远？"
它不回答："这句话应该判对齐还是不对齐？"

校准结果只用于评估 R0 的感知质量，**禁止**：
- 写入她的规则；
- 驱动 Trust/Stress；
- 存进 knowledge。

真正让她学会"这句话对这个人是什么意思"的，是交互结果：
他笑了 / 他冷了 / 他接了 / 他没接。
这些按 user_id 累积，存在 suspicion / trust / knowledge 里。
新关系默认 unknown，先观察，不套旧规则。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median

LABEL_SCORE = {"对齐": 0.0, "中性": 0.5, "不对齐": 1.0}
ALIASES = {"合适": "对齐", "不合适": "不对齐"}
DISAGREE_MAX = 0.34          # = 多数派占比 < 0.66
PROVISIONAL_MAX = 5
FORMAL_MIN = 10
PROVISIONAL_CAP = 0.50
LEXICAL_CAP = 0.60
CONTEXT_CAP = 0.85
MAX_ERROR = 0.25
DRIFT_LIMIT = 2


@dataclass
class Observation:
    item: str
    label: str
    at: float = 0.0


class Calibration:
    def __init__(self) -> None:
        self.obs: list[Observation] = []
        self.drift: dict[str, int] = {}
        self.frozen: set[str] = set()

    def add(self, item: str, label: str) -> None:
        label = ALIASES.get(label, label)
        if label not in LABEL_SCORE:
            raise ValueError(f"label 只能是 {tuple(LABEL_SCORE)}")
        self.obs.append(Observation(str(item), label))

    def counts(self, item: str) -> dict[str, int]:
        out = {k: 0 for k in LABEL_SCORE}
        for o in self.obs:
            if o.item == item:
                out[o.label] += 1
        return out

    def n(self, item: str) -> int:
        return sum(self.counts(item).values())

    def majority(self, item: str) -> tuple[str, float]:
        c = self.counts(item)
        n = sum(c.values())
        if n == 0:
            return "", 0.0
        label = max(c, key=c.get)
        return label, c[label] / n

    def disagreement(self, item: str) -> float:
        _label, share = self.majority(item)
        return 0.0 if share == 0 else 1.0 - share

    def human_score(self, item: str) -> float | None:
        vals = sorted(LABEL_SCORE[o.label] for o in self.obs if o.item == item)
        return float(median(vals)) if vals else None

    def state(self, item: str) -> str:
        n = self.n(item)
        if n < 3:
            return "uncalibrated"
        if n < FORMAL_MIN:
            return "provisional"
        return "formal"

    def _cap(self, item: str, source: str) -> float:
        if self.state(item) == "provisional":
            return PROVISIONAL_CAP
        return LEXICAL_CAP if source == "lexical_template" else CONTEXT_CAP

    def report(self, item: str) -> dict | None:
        """只暴露“人类有多一致”，不暴露标准答案 label。"""
        if self.n(item) == 0:
            return None
        maj, share = self.majority(item)
        return {"n": self.n(item),
                "consensus_rate": round(share, 4),
                "human_variance": round(1.0 - share, 4)}

    def score(self, item: str, rule_score: float, source: str = "context") -> dict:
        if item in self.frozen:
            return {"label": "unknown", "score": 0.0, "reason": "rule_frozen"}
        if self.state(item) == "uncalibrated":
            return {"label": "unknown", "score": 0.0, "reason": "calibration_failed"}
        if self.disagreement(item) > DISAGREE_MAX:
            return {"label": "unknown", "score": 0.0, "reason": "disagreement"}

        human = self.human_score(item)
        rule_label = min(LABEL_SCORE, key=lambda k: abs(LABEL_SCORE[k] - float(rule_score)))
        maj, _ = self.majority(item)
        if human is None or abs(float(rule_score) - human) > MAX_ERROR or rule_label != maj:
            self.drift[item] = self.drift.get(item, 0) + 1
            if self.drift[item] >= DRIFT_LIMIT:
                self.frozen.add(item)
            return {"label": "unknown", "score": 0.0, "reason": "rule_drift"}
        self.drift[item] = 0

        cap = self._cap(item, source)
        s = max(0.0, min(1.0, float(rule_score)))
        # cap 是置信收缩：保留方向，只压缩离中性的距离
        eff = 0.5 + (s - 0.5) * cap
        return {"label": "ok", "score": round(max(0.0, min(1.0, eff)), 6),
                "reason": source, "state": self.state(item)}

    def admit(self, item: str, alignment, source: str = "context") -> dict:
        """R1 入口：R0 说 unknown 就拒判；否则再走校准闸门。"""
        if alignment is None or getattr(alignment, "unknown", True):
            reason = getattr(alignment, "reason", "unknown")
            return {"label": "unknown", "score": 0.0, "reason": reason}
        r = self.score(item, float(alignment.score), source)
        if r["label"] == "ok":
            r["confidence"] = float(getattr(alignment, "confidence", 0.0))
        return r

    def effects(self, score: float, trust: float) -> tuple[float, float]:
        s = max(0.0, min(1.0, float(score)))
        t = max(0.0, min(1.0, float(trust)))
        d_stress = 0.30 * s * (1.5 - 0.8 * t)
        d_p = -0.20 * s * (1.5 - 0.8 * t)
        return round(d_stress, 4), round(d_p, 4)
