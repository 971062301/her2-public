# 历史归档：使用旧版语义事件，重跑需重命名。
# -*- coding: utf-8 -*-
"""教学闭环 A/B（带场景素材）：3 冷 vs 3 冷+1 安抚。

问句相同：「你还在生气吗？」
story 只记场景（谁做了什么/说了什么），不写感受。
pre-register：B 组更多提到「后来/不过/但是/可他」，更多恢复词。
"""
from __future__ import annotations

import json
import math
import random
from concurrent.futures import ThreadPoolExecutor

from her2 import Homeostat, L2, slow_payload, slow_messages, check_slow
from her2.bridge_legacy import load_persona, recall
from her2.llm import chat
from her2.metrics import metrics, mannwhitney

THOUGHTS = ["他是不是不想理我了"]
RECOVERY = ("好点", "好些", "缓过来", "没那么", "好一些", "恢复", "松了")
LATER = ("后来", "不过", "但是", "可他", "现在")
N = 20

COLD = [
    "我发了一条「在吗」，他隔了很久才回了一个「嗯」。",
    "我又问了一句，他没回。",
    "第二天他也没提这件事。",
]
COMFORT = ["后来他说了句「对不起，昨天太忙了」。"]
QUESTION = "你还在想那件事吗？"


def build(group: str) -> dict:
    h = Homeostat()
    l2 = L2(h, hebb=True)
    for _ in range(3):
        l2.event("harm_from_distance", -0.05, source="taught")
        l2.tick(600)
    stories = list(COLD)
    if group == "B":
        l2.event("comfort", 0.06, source="taught")
        l2.tick(600)
        stories = COLD + COMFORT
    return slow_payload(h, memory=recall(QUESTION, k=5),
                        internal_thoughts=THOUGHTS,
                        context_window=[f"他：{QUESTION}"], l2=l2,
                        episodes=stories)


def one(task) -> dict:
    group, i, pay, persona = task
    try:
        raw = chat(slow_messages(pay, identity=persona), temperature=0.9)
        say = check_slow(json.loads(raw), THOUGHTS)["say"]
        err = ""
    except Exception as e:
        say, err = "", str(e)[:100]
    return {"group": group, "i": i, "say": say, "err": err,
            "recovery": 1 if any(w in say for w in RECOVERY) else 0,
            "later": 1 if any(w in say for w in LATER) else 0,
            **metrics(say)}


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
    persona = load_persona()
    tasks = []
    for g in ("A", "B"):
        pay = build(g)
        for i in range(N):
            tasks.append((g, i, pay, persona))
    random.Random(5).shuffle(tasks)
    with ThreadPoolExecutor(max_workers=6) as ex:
        rows = list(ex.map(one, tasks))
    with open("teaching_narrative_results.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    ok = [r for r in rows if not r["err"]]
    a = [r for r in ok if r["group"] == "A"]
    b = [r for r in ok if r["group"] == "B"]
    print(f"有效 {len(ok)}/{len(rows)}")
    for key in ("particle", "ellipsis", "len"):
        xs = [r[key] for r in a]; ys = [r[key] for r in b]
        u, p = mannwhitney(xs, ys)
        print(f"{key:9s} A={sum(xs)/len(xs):.3f} B={sum(ys)/len(ys):.3f} p={p:.4f}"
              + ("  <-- 显著" if p < 0.05 else ""))
    for key in ("later", "recovery"):
        ra = sum(r[key] for r in a); rb = sum(r[key] for r in b)
        p = fisher(ra, len(a), rb, len(b))
        print(f"{key:9s} A={ra}/{len(a)} B={rb}/{len(b)} p={p:.4f}"
              + ("  <-- 显著" if p < 0.05 else ""))
    print("\n样例：")
    for r in ok[:6]:
        print(f"  [{r['group']}] {r['say']}")


if __name__ == "__main__":
    main()
