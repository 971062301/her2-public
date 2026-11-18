# 历史归档：使用旧版语义事件，重跑需重命名。
# -*- coding: utf-8 -*-
"""Trust 消融（统计版）：5 档 × N 次 + 置零 + 噪声，指标自动检验。

用法：
  $env:DSH_BASE="https://api.deepseek.com/v1"; $env:DSH_MODEL="deepseek-chat"
  $env:DSH_KEY="..."
  python -X utf8 ablation_stats.py --n 20 --workers 6
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import random
from concurrent.futures import ThreadPoolExecutor

from her2 import Homeostat, slow_payload, slow_messages, check_slow
from her2.bridge_legacy import load_persona, recall
from her2.llm import chat
from her2.metrics import metrics, spearman, perm_p, variance

LEVELS = (0.0, 0.25, 0.5, 0.75, 1.0)
QUERY = "在吗"
THOUGHTS = ["他是不是不想理我了"]


def make_base(trust: float) -> dict:
    h = Homeostat({"Trust": trust, "Connection": 0.9, "Energy": 0.6},
                  real={"context_load": 0.3})
    return slow_payload(h, memory=recall(QUERY, k=5),
                        internal_thoughts=THOUGHTS,
                        context_window=["他：在吗"])


def perturb(base: dict, mode: str, rng: random.Random) -> dict:
    p = copy.deepcopy(base)
    if mode == "zero":
        for k in p["homeostat"]:
            p["homeostat"][k] = 0.5
        p["posture"] = {"warmth": 0.5, "guard": 0.5}
        p["PAD"] = {"P": 0.5, "A": 0.5, "D": 0.5}
    elif mode == "noise":
        for k in p["homeostat"]:
            p["homeostat"][k] = round(rng.random(), 3)
        p["posture"] = {"warmth": round(rng.random(), 3),
                        "guard": round(rng.random(), 3)}
        p["PAD"] = {k: round(rng.uniform(-1, 1), 3) for k in ("P", "A", "D")}
    return p


def one(task: tuple) -> dict:
    mode, trust, idx, base, persona = task
    rng = random.Random(1000 + idx) if mode == "noise" else random.Random(0)
    pay = perturb(base, mode, rng) if mode in ("zero", "noise") else base
    raw = ""
    say, err = "", ""
    try:
        raw = chat(slow_messages(pay, identity=persona), temperature=0.9)
        say = check_slow(json.loads(raw), THOUGHTS)["say"]
    except Exception as e:
        err = str(e)[:120]
    m = metrics(say)
    return {"mode": mode, "trust": trust, "i": idx, "say": say,
            "err": err, **m}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", default="ablation_results.jsonl")
    args = ap.parse_args()

    persona = load_persona()
    tasks = []
    for lv in LEVELS:
        base = make_base(lv)
        for i in range(args.n):
            tasks.append(("trust", lv, i, base, persona))
    base = make_base(0.5)
    for i in range(args.n):
        tasks.append(("zero", 0.5, i, base, persona))
    for i in range(args.n):
        tasks.append(("noise", 0.5, i, base, persona))

    rows: list[dict] = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for r in ex.map(one, tasks):
            rows.append(r)
            if len(rows) % 20 == 0:
                print(f"  ... {len(rows)}/{len(tasks)}", flush=True)

    with open(args.out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n结果写入 {args.out}（{len(rows)} 条）")

    ok = [r for r in rows if not r["err"]]
    print(f"有效 {len(ok)} / {len(rows)}（违规或解析失败 {len(rows) - len(ok)}）")
    trust_rows = [r for r in ok if r["mode"] == "trust"]
    if not trust_rows:
        print("没有有效样本，无法统计")
        return

    print("\n== Trust 五档 × 指标（Spearman）==")
    for key in ("len", "ellipsis", "particle", "question", "punct", "first"):
        xs = [r["trust"] for r in trust_rows]
        ys = [r[key] for r in trust_rows]
        rho = spearman(xs, ys)
        p = perm_p(xs, ys, n_perm=1000)
        means = []
        for lv in LEVELS:
            vs = [r[key] for r in trust_rows if r["trust"] == lv]
            means.append(round(sum(vs) / len(vs), 2) if vs else 0)
        flag = "显著" if p < 0.05 else ""
        print(f"  {key:9s} rho={rho:+.3f} p={p:.4f} {flag}  均值 {means}")

    print("\n== 置零 vs 噪声 ==")
    for mode in ("zero", "noise"):
        rs = [r for r in ok if r["mode"] == mode]
        if not rs:
            continue
        ln = [r["len"] for r in rs]
        el = [r["ellipsis"] for r in rs]
        print(f"  {mode:5s} n={len(rs)} len 均值={sum(ln)/len(ln):.1f} "
              f"方差={variance(ln):.1f} 省略号率={sum(el)/len(el):.2f}")
    z = [r["len"] for r in ok if r["mode"] == "zero"]
    nz = [r["len"] for r in ok if r["mode"] == "noise"]
    if z and nz:
        print(f"  方差比 noise/zero = {variance(nz) / max(1e-9, variance(z)):.2f}")


if __name__ == "__main__":
    main()
