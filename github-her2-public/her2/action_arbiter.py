# -*- coding: utf-8 -*-
"""动作仲裁层：LLM 只建议，身体由这里选一个动作。

输入：驱力、world_model 预测、可用动作、LLM 建议、最近动作。
输出：永远是一个动作（含 idle），不返回空。

打分权重先写死，跑出数据后再调；LLM 建议只是 bonus，不是决定项。
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class ArbiterInput:
    boredom: float = 0.0
    connection: float = 0.3
    stress: float = 0.0
    energy: float = 0.7
    autonomy: float = 0.8
    suggest: str = ""
    available: tuple[str, ...] = ("idle", "follow", "mine", "explore", "look")
    recent: tuple[str, ...] = ()
    predictions: dict | None = None


class ActionArbiter:
    def expected_value(self, action: str, pred) -> float:
        if pred is None or getattr(pred, "n", 0) <= 0:
            return 0.0
        success = pred.success / max(1, pred.n)
        relief = max(0.0, -pred.avg_boredom) * 0.5
        pain = pred.expected_pain
        return success * 0.4 + relief - pain * 0.5

    def scores(self, x: ArbiterInput) -> dict[str, float]:
        s = {}
        preds = x.predictions or {}
        s["idle"] = 0.25 + (1.0 - x.boredom) * 0.2 + (1.0 - x.stress) * 0.1
        s["follow"] = (1.0 - x.connection) * 0.55 + x.autonomy * 0.1
        s["mine"] = x.boredom * 0.55 + self.expected_value("mine", preds.get("mine"))
        s["explore"] = x.boredom * 0.35 + (1.0 - x.connection) * 0.15
        s["look"] = x.boredom * 0.15
        # 疲惫/低自主：压制动作
        if x.energy < 0.2:
            for a in ("mine", "follow", "explore"):
                s[a] -= 0.5
        s["idle"] += max(0.0, x.energy < 0.2) * 0.4
        # 最近做过，减一点，避免复读
        for a in ("mine", "follow", "explore"):
            if a in x.recent:
                s[a] -= 0.1
        # LLM 建议只是加分
        if x.suggest in s and x.suggest in x.available:
            s[x.suggest] += 0.3
        for a in list(s):
            if a not in x.available:
                s.pop(a, None)
        return s

    def decide(self, x: ArbiterInput) -> str:
        s = self.scores(x)
        if not s:
            return "idle"
        return max(s, key=s.get)


@dataclass
class Motives:
    approach: float = 0.0
    avoid: float = 0.0
    explore: float = 0.0
    idle: float = 0.0


class ActionSelector:
    """L4 动机 → 效用 → 动作；不写 if，idle 合法。

    选择不是每 tick 直接 argmax，而是每个动作有一个连续激活值；
    效用是驱动力，激活值有惯性。这样单次噪声推不动切换。
    """

    def __init__(self, tau: float = 4.0, switch_cost: float = 0.12,
                 stickiness: float = 0.25, commit_tau: float = 8.0) -> None:
        self.tau = max(0.1, float(tau))
        self.switch_cost = max(0.0, float(switch_cost))
        self.stickiness = max(0.0, float(stickiness))
        self.commit_tau = max(0.1, float(commit_tau))
        self._current = ""
        self._duration = 0.0
        self.activation: dict[str, float] = {}
        self.history: list[str] = []
        self._t = 0.0
        self._oneshot_last: dict[str, float] = {}

    ONESHOT = {"jump", "look"}

    RELIEF = {
        "follow": {"approach": 1.0, "explore": 0.1, "idle": 0.0, "avoid": 0.0},
        "mine":   {"approach": 0.1, "explore": 0.9, "idle": 0.0, "avoid": 0.0},
        "back":   {"approach": 0.0, "explore": 0.0, "idle": 0.1, "avoid": 0.9},
        "look":   {"approach": 0.0, "explore": 0.3, "idle": 0.0, "avoid": 0.0},
        "jump":   {"approach": 0.1, "explore": 0.3, "idle": 0.0, "avoid": 0.6},
        "sleep":  {"approach": 0.0, "explore": 0.0, "idle": 1.2, "avoid": 0.2},
        "idle":   {"approach": 0.0, "explore": 0.0, "idle": 1.0, "avoid": 0.1},
    }

    def utility(self, action: str, m: Motives, preds: dict,
                suggest: str = "", recent: tuple = (),
                current: str = "") -> float:
        r = self.RELIEF.get(action, {})
        u = (m.approach * r.get("approach", 0.0)
             + m.avoid * r.get("avoid", 0.0)
             + m.explore * r.get("explore", 0.0)
             + m.idle * r.get("idle", 0.0))
        p = preds.get(action)
        if p is not None and getattr(p, "n", 0) > 0:
            u -= p.expected_pain * 0.5
        if action == suggest:
            u += 0.3
        # 只惩罚“切回最近做过的动作”，不惩罚正在持续的动作
        if action in recent and action != current:
            u -= 0.1
        # 连续切换成本：当前动作有粘性，噪声不足以换招
        if current and action != current:
            u -= self.switch_cost
        return u

    def decide(self, m: Motives, available, preds: dict,
               suggest: str = "", recent: tuple = (),
               current: str = "", dt: float = 1.0) -> str:
        choices = [a for a in available if a in self.RELIEF] or ["idle"]
        self._t += max(0.0, dt)
        # 最近 4 次决策都算“刚做过”，防止 A→B→A→B 振荡
        hist = tuple(self.history[-4:])
        # 承诺随执行时长连续增长；不是阈值，也不是定时器
        if current and current == self._current:
            self._duration += max(0.0, dt)
        else:
            self._current = current
            self._duration = 0.0
        commit = self.stickiness * (1.0 - math.exp(-self._duration / self.commit_tau))
        alpha = 1.0 - math.exp(-max(0.0, dt) / self.tau)
        for a in self.RELIEF:
            target = self.utility(a, m, preds, suggest, hist, current) if a in choices else 0.0
            if a == current and a not in self.ONESHOT:
                target += commit       # 承诺只奖励持续动作
            # 一次性动作：完成后连续不应期，不是 tick 阈值
            if a in self.ONESHOT and a in self._oneshot_last:
                age = max(0.0, self._t - self._oneshot_last[a])
                target -= 0.8 * math.exp(-age / 4.0)
            prev = self.activation.get(a, target)
            self.activation[a] = prev + alpha * (target - prev)
        choice = max(choices, key=lambda a: self.activation[a])
        if choice in self.ONESHOT:
            self._oneshot_last[choice] = self._t
        self.history = (self.history + [choice])[-4:]
        return choice


# 动作声明表：元测试逼“声明”，不逼数值；显式 0 是合法声明。
ACTION_SPECS = {
    "mine":   {"cls": "sustained", "on_running_cost": 0.002, "on_finish_relief": 0.3, "precondition": "target"},
    "jump":   {"cls": "oneshot",   "on_running_cost": 0.0,   "on_finish_relief": 0.05, "precondition": "True"},
    "look":   {"cls": "oneshot",   "on_running_cost": 0.0,   "on_finish_relief": 0.02, "precondition": "True"},
    "follow": {"cls": "sustained", "on_running_cost": 0.0,   "on_finish_relief": 0.0, "precondition": "target_entity"},
    "back":   {"cls": "sustained", "on_running_cost": 0.0,   "on_finish_relief": 0.0, "precondition": "True"},
    "sleep":  {"cls": "sustained", "on_running_cost": 0.0,   "on_finish_relief": 0.5, "precondition": "True"},
    "idle":   {"cls": "nonjob",    "on_running_cost": -0.001, "on_finish_relief": 0.0, "precondition": "True"},
    "speak":  {"cls": "nonjob",    "on_running_cost": None,  "on_finish_relief": 0.02, "precondition": "wake"},
}
