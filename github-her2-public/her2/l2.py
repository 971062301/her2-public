# -*- coding: utf-8 -*-
"""L2 赫布闭环：Surprise → 负性事件 的增益学习。

- outcome 是**结构化事件**（冷落/安抚/威胁），不从台词 parse；
- Surprise 由内核算：事件前后身体变量差 / 尺度，归一到 [0,1]；
- 权重锁在 [w_min, w_max]，且有基线回归，不会把 Trust 拉到卡死。
"""
from __future__ import annotations

from dataclasses import dataclass

# [价值表] 结构化事件 → 效价。只从事件/教学来，绝不从台词 parse。
OUTCOME_VALENCE = {
    "hp_decrease": -1.0, "hp_increase": +1.0,
    "body_regen": 0.0, "healed_by_owner": +1.0,
    "item_gain": +0.3, "item_loss": -0.3,
    "distance_increase": 0.0, "distance_decrease": 0.0,
    "neutral": 0.0,
    # 结果/教学用的结构化 outcome（不是感知事件）
    "cold": -1.0, "comfort": +1.0, "threat": -1.0,
    "death": -1.0,
}


@dataclass
class L2Config:
    lr: float = 0.02
    init: float = 0.2
    lo: float = 0.05
    hi: float = 0.8
    scale: float = 0.5          # 事件幅度 → surprise 的尺度


# [先天] 赫布学习规则本身（会学）；[后天] self.w 里的权重（学到的）
class L2:
    """一遍事件：预测 → 事件 → 误差 → 学权重；OFF 时权重冻结。"""

    def __init__(self, homeostat, hebb: bool = True, cfg: L2Config | None = None) -> None:
        self.h = homeostat
        self.hebb = bool(hebb)
        self.cfg = cfg or L2Config()
        # [后天] 这些权重是经历写的
        self.w: dict[str, float] = {k: self.cfg.init for k in OUTCOME_VALENCE}
        self.last_surprise: float = 0.0
        self.accum_surprise: float = 0.0
        self.last_marginal: float = 0.0
        self.counts: dict[str, int] = {}
        self.history: list[str] = []
        self.traces: list[dict] = []

    def gain(self, kind: str) -> float:
        """权重相对先验的放大倍数，夹在 [0.25, 4]。"""
        return max(0.25, min(4.0, self.w.get(kind, self.cfg.init) / self.cfg.init))

    def event(self, kind: str, base_delta: float, source: str = "lived") -> dict:
        """结构化事件：base_delta 是未学习时的身体变化。"""
        valence = OUTCOME_VALENCE.get(kind, 0.0)
        before = self.h.value("Trust")
        self.h.change("Trust", base_delta * self.gain(kind))
        after = self.h.value("Trust")
        surprise = min(1.0, abs(after - before) / max(1e-6, self.cfg.scale))
        self.last_surprise = surprise
        self.accum_surprise += surprise
        self.last_marginal = after - before
        self.counts[kind] = self.counts.get(kind, 0) + 1
        self.history = (self.history + [kind])[-10:]
        if self.hebb and valence:
            self.w[kind] = max(self.cfg.lo, min(
                self.cfg.hi, self.w[kind] + self.cfg.lr * surprise * abs(valence)))
        rec = {"kind": kind, "source": source, "delta": round(after - before, 4),
               "surprise": round(surprise, 4),
               "w": round(self.w.get(kind, 0.0), 4),
               "trust": round(self.h.value("Trust"), 4)}
        self.traces.append(rec)
        self.traces = self.traces[-200:]
        return rec

    def sequence(self, n: int = 3) -> list[str]:
        return list(self.history[-n:])

    def recent_events(self, interval_s: float = 600.0) -> dict[str, object]:
        """结构化摘要：只给结构，不翻译成语义。"""
        kind = max(self.counts, key=self.counts.get) if self.counts else "none"
        return {"type": kind, "count": int(self.counts.get(kind, 0)),
                "last_interval_s": float(interval_s)}

    def learning(self) -> dict[str, float]:
        """给台词层的轨迹量：瞬时 Trust 几乎分不出 ON/OFF，这些能。"""
        return {"accumulated_surprise": round(self.accum_surprise, 4),
                "weight_cold": round(self.w.get("cold", 0.0), 4),
                "last_marginal": round(self.last_marginal, 5),
                "gain": round(self.gain("cold"), 4)}

    def tick(self, dt: float) -> None:
        """基线回归照旧：不学习也会回。"""
        self.h.update(dt)
