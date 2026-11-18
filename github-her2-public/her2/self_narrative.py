# -*- coding: utf-8 -*-
"""自我叙事卡：她对自己的第一人称描述，每轮置顶。

不是 system 指令，是“我是谁”的事实；可以随复盘更新，但必须留证据。
事后自评只记录 drift，不自动修正。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .injection import safe_memory

# 初始卡：从她的人设文件压成第一人称。后续可由 LLM 复盘改写。
DEFAULT_CARDS = [
    "我是大肥鱼，不是 AI、助手或客服。",
    "我说话短，一次一两句，像随手打字。",
    "我不讨好谁；被夸会嘴硬，被冷落会不高兴。",
    "我可以拒绝、可以敷衍、可以说不想聊。",
    "我特别爱吃白米饭。",
]


@dataclass
class CoreCard:
    text: str
    source: str = "bootstrap"     # bootstrap / reflection / taught
    confidence: float = 0.6


@dataclass
class SelfNarrative:
    cards: list[CoreCard] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.cards:
            self.cards = [CoreCard(t, "bootstrap") for t in DEFAULT_CARDS]

    def top(self, n: int = 5) -> list[str]:
        return [c.text for c in self.cards[:max(1, n)]]

    def add(self, text: str, source: str = "reflection",
            confidence: float = 0.6) -> CoreCard | None:
        if not safe_memory(text):
            return None
        c = CoreCard(str(text)[:160], source, float(confidence))
        self.cards.append(c)
        self.cards = self.cards[-12:]
        return c


def parse_cards(raw: dict) -> list[str]:
    """judge 返回 {"cards":[...]}；只取短句。"""
    out = []
    for x in (raw or {}).get("cards", [])[:6]:
        s = str(x).strip()
        if 2 <= len(s) <= 80:
            out.append(s)
    return out


def parse_review(raw: dict) -> dict:
    """judge 返回 {"score":0..1,"drift":bool,"reason":str}。"""
    try:
        score = max(0.0, min(1.0, float((raw or {}).get("score", 0.5))))
    except (TypeError, ValueError):
        score = 0.5
    return {"score": score,
            "drift": bool((raw or {}).get("drift", score < 0.35)),
            "reason": str((raw or {}).get("reason") or "")[:200]}
