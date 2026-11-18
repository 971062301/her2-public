# -*- coding: utf-8 -*-
"""TADM 式做梦：Capture → Consolidate → Synthesize → Integrate。

借机制，不借符号：读连续情绪变量，产候选，不直接改长期记忆。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Episode:
    text: str
    charge: float = 0.0
    at: float = 0.0


@dataclass
class DreamResult:
    captured: list[Episode] = field(default_factory=list)
    consolidated: str = ""
    synthesized: list[str] = field(default_factory=list)
    integrated: list[str] = field(default_factory=list)
    tokens_used: int = 0


# [后天] 梦的内容来自经历；循环结构是[先天]的
class DreamCycle:
    """每轮做梦有 token 预算，防止内省跑飞。"""

    def __init__(self, budget_tokens: int = 200, max_items: int = 5) -> None:
        self.budget = max(0, int(budget_tokens))
        self.max_items = max(0, int(max_items))

    @staticmethod
    def _cost(text: str) -> int:
        # 中文按字算，保守 1 字 ≈ 1 token
        return len(str(text or ""))

    def capture(self, episodes: list[Episode], P: float) -> list[Episode]:
        """按 |电荷| + 负 P 的显著性选材（不排序情绪，只选材）。"""
        scored = []
        for e in episodes:
            base = abs(float(e.charge))
            bias = max(0.0, -float(P)) * (1.0 if e.charge < 0 else 0.0)
            scored.append((base + bias, e))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:self.max_items]]

    def consolidate(self, picked: list[Episode]) -> str:
        if not picked:
            return ""
        return "；".join(e.text[:40] for e in picked[:self.max_items])

    def synthesize(self, summary: str, P: float, A: float) -> list[str]:
        """符号化候选：不调 LLM；用状态给候选加一句“体感”。"""
        if not summary:
            return []
        tone = ("发闷" if P < -0.3 else "轻" if P > 0.3 else "平")
        edge = "绷着" if A > 0.5 else "松"
        cand = f"这阵子（{tone}/{edge}）：{summary}"
        out = []
        used = 0
        for piece in (cand,):
            c = self._cost(piece)
            if used + c > self.budget:
                piece = piece[:max(0, self.budget - used)]
                c = self._cost(piece)
            if piece:
                out.append(piece)
                used += c
        return out

    def integrate(self, cands: list[str]) -> list[str]:
        """只返回候选，不写长期记忆；写不写由上层决定。"""
        return [c for c in cands if c.strip()][:self.max_items]

    def run(self, episodes: list[Episode], P: float, A: float) -> DreamResult:
        r = DreamResult()
        r.captured = self.capture(episodes, P)
        r.consolidated = self.consolidate(r.captured)
        r.synthesized = self.synthesize(r.consolidated, P, A)
        r.integrated = self.integrate(r.synthesized)
        r.tokens_used = sum(self._cost(x) for x in r.synthesized)
        return r
