# -*- coding: utf-8 -*-
"""L5 记忆检索：负电荷污染，带上限（白皮书 §5.1）。"""


def pollution(P: float, charge: float, w: float = 0.3, cap: float = 0.5) -> float:
    """P<0 时，负电荷记忆更容易被想起；有 cap，防内耗。"""
    p_neg = max(0.0, -float(P))
    score = p_neg * abs(float(charge)) * w
    return max(-cap, min(cap, score))


def score(base: float, P: float, charge: float, **kw) -> float:
    return float(base) + pollution(P, charge, **kw)


import math


def pad_weight(P: float, A: float, D: float, alpha: float = 1.0,
               bp: float = 0.8, ba: float = 0.4, bd: float = 0.2) -> float:
    """TADM 式检索权重：w ∝ α·exp(βP·P + βA·A + βD·D)。"""
    z = bp * float(P) + ba * float(A) + bd * float(D)
    z = max(-20.0, min(20.0, z))
    return float(alpha) * math.exp(z)


def rank(items: list[dict], P: float, A: float, D: float) -> list[dict]:
    """按 base × pad_weight 排序；不改变原列表。"""
    out = []
    for it in items:
        w = pad_weight(P, A, D)
        out.append({**it, "score": float(it.get("base", 1.0)) * w})
    return sorted(out, key=lambda x: x["score"], reverse=True)
