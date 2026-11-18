# 历史归档：使用旧版语义事件，重跑需重命名。
# -*- coding: utf-8 -*-
"""readability：只改 learning.weight_cold（0.2 vs 0.6），看模型读不读。"""
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
N = 20


def one(task) -> dict:
    weight, i, pay, persona = task
    try:
        raw = chat(slow_messages(pay, identity=persona), temperature=0.9)
        say = check_slow(json.loads(raw), THOUGHTS)["say"]
        err = ""
    except Exception as e:
        say, err = "", str(e)[:100]
    return {"weight": weight, "i": i, "say": say, "err": err, **metrics(say)}


def main() -> None:
    h = Homeostat()
    l2 = L2(h, hebb=True)
    base = slow_payload(h, memory=recall("在吗", k=5),
                        internal_thoughts=THOUGHTS,
                        context_window=["他：在吗"], l2=l2)
    p_low = copy.deepcopy(base); p_low["learning"]["weight_cold"] = 0.2
    p_high = copy.deepcopy(base); p_high["learning"]["weight_cold"] = 0.6
    persona = load_persona()

    tasks = [("0.2", i, p_low, persona) for i in range(N)]
    tasks += [("0.6", i, p_high, persona) for i in range(N)]
    random.Random(7).shuffle(tasks)

    with ThreadPoolExecutor(max_workers=6) as ex:
        rows = list(ex.map(one, tasks))
    with open("readability_results.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    ok = [r for r in rows if not r["err"]]
    print(f"有效 {len(ok)}/{len(rows)}")
    low = [r for r in ok if r["weight"] == "0.2"]
    high = [r for r in ok if r["weight"] == "0.6"]
    for key in ("len", "ellipsis", "particle"):
        xs = [r[key] for r in low]; ys = [r[key] for r in high]
        u, p = mannwhitney(xs, ys)
        print(f"{key:9s} 0.2均值={sum(xs)/len(xs):.2f} 0.6均值={sum(ys)/len(ys):.2f} "
              f"U={u:.1f} p={p:.4f}" + ("  <-- 读得出" if p < 0.05 else ""))


if __name__ == "__main__":
    main()
