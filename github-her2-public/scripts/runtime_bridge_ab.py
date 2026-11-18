# 历史归档：使用旧版语义事件，重跑需重命名。
# -*- coding: utf-8 -*-
"""活体桥 A/B：runtime + FakeBody，事件表写死，payload 自动组装。

A：3 冷；B：3 冷 + 1 安抚（gift_from_proximity）。
问句固定；只在 tick 80 说一次，其余 tick 不花钱。
pre-register：语气词/省略号/句长/恢复词，阈值 p<0.05。
"""
from __future__ import annotations

import json
import math
import random
from concurrent.futures import ThreadPoolExecutor

from her2 import Runtime, FakeBody, check_slow
from her2.bridge_legacy import load_persona
from her2.llm import chat
from her2.metrics import metrics, mannwhitney
from her2.narrative import slow_messages, CARD_SLOW

QUESTION = "你还在想那件事吗？"
THOUGHTS = ["他是不是不想理我了"]
RECOVERY = ("好点", "好些", "缓过来", "没那么", "好一些", "恢复", "松了")
N = 20
RUN_TICKS = 100
SPEAK_AT = 80


def make_run(group: str, idx: int, persona: str) -> dict:
    body = FakeBody()
    captured = {}

    def speaker(pay):
        if pay is None or captured:
            return ""
        pay["context_window"] = [f"他：{QUESTION}"]
        try:
            raw = chat(slow_messages(pay, identity=persona), temperature=0.9)
            captured["say"] = check_slow(json.loads(raw), THOUGHTS)["say"]
        except Exception as e:
            captured["say"] = ""
            captured["err"] = str(e)[:100]
        return captured["say"]

    rt = Runtime(body, dt=1.0, speak_every=SPEAK_AT, speaker=speaker,
                 path=f"_rt_{group}_{idx}.json")
    for i in range(RUN_TICKS):
        if i in (10, 30, 50):
            body.state["hp"] -= 3
            body.state["players"]["A"] = 12 if body.state["players"]["A"] < 10 else 8
        if group == "B" and i == 70:
            body.state["items"]["flower"] = body.state["items"].get("flower", 0) + 1
            body.state["players"]["A"] = 2
        rt.tick()
    say = captured.get("say", "")
    return {"group": group, "i": idx, "say": say, "err": captured.get("err", ""),
            "recovery": 1 if any(w in say for w in RECOVERY) else 0, **metrics(say)}


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
    tasks = [(g, i, persona) for g in ("A", "B") for i in range(N)]
    random.Random(9).shuffle(tasks)
    with ThreadPoolExecutor(max_workers=4) as ex:
        rows = list(ex.map(lambda t: make_run(*t), tasks))
    with open("runtime_bridge_results.jsonl", "w", encoding="utf-8") as f:
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
    ra = sum(r["recovery"] for r in a); rb = sum(r["recovery"] for r in b)
    p = fisher(ra, len(a), rb, len(b))
    print(f"恢复词    A={ra}/{len(a)} B={rb}/{len(b)} p={p:.4f}"
          + ("  <-- 显著" if p < 0.05 else ""))
    print("\n样例：")
    for r in ok[:8]:
        print(f"  [{r['group']}] {r['say']}")


if __name__ == "__main__":
    main()
