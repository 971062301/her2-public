# -*- coding: utf-8 -*-
"""L0：反射与无意识表达层。

- 命中高频词/重复/日常废话 → 直接模板，不走 L1/意向/LLM；
- 模板按当前 PAD 选（高 P 暖、低 P 冷）；
- Autonomy 极低 + Fear 极高 → hold（死寂）；
- 没命中 → 返回 None，交回慢思考。
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class Reflex:
    text: str
    weight: float = 1.0
    hits: int = 0
    relation_kind: str = "any"
    kind: str = "innate"        # innate / habit
    success: int = 0

    def worth(self) -> bool:
        return self.weight >= 0.2


class L0:
    def __init__(self, learn_after: int = 5) -> None:
        self.dict: dict[str, Reflex] = {}
        self.pending: dict[str, int] = {}
        self.learn_after = int(learn_after)
        self.hits = 0

    def add(self, text: str, weight: float = 1.0,
            relation_kind: str = "any", kind: str = "innate") -> None:
        self.dict[text] = Reflex(text, weight, relation_kind=relation_kind, kind=kind)

    def learn(self, text: str, relation_kind: str = "any",
              outcome: float = 1.0) -> None:
        """习惯：同一输入在同一关系下反复有正结果，才固化。"""
        t = str(text or "").strip()
        if not t or len(t) > 12:
            return
        if outcome <= 0:
            return
        key = f"{relation_kind}|{t}"
        self.pending[key] = self.pending.get(key, 0) + 1
        if self.pending[key] >= self.learn_after:
            self.add(t, 1.0, relation_kind=relation_kind, kind="habit")
            self.pending[key] = 0

    def feedback(self, text: str, was_right: bool) -> None:
        """误判就降权；太低就剔除（脱敏）。"""
        r = self.dict.get(text)
        if not r:
            return
        r.weight = max(0.0, r.weight * (1.0 if was_right else 0.5))
        if not r.worth():
            self.dict.pop(text, None)

    def decay(self, dt: float, tau: float = 86400.0) -> None:
        """习惯不用会消退；天生的词典不衰减。"""
        for t, r in list(self.dict.items()):
            if r.kind != "habit":
                continue
            r.weight *= max(0.0, 1.0 - max(0.0, dt) / max(1e-6, tau))
            if not r.worth():
                self.dict.pop(t, None)

    @staticmethod
    def _reply(P: float, energy: float = 0.7, stress: float = 0.0) -> str:
        if stress > 0.6:
            return "干嘛？" if energy >= 0.5 else "别烦我"
        if energy < 0.3:
            return "……"
        if P >= 0.15:
            return "在呢" if energy >= 0.5 else "嗯"
        if P >= -0.15:
            return "怎么啦"
        return "哦"

    def try_respond(self, text: str, state: dict,
                    relation: dict | None = None,
                    recent: list[str] | None = None,
                    cognitive_load: float = 0.0) -> dict | None:
        if cognitive_load > 0 and random.random() < max(0.0, min(1.0, cognitive_load)):
            return None      # 认知负荷高：反射被抑制的概率连续上升
        t = str(text or "").strip()
        if not t:
            return None
        autonomy = float(state.get("Autonomy", 0.8))
        fear = float(state.get("Fear", state.get("Stress", 0.0)))
        energy = float(state.get("Energy", 0.7))
        stress = float(state.get("Stress", fear))
        p = float(state.get("P", 0.0))

        # 极端压制：连反射都不走
        if (1.0 - autonomy) * fear > 0.6:
            self.hits += 1
            return {"mode": "l0", "say": "", "hold": True, "reason": "suppressed"}

        # 词典命中
        kind = str((relation or {}).get("kind") or "any")
        ent = self.dict.get(t)
        if (ent and ent.worth()
                and ent.relation_kind in ("any", kind)):
            ent.hits += 1
            ent.success += 1
            self.hits += 1
            return {"mode": "l0",
                    "say": self._reply(p, energy, stress),
                    "reason": "habit" if ent.kind == "habit" else "lexicon"}

        # 短时间重复同一句
        rep = [x for x in (recent or [])[-4:] if x == t]
        if len(rep) >= 3:
            self.hits += 1
            return {"mode": "l0", "say": "干嘛？", "reason": "repeat"}

        # 日常废话 + 累/烦 → 应付
        dull = (len(t) <= 8 and not any(ch in t for ch in "？！!?"))
        load = 0.6 * (1.0 - max(0.0, min(1.0, energy))) + 0.4 * max(0.0, min(1.0, stress))
        if dull and load > 0.45:
            self.hits += 1
            return {"mode": "l0", "say": self._reply(p, energy, stress),
                    "reason": "autopilot"}
        return None
