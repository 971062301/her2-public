# -*- coding: utf-8 -*-
"""R1 的接口契约：把“语气猜测”转成离散表层特征。

- 猜测必须带证据；没证据 → confidence=0；
- 关系只当先验（改猜测倾向），不改任何测量值；
- 连续 confidence → 连续的表层区间，不写死“几个省略号”。
"""
from __future__ import annotations

from dataclasses import dataclass, field

LABELS = ("neutral", "possible_edge")
PARTICLES = "呢呀嘛哦吧啊啦"


@dataclass
class ToneGuess:
    label: str = "neutral"
    confidence: float = 0.0
    evidence: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.label not in LABELS:
            raise ValueError(f"label 只能是 {LABELS}")
        self.confidence = max(0.0, min(1.0, float(self.confidence)))
        if not self.evidence:
            self.confidence = 0.0        # 没来源锚点，不算数

    def with_prior(self, trust: float) -> "ToneGuess":
        """关系只影响猜测倾向，不改测量值。"""
        bias = 1.0 + 0.2 * (0.7 - max(0.0, min(1.0, float(trust))))
        return ToneGuess(self.label, self.confidence * bias, list(self.evidence))


@dataclass
class Surface:
    max_chars: int
    ellipsis_max: int
    allow_particle: bool
    allow_address: bool


def surface_targets(g: ToneGuess) -> Surface:
    """连续映射：confidence 越高，句子越短、省略号越多、语气词/称呼越少。"""
    c = g.confidence if g.label == "possible_edge" else 0.0
    return Surface(
        max_chars=int(round(30 - 18 * c)),
        ellipsis_max=int(round(2 * c)),
        allow_particle=c < 0.6,
        allow_address=c < 0.5,
    )


def validate_surface(say: str, s: Surface) -> list[str]:
    """越界就报出来；不在这里改句子。"""
    out = []
    if len(say) > s.max_chars + 2:
        out.append(f"len>{s.max_chars}")
    if say.count("…") + say.count("...") > s.ellipsis_max:
        out.append(f"ellipsis>{s.ellipsis_max}")
    if not s.allow_particle and any(ch in PARTICLES for ch in say):
        out.append("particle")
    return out


def rule_tone(feats: dict, context_edge: bool = False) -> ToneGuess:
    """确定性规则版 R1：只从读数算，不调 LLM；证据可查。"""
    score = 0.0
    ev: list[str] = []
    if float(feats.get("ellipsis", 0)) >= 1:
        score += 0.25
        ev.append("ellipsis")
    if float(feats.get("len", 0)) <= 6:
        score += 0.15
        ev.append("short")
    if float(feats.get("repeat_run", 0)) >= 2:
        score += 0.15
        ev.append("repeat_run")
    if float(feats.get("punct_ratio", 0)) >= 0.25:
        score += 0.10
        ev.append("punct_ratio")
    if context_edge:
        score += 0.25
        ev.append("context_edge")
    conf = min(0.9, score)
    label = "possible_edge" if conf >= 0.4 else "neutral"
    return ToneGuess(label, conf, ev)


def render_surface(s: Surface, base: str = "在") -> str:
    """模板版：只按 surface 拼，不经过 LLM（对照组 A）。"""
    say = base
    if not s.allow_particle:
        say = say.replace("呢", "").replace("呀", "")
    if s.ellipsis_max:
        say = "…" * s.ellipsis_max + say
    if len(say) > s.max_chars + 2:
        say = say[:s.max_chars]
    return say
