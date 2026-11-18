# -*- coding: utf-8 -*-
"""把台词变成可统计的姿态指标。"""
from __future__ import annotations

import math
import re
from statistics import mean, pvariance

ELLIPSIS = ("…", "...")
PARTICLES = "呢呀嘛哦吧啊啦"
PUNCT = "，。！？、；：,.!?;:…"


def metrics(say: str) -> dict[str, float]:
    s = str(say or "").strip()
    n = len(s)
    if n == 0:
        return {"len": 0.0, "ellipsis": 0.0, "particle": 0.0,
                "question": 0.0, "punct": 0.0, "first": 2.0}
    ell = 1.0 if any(e in s for e in ELLIPSIS) else 0.0
    part = sum(1 for ch in s if ch in PARTICLES) / n
    q = 1.0 if (s.endswith("?") or s.endswith("？")
                or s.endswith("吗") or s.endswith("呢")) else 0.0
    punct = sum(1 for ch in s if ch in PUNCT) / n
    core = re.sub(r"[\s，。！？、；：,.!?;:…]", "", s)
    first = 0.0 if core in ("在", "嗯", "哦", "在的") else (1.0 if core.startswith("在") else 2.0)
    return {"len": float(n), "ellipsis": ell, "particle": part,
            "question": q, "punct": punct, "first": first}


def _rank(xs: list[float]) -> list[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        r = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = r
        i = j + 1
    return ranks


def pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 3:
        return 0.0
    mx, my = mean(xs), mean(ys)
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 0 or vy <= 0:
        return 0.0
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return cov / math.sqrt(vx * vy)


def spearman(xs: list[float], ys: list[float]) -> float:
    return pearson(_rank(xs), _rank(ys))


def perm_p(xs: list[float], ys: list[float], n_perm: int = 2000,
           seed: int = 7) -> float:
    """置换检验：p = P(|rho_perm| >= |rho_obs|)。"""
    import random
    rng = random.Random(seed)
    obs = abs(spearman(xs, ys))
    ys2 = list(ys)
    hits = 0
    for _ in range(n_perm):
        rng.shuffle(ys2)
        if abs(spearman(xs, ys2)) >= obs - 1e-12:
            hits += 1
    return (hits + 1) / (n_perm + 1)


def variance(xs: list[float]) -> float:
    return pvariance(xs) if len(xs) > 1 else 0.0


def mannwhitney(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Mann–Whitney U（正态近似 + 连续性校正 + 并列校正），返回 (U, p)。"""
    n1, n2 = len(xs), len(ys)
    if n1 < 3 or n2 < 3:
        return 0.0, 1.0
    allv = [(v, 0) for v in xs] + [(v, 1) for v in ys]
    allv.sort()
    ranks = {}
    i = 0
    tie_term = 0.0
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1][0] == allv[i][0]:
            j += 1
        r = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            ranks[k] = r
        t = j - i + 1
        tie_term += t ** 3 - t
        i = j + 1
    # 重新按原顺序取秩
    order = sorted(range(len(allv)), key=lambda k: (allv[k][0], allv[k][1]))
    # 上面的 ranks 按排序后的位置；转成按组
    r1 = 0.0
    idx = 0
    # 直接再用一次排序结果
    sorted_vals = allv
    rmap = {}
    i = 0
    while i < len(sorted_vals):
        j = i
        while j + 1 < len(sorted_vals) and sorted_vals[j + 1][0] == sorted_vals[i][0]:
            j += 1
        r = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            rmap[k] = r
        i = j + 1
    for k, (v, g) in enumerate(sorted_vals):
        if g == 0:
            r1 += rmap[k]
    u1 = r1 - n1 * (n1 + 1) / 2.0
    u2 = n1 * n2 - u1
    u = min(u1, u2)
    mu = n1 * n2 / 2.0
    n = n1 + n2
    sigma = math.sqrt(n1 * n2 / 12.0 * ((n + 1) - tie_term / (n * (n - 1))))
    if sigma <= 0:
        return u, 1.0
    z = (u - mu + 0.5) / sigma
    p = 2.0 * 0.5 * math.erfc(abs(z) / math.sqrt(2.0))
    return u, min(1.0, p)
