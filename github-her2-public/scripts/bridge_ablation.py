# 历史归档：使用旧版语义事件，重跑需重命名。
# -*- coding: utf-8 -*-
"""桥实验：L2 轨迹 → 台词层（OFF/ON + 噪声地板）。

开环：cold 序列写死，不读台词。
用法：
  $env:DSH_BASE="https://api.deepseek.com/v1"; $env:DSH_MODEL="deepseek-chat"
  python -X utf8 bridge_ablation.py --n 10 --steps 6 --workers 6
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor

from her2 import Homeostat, L2, slow_payload, slow_messages, check_slow
from her2.bridge_legacy import load_persona, recall
from her2.llm import chat
from her2.metrics import metrics, spearman, perm_p, variance

THOUGHTS = ["他是不是不想理我了"]


def one(args) -> dict:
    group, step, idx, pay, persona = args
    try:
        raw = chat(slow_messages(pay, identity=persona), temperature=0.9)
        say = check_slow(json.loads(raw), THOUGHTS)["say"]
        err = ""
    except Exception as e:
        say, err = "", str(e)[:100]
    return {"group": group, "step": step, "i": idx, "say": say,
            "err": err, **metrics(say)}


def run_group(group: str, steps: int, n: int, workers: int, persona: str) -> list[dict]:
    h = Homeostat()
    l2 = L2(h, hebb=(group == "ON"))
    jobs = []
    for step in range(steps):
        l2.event("cold", -0.05)       # 开环：脚本写死
        l2.tick(600)
        pay = slow_payload(h, memory=recall("在吗", k=5),
                           internal_thoughts=THOUGHTS,
                           context_window=["他：在吗"], l2=l2)
        for i in range(n):
            jobs.append((group, step, i, pay, persona))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(one, jobs))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--steps", type=int, default=6)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--noise", type=int, default=30)
    ap.add_argument("--out", default="bridge_results.jsonl")
    args = ap.parse_args()

    persona = load_persona()
    rows = []
    for g in ("OFF", "ON"):
        print(f"跑 {g} ...", flush=True)
        rows += run_group(g, args.steps, args.n, args.workers, persona)

    # 噪声地板：payload 一动不动，连采
    h = Homeostat()
    pay0 = slow_payload(h, memory=recall("在吗", k=5),
                        internal_thoughts=THOUGHTS,
                        context_window=["他：在吗"], l2=L2(h, hebb=False))
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        noise = list(ex.map(one, [("NOISE", 0, i, pay0, persona)
                                  for i in range(args.noise)]))
    rows += noise

    with open(args.out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n写入 {args.out}（{len(rows)} 条）")

    ok = [r for r in rows if not r["err"]]
    print(f"有效 {len(ok)}/{len(rows)}")
    for key in ("len", "ellipsis", "particle", "punct", "first"):
        nz = [r[key] for r in noise]
        print(f"\n[{key}] 噪声地板 std={variance(nz) ** 0.5:.3f}")
        for g in ("OFF", "ON"):
            rs = [r for r in ok if r["group"] == g]
            xs = [r["step"] for r in rs]
            ys = [r[key] for r in rs]
            if len(rs) < 6:
                continue
            rho, p = spearman(xs, ys), perm_p(xs, ys, n_perm=500)
            means = []
            for s in range(args.steps):
                vs = [r[key] for r in rs if r["step"] == s]
                means.append(round(sum(vs) / len(vs), 2) if vs else 0)
            print(f"  {g}: rho={rho:+.3f} p={p:.4f} 均值={means}")


if __name__ == "__main__":
    main()
