# -*- coding: utf-8 -*-
"""经验卡：LLM 复盘时写下的“我学到了什么”，代码只存/召回。

不写反讽字典；卡片内容是模型自己的句子，代码只按字面相关召回。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .injection import safe_memory


def _grams(s: str) -> set[str]:
    s = "".join(ch for ch in str(s) if not ch.isspace())
    return {s[i:i + 2] for i in range(max(0, len(s) - 1))} or {s}


def _sim(a: str, b: str) -> float:
    ga, gb = _grams(a), _grams(b)
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / (len(ga) * len(gb)) ** 0.5


@dataclass
class KnowledgeCard:
    text: str
    tags: list[str] = field(default_factory=list)
    weight: float = 1.0
    hits: int = 0


class KnowledgeStore:
    def __init__(self) -> None:
        self.cards: list[KnowledgeCard] = []

    def add(self, text: str, tags: list[str] | None = None,
            weight: float = 1.0) -> KnowledgeCard | None:
        if not safe_memory(text):
            return None
        c = KnowledgeCard(str(text)[:300], list(tags or []), float(weight))
        self.cards.append(c)
        return c

    def retrieve(self, query: str, k: int = 2) -> list[KnowledgeCard]:
        q = str(query or "")
        scored = []
        for c in self.cards:
            s = max(_sim(q, c.text), max((_sim(q, t) for t in c.tags), default=0.0))
            scored.append((s, c.weight, c))
        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return [c for s, _w, c in scored[:max(0, k)] if s > 0.05]

    def hit(self, card: KnowledgeCard) -> None:
        card.hits += 1
        card.weight = min(3.0, card.weight + 0.05)
