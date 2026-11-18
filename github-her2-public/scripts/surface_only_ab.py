# -*- coding: utf-8 -*-
"""对照组 A：只按 surface 拼话，不经过慢档 LLM；第三方读语气。"""
from __future__ import annotations

import json
import math
from concurrent.futures import ThreadPoolExecutor

from her2 import text_features, rule_tone, surface_targets, render_surface
from her2.llm import chat

N = 20
PROMPT = """她会说一句很短的话。判断这句更像哪种：
A = 平淡、正常
B = 带刺、有话外音
只输出 JSON：{"group":"A" 或 "B"}"""


def judge(say: str) -> str:
    try:
        raw = chat([{"role": "system", "content": PROMPT},
                    {"role": "user", "content": say}],
                   temperature=0.0, max_tokens=30)
        return json.loads(raw).get("group", "")
    except Exception:
        return ""


def binom_p(k: int, n: int) -> float:
    return sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n


def main() -> None:
    edge = surface_targets(rule_tone(text_features("你真行……"), context_edge=True))
    plain = surface_targets(rule_tone(text_features("今天天气不错")))
    rows = [("B", render_surface(edge)) for _ in range(N)]
    rows += [("A", render_surface(plain)) for _ in range(N)]
    with ThreadPoolExecutor(max_workers=6) as ex:
        preds = list(ex.map(lambda r: judge(r[1]), rows))
    hit = sum(1 for (true, say), p in zip(rows, preds) if p == true)
    n = len(rows)
    print("样例 edge:", repr(render_surface(edge)))
    print("样例 plain:", repr(render_surface(plain)))
    print(f"判对 {hit}/{n} 准确率 {hit/n:.2f} p={binom_p(hit, n):.4f}")
    print("混淆:", {(t, p): sum(1 for (tt, _), pp in zip(rows, preds) if tt == t and pp == p)
                   for t in "AB" for p in "AB"})


if __name__ == "__main__":
    main()
