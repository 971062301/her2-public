# -*- coding: utf-8 -*-
"""概念卡：LLM 复盘时抽象出的“情境→策略→结果”。

代码不自动生成概念；只负责存、检索、记成败。
失败次数 > 成功次数时，卡自动失效（不再激活）。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .injection import safe_memory

EXECUTABLE = {"forward", "back", "left", "right", "jump", "follow",
              "go_to", "go_to_place", "stop", "look", "eat", "work",
              "mine", "chop"}


@dataclass
class ConceptCard:
    concept_id: str
    concept_name: str
    signs: list[str] = field(default_factory=list)
    action: str = ""
    outcome: str = ""
    success_count: int = 0
    fail_count: int = 0
    source: str = "reflection"
    deprecated: bool = False

    @property
    def executable(self) -> bool:
        return self.action in EXECUTABLE

    @property
    def active(self) -> bool:
        return not self.deprecated and self.executable

    def record(self, success: bool) -> None:
        if success:
            self.success_count += 1
        else:
            self.fail_count += 1


class ConceptMemory:
    def __init__(self) -> None:
        self.cards: dict[str, ConceptCard] = {}
        self.seq = 0

    def add(self, name: str, signs: list[str], action: str,
            outcome: str = "", source: str = "reflection") -> ConceptCard:
        self.seq += 1
        cid = f"c_{self.seq:03d}"
        c = ConceptCard(cid, str(name)[:80],
                        [str(s)[:80] for s in signs][:8],
                        str(action)[:80], str(outcome)[:120], source=source)
        self.cards[cid] = c
        return c

    def active(self) -> list[ConceptCard]:
        return [c for c in self.cards.values() if c.active]

    def record(self, cid: str, success: bool) -> ConceptCard | None:
        c = self.cards.get(cid)
        if c:
            c.record(success)
        return c

    def retire(self, cid: str) -> ConceptCard | None:
        """她自己在复盘里决定退休；代码不按次数自动判死。"""
        c = self.cards.get(cid)
        if c:
            c.deprecated = True
        return c

    def parse(self, raw: dict) -> list[ConceptCard]:
        """judge 返回 {"concepts":[{name,signs,action,outcome}]}。"""
        out = []
        for x in (raw or {}).get("concepts", [])[:5]:
            try:
                name = str(x.get("name") or "").strip()
                signs = [str(s)[:80] for s in (x.get("signs") or [])][:8]
                action = str(x.get("action") or "").strip()
                if len(name) < 2 or not signs or not action:
                    continue
                if not safe_memory(" ".join([name] + signs + [action])):
                    continue
                out.append(self.add(name, signs, action,
                                    str(x.get("outcome") or "")))
            except Exception:
                continue
        return out

    def deprecated(self) -> list[ConceptCard]:
        return [c for c in self.cards.values() if c.deprecated]

    def activate(self, description: str, judge=None) -> list[ConceptCard]:
        """语义激活：由 LLM 判断当前情境是否命中 signs；没判官就 unknown。"""
        if judge is None:
            return []
        active = self.active()
        if not active:
            return []
        try:
            raw = judge({"description": str(description),
                         "cards": [{"id": c.concept_id, "signs": c.signs}
                                   for c in active]}) or {}
        except Exception:
            return []
        ids = set(raw.get("concept_ids") or [])
        hit = [c for c in active if c.concept_id in ids and not c.deprecated]
        hit.sort(key=lambda c: (-c.success_count, c.fail_count))
        return hit[:4]

    def as_dict(self, cards: list[ConceptCard]) -> list[dict]:
        return [{"id": c.concept_id, "name": c.concept_name,
                 "signs": c.signs, "action": c.action,
                 "outcome": c.outcome,
                 "success": c.success_count, "fail": c.fail_count}
                for c in cards]

    def top(self, n: int = 4) -> list[dict]:
        return [{"id": c.concept_id, "name": c.concept_name,
                 "signs": c.signs, "action": c.action,
                 "outcome": c.outcome,
                 "success": c.success_count, "fail": c.fail_count}
                for c in self.active()[:max(1, n)]]
