# -*- coding: utf-8 -*-
"""空间记忆：地点名 → 坐标/标签。通用，不依赖 MC。

坐标是身体格式；名字/标签是她的记忆。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Place:
    name: str
    x: float
    y: float
    z: float
    tags: list[str] = field(default_factory=list)
    source: str = "told"      # told / visited
    hits: int = 0

    def pos(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)


class PlaceMemory:
    def __init__(self) -> None:
        self.map: dict[str, Place] = {}

    def remember(self, name: str, x: float, y: float, z: float,
                 tags: list[str] | None = None, source: str = "told") -> Place:
        p = Place(str(name), float(x), float(y), float(z), list(tags or []), source)
        self.map[p.name] = p
        return p

    def get(self, name: str) -> Place | None:
        return self.map.get(str(name))

    def find(self, text: str) -> Place | None:
        s = str(text or "")
        for name in self.map:
            if name and name in s:
                return self.map[name]
        return None

    def nearest(self, x: float, z: float) -> Place | None:
        if not self.map:
            return None
        return min(self.map.values(),
                   key=lambda p: (p.x - x) ** 2 + (p.z - z) ** 2)

    def as_list(self, limit: int = 8) -> list[dict]:
        return [{"name": p.name, "pos": [p.x, p.y, p.z],
                 "tags": list(p.tags)} for p in list(self.map.values())[:limit]]

    def first_tagged(self, tag: str) -> Place | None:
        for p in self.map.values():
            if tag in p.tags:
                return p
        return None

    def hit(self, name: str) -> None:
        p = self.map.get(name)
        if p:
            p.hits += 1
