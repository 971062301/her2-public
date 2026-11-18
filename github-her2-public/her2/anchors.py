# -*- coding: utf-8 -*-
"""锚点记忆：承诺、互动模式、语境。

预测必须基于锚点，不能凭空猜。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Promise:
    id: str
    who: str
    what: str
    status: str = "pending"      # pending / kept / broken
    at: float = 0.0


class Anchors:
    def __init__(self) -> None:
        self.promises: list[Promise] = []
        self.patterns: dict[tuple[str, str], int] = {}

    def add_promise(self, pid: str, who: str, what: str, at: float = 0.0) -> Promise:
        p = Promise(pid, who, what, "pending", at)
        self.promises.append(p)
        return p

    def pending(self, who: str) -> list[Promise]:
        return [p for p in self.promises if p.who == who and p.status == "pending"]

    def mark(self, pid: str, status: str) -> None:
        if status not in ("kept", "broken"):
            raise ValueError("status 只能是 kept/broken")
        for p in self.promises:
            if p.id == pid:
                p.status = status
                return

    def note_pattern(self, who: str, kind: str) -> int:
        key = (who, kind)
        self.patterns[key] = self.patterns.get(key, 0) + 1
        return self.patterns[key]

    def pattern(self, who: str, kind: str) -> int:
        return self.patterns.get((who, kind), 0)
