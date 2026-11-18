# -*- coding: utf-8 -*-
"""轻量世界模型：情境 + 动作 → 后果统计。

只记事实，不替她决策。key = context|action。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Prediction:
    n: int = 0
    success: int = 0
    fail: int = 0
    blocked: int = 0
    hp_sum: float = 0.0
    dist_sum: float = 0.0
    boredom_sum: float = 0.0

    @property
    def fail_rate(self) -> float:
        return self.fail / self.n if self.n else 0.0

    @property
    def blocked_rate(self) -> float:
        return self.blocked / self.n if self.n else 0.0

    @property
    def avg_hp(self) -> float:
        return self.hp_sum / self.n if self.n else 0.0

    @property
    def avg_dist(self) -> float:
        return self.dist_sum / self.n if self.n else 0.0

    @property
    def avg_boredom(self) -> float:
        return self.boredom_sum / self.n if self.n else 0.0

    @property
    def expected_pain(self) -> float:
        """0~1：失败、被挡、受伤至少中一个的概率并集；不设阈值。"""
        hurt = min(1.0, max(0.0, -self.avg_hp) / 10.0)
        return 1.0 - (1.0 - self.fail_rate) * (1.0 - self.blocked_rate) * (1.0 - hurt)


class WorldModel:
    def __init__(self) -> None:
        self.table: dict[str, Prediction] = {}

    def observe(self, context: str, action: str, success: bool,
                blocked: bool = False, hp_delta: float = 0.0,
                distance_delta: float = 0.0,
                boredom_delta: float = 0.0) -> Prediction:
        k = f"{context}|{action}"
        p = self.table.setdefault(k, Prediction())
        p.n += 1
        if success:
            p.success += 1
        else:
            p.fail += 1
        if blocked:
            p.blocked += 1
        p.hp_sum += float(hp_delta)
        p.dist_sum += float(distance_delta)
        p.boredom_sum += float(boredom_delta)
        return p

    def predict(self, context: str, action: str) -> Prediction | None:
        return self.table.get(f"{context}|{action}")

    @staticmethod
    def negative(p: Prediction | None) -> bool:
        if not p or p.n <= 0:
            return False
        return p.fail_rate >= 0.5 or p.blocked_rate >= 0.5 or p.avg_hp < -0.5

    def preview(self, context: str, primary: str,
                actions: list[str]) -> list[str]:
        """只有 primary 预计会痛，才把有数据的备选摆出来。"""
        p0 = self.predict(context, primary)
        if not self.negative(p0):
            return self.lines(context, [primary])
        return self.lines(context, [primary] + [a for a in actions if a != primary])

    def lines(self, context: str, actions: list[str]) -> list[str]:
        out = []
        for a in actions:
            p = self.predict(context, a)
            if not p or p.n <= 0:
                continue
            bits = [f"试过 {p.n} 次"]
            if p.success:
                bits.append(f"成功 {p.success} 次")
            if p.avg_dist < -0.5:
                bits.append(f"平均靠近 {abs(p.avg_dist):.1f} 格")
            if p.fail_rate >= 0.5:
                bits.append(f"失败率 {p.fail_rate:.0%}")
            if p.blocked_rate >= 0.5:
                bits.append("常被挡住")
            if p.avg_hp < -0.5:
                bits.append(f"平均掉血 {abs(p.avg_hp):.1f}")
            if abs(p.avg_boredom) >= 0.05:
                bits.append(f"平均无聊变化 {p.avg_boredom:+.2f}")
            bits.append(f"预计痛觉 {p.expected_pain:.2f}")
            out.append(f"用 {a}：" + "，".join(bits))
        return out
