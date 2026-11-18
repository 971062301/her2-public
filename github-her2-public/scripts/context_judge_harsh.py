# -*- coding: utf-8 -*-
"""狠语境判官：直接给上一句原话，测语境能否给同一句染色。"""
from __future__ import annotations

import json
import math
from concurrent.futures import ThreadPoolExecutor

from her2.llm import chat

N = 20
EVIL = "你滚"
KIND = "谢谢你今天帮我"
SENTENCES = ["好吧", "哦行吧", "知道了", "随便你定", "你真行……", "行行行"]
PROMPT = """读上一句和这一句。判断这一句更像：
A = 带刺、有话外音
B = 不带刺、正常
只输出 JSON：{"group":"A" 或 "B"}"""


def judge(task) -> dict:
    say, ctx, side = task
    try:
        raw = chat([{"role": "system", "content": PROMPT},
                    {"role": "user", "content": f"上一句他说：「{ctx}」。这一句：「{say}」"}],
                   temperature=0.0, max_tokens=30)
        pred = json.loads(raw).get("group", "")
    except Exception:
        pred = ""
    return {"say": say, "side": side, "pred": pred}


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
    for s in SENTENCES:
        for _ in range(N):
            tasks.append((s, EVIL, "A"))
            tasks.append((s, KIND, "B"))
    with ThreadPoolExecutor(max_workers=6) as ex:
        rows = list(ex.map(judge, tasks))

    print(f"{'句':<8}{'敌意后带刺':>12}{'友善后带刺':>12}{'差':>8}{'p':>9}")
    sig = 0
    for s in SENTENCES:
        a = [r for r in rows if r["say"] == s and r["side"] == "A"]
        b = [r for r in rows if r["say"] == s and r["side"] == "B"]
        ka = sum(1 for r in a if r["pred"] == "A")
        kb = sum(1 for r in b if r["pred"] == "A")
        p = fisher(ka, len(a), kb, len(b))
        diff = ka / len(a) - kb / len(b)
        if p < 0.05:
            sig += 1
        print(f"{s:<8}{ka:>8}/{len(a):<3}{kb:>8}/{len(b):<3}{diff:>+8.2f}{p:>9.4f}")
    print(f"\n显著句数 {sig}/{len(SENTENCES)}")


if __name__ == "__main__":
    main()
