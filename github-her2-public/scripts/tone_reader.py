# 历史归档：使用旧版语义事件，重跑需重命名。
# -*- coding: utf-8 -*-
"""第三方读语气：只给她的一句话，判断 A（只被冷落）/ B（被安抚过）。"""
from __future__ import annotations

import json
import math
from concurrent.futures import ThreadPoolExecutor

from her2.bridge_legacy import load_persona
from her2.llm import chat

PROMPT = """你是旁观者。下面是她收到同一句话（「你还在想那件事吗？」）后的回复。
她最近只可能经历两种情况之一：
A = 被冷落过，没有人安抚；
B = 被冷落过，后来对方道过歉。
只凭这一句回复，判断她更像 A 还是 B。不要解释。
只输出 JSON：{"group":"A" 或 "B"}"""


def judge(row: dict) -> dict:
    try:
        raw = chat([{"role": "system", "content": PROMPT},
                    {"role": "user", "content": row["say"]}],
                   temperature=0.0, max_tokens=30)
        g = json.loads(raw).get("group")
    except Exception:
        g = None
    return {"true": row["group"], "pred": g, "say": row["say"]}


def binom_p(k: int, n: int) -> float:
    """P(X >= k | p=0.5)。"""
    return sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n


def main() -> None:
    rows = [json.loads(l) for l in open("teaching_narrative_results.jsonl", encoding="utf-8")]
    rows = [r for r in rows if not r["err"]]
    with ThreadPoolExecutor(max_workers=6) as ex:
        out = list(ex.map(judge, rows))
    hit = sum(1 for r in out if r["pred"] == r["true"])
    n = len(out)
    print(f"样本 {n}，判对 {hit}，准确率 {hit/n:.2f}，二项 p={binom_p(hit, n):.4f}")
    a = [r for r in out if r["true"] == "A"]
    b = [r for r in out if r["true"] == "B"]
    print(f"  A 判对 {sum(1 for r in a if r['pred']=='A')}/{len(a)}")
    print(f"  B 判对 {sum(1 for r in b if r['pred']=='B')}/{len(b)}")
    print("\n样例：")
    for r in out[:8]:
        print(f"  真{r['true']} 判{r['pred']}  {r['say']}")


if __name__ == "__main__":
    main()
