# -*- coding: utf-8 -*-
"""对“某个人”的态度（与全局 Homeostat 分开）。

- 全局 Homeostat：心情/身体，对谁都一样；
- Relation：对他这个人的 trust/closeness/regard，慢变；
- 同一句话先落到 Relation，再按 leak 比例渗到全局。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Relation:
    id: str
    name: str = ""
    kind: str = "stranger"      # owner / stranger / group
    trust: float = 0.5
    closeness: float = 0.2
    regard: float = 0.0         # -1 看低 … +1 看重
    suspicion: float = 0.0      # 0..1 身体记忆：对这个人“话里有话”的防备
    last_at: float = 0.0
    events: int = 0
    notes: list[str] = field(default_factory=list)

    def clamp(self) -> None:
        for k in ("trust", "closeness"):
            setattr(self, k, max(0.0, min(1.0, float(getattr(self, k)))))
        self.regard = max(-1.0, min(1.0, float(self.regard)))
        self.suspicion = max(0.0, min(1.0, float(self.suspicion)))

    def context(self) -> dict:
        """给 R0 的“关系上下文”，不是给 LLM 的情绪结论。"""
        return {"id": self.id, "kind": self.kind,
                "trust": round(self.trust, 3),
                "closeness": round(self.closeness, 3),
                "regard": round(self.regard, 3),
                "suspicion": round(self.suspicion, 3),
                "known": self.events > 0}


class Relations:
    def __init__(self, base_leak: float = 0.10, factor: float = 0.80) -> None:
        self.map: dict[str, Relation] = {}
        self.base_leak = float(base_leak)
        self.factor = float(factor)

    def get(self, rid: str, name: str = "", kind: str = "stranger") -> Relation:
        r = self.map.get(rid)
        if r is None:
            r = Relation(rid, name or rid, kind)
            self.map[rid] = r
        elif name:
            r.name = name
        return r

    def update(self, rid: str, *, trust: float = 0.0,
               closeness: float = 0.0, regard: float = 0.0) -> Relation:
        r = self.get(rid)
        r.trust += trust
        r.closeness += closeness
        r.regard += regard
        r.events += 1
        r.clamp()
        return r

    def leak_for(self, closeness: float) -> float:
        """越亲近，渗透越大；连续，不是常数。"""
        return max(0.0, min(0.95, self.base_leak + self.factor * float(closeness)))

    def apply_event(self, rid: str, *, trust: float = 0.0,
                    closeness: float = 0.0) -> tuple[Relation, float, float]:
        """事件先落 Relation，再按 leak 渗全局；返回 (关系, 全局trust, 全局closeness)。"""
        r = self.update(rid, trust=trust, closeness=closeness)
        leak = self.leak_for(r.closeness)
        return r, trust * leak, closeness * leak

    def global_leak(self, trust: float = 0.0, closeness: float = 0.0,
                    closeness_level: float = 0.0) -> tuple[float, float]:
        leak = self.leak_for(closeness_level)
        return trust * leak, closeness * leak

    def decay(self, dt: float, tau: float = 86400.0) -> None:
        """向基线回落，不是归零：信任回 0.5，亲近回 0.2，怀疑/看重回 0。"""
        k = min(1.0, max(0.0, dt) / max(1e-6, tau))
        for r in self.map.values():
            r.trust += (0.5 - r.trust) * k
            r.closeness += (0.2 - r.closeness) * k
            r.regard += (0.0 - r.regard) * k
            r.suspicion += (0.0 - r.suspicion) * k
            r.clamp()
