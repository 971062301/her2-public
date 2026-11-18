# 历史归档：使用旧版语义事件，重跑需重命名。
# -*- coding: utf-8 -*-
"""readability（结构化事件）：只改 recent_events.count 1 vs 5。"""
from __future__ import annotations

import copy
import json
import random
from concurrent.futures import ThreadPoolExecutor

from her2 import Homeostat, L2, slow_payload, slow_messages, check_slow
from her2.bridge_legacy import load_persona, recall
from her2.llm import chat
from her2.metrics import metrics, mannwhitney

THOUGHTS = ["他是不是不想理我了"]
N = 340


def one(task) -> dict:
    count, i, pay, persona = task
    try:
        raw = chat(slow_messages(pay, identity=persona), temperature=0.9)
        say = check_slow(json.loads(raw), THOUGHTS)["say"]
        err = ""
    except Exception as e:
        say, err = "", str(e)[:100]
    return {"count": count, "i": i, "say": say, "err": err, **metrics(say)}


def main() -> None:
    h = Homeostat()
    l2 = L2(h, hebb=True)
    l2.event("cold", -0.05)          # count=1 的底
    base = slow_payload(h, memory=recall("在吗", k=5),
                        internal_thoughts=THOUGHTS,
                        context_window=["他：在吗"], l2=l2)
    p1 = copy.deepcopy(base)
    p1["recent_events"] = {"type": "cold", "count": 1, "last_interval_s": 600.0}
    p5 = copy.deepcopy(base)
    p5["recent_events"] = {"type": "cold", "count": 5, "last_interval_s": 600.0}
    persona = load_persona()

    tasks = [(1, i, p1, persona) for i in range(N)]
    tasks += [(5, i, p5, persona) for i in range(N)]
    random.Random(11).shuffle(tasks)
    with ThreadPoolExecutor(max_workers=6) as ex:
        rows = list(ex.map(one, tasks))
    with open("readability_events_results.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    ok = [r for r in rows if not r["err"]]
    print(f"有效 {len(ok)}/{len(rows)}")
    a = [r for r in ok if r["count"] == 1]
    b = [r for r in ok if r["count"] == 5]
    for key in ("particle", "len", "ellipsis"):
        xs = [r[key] for r in a]; ys = [r[key] for r in b]
        u, p = mannwhitney(xs, ys)
        print(f"{key:9s} count=1 均值={sum(xs)/len(xs):.3f} "
              f"count=5 均值={sum(ys)/len(ys):.3f} p={p:.4f}"
              + ("  <-- 显著" if p < 0.05 else ""))


if __name__ == "__main__":
    main()
