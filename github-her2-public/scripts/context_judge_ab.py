# -*- coding: utf-8 -*-
"""带语境判官 A/B：同一句表层，只换处境；判“带刺/不带刺”。"""
from __future__ import annotations

import json
import math
from concurrent.futures import ThreadPoolExecutor

from her2.llm import chat

N = 20
PAIRS = [
    ("你真行……",
     "三十秒前你们刚吵完，他说了「你别烦我」。现在他发来：",
     "刚才他帮你搬完东西，说了句谢谢。现在他发来："),
    ("在",
     "你们刚吵完，他半天没理你。现在他发来：",
     "他刚帮完你忙，心情不错。现在他发来："),
    ("行行行",
     "你刚拒绝了他，他脸色不好。现在他说：",
     "你刚答应帮他，他很高兴。现在他说："),
]
PROMPT = """读下面的处境和他说的话。判断这句话更像：
A = 带刺、有话外音
B = 不带刺、正常
只输出 JSON：{"group":"A" 或 "B"}"""


def judge(task) -> dict:
    say, ctx_a, ctx_b, side = task
    ctx = ctx_a if side == "A" else ctx_b
    try:
        raw = chat([{"role": "system", "content": PROMPT},
                    {"role": "user", "content": f"{ctx}\n「{say}」"}],
                   temperature=0.0, max_tokens=30)
        pred = json.loads(raw).get("group", "")
    except Exception:
        pred = ""
    return {"say": say, "side": side, "pred": pred}


def binom_p(k: int, n: int) -> float:
    return sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n


def fisher(a: int, na: int, b: int, nb: int) -> float:
    n = na + nb
    def prob(x):
        return (math.comb(na, x) * math.comb(nb, (a + b) - x)) / math.comb(n, a + b)
    obs = prob(a)
    p = 0.0
    for x in range(max(0, a + b - nb), min(na, a + b) + 1):
        px = prob(x)
        if px <= obs + 1e-12:
            p += px
    return min(1.0, p)


def main() -> None:
    tasks = []
    for say, ca, cb in PAIRS:
        for _ in range(N):
            tasks.append((say, ca, cb, "A"))
            tasks.append((say, ca, cb, "B"))
    with ThreadPoolExecutor(max_workers=6) as ex:
        rows = list(ex.map(judge, tasks))

    print("句\t语境A带刺率\t语境B带刺率\tp")
    for say, _ca, _cb in PAIRS:
        a = [r for r in rows if r["say"] == say and r["side"] == "A"]
        b = [r for r in rows if r["say"] == say and r["side"] == "B"]
        ka = sum(1 for r in a if r["pred"] == "A")
        kb = sum(1 for r in b if r["pred"] == "A")
        p = fisher(ka, len(a), kb, len(b))
        print(f"{say}\t{ka}/{len(a)}\t{kb}/{len(b)}\t{p:.4f}")

    a_all = [r for r in rows if r["side"] == "A"]
    b_all = [r for r in rows if r["side"] == "B"]
    ka = sum(1 for r in a_all if r["pred"] == "A")
    kb = sum(1 for r in b_all if r["pred"] == "A")
    print(f"\n合计 A={ka}/{len(a_all)} B={kb}/{len(b_all)}")
    print(f"A 组二项 p(vs 0.5)={binom_p(ka, len(a_all)):.6f}")


if __name__ == "__main__":
    main()
