# -*- coding: utf-8 -*-
"""100 轮审计：关系双向 / R1 拒判率 / L0 是否只学正结果。"""
from __future__ import annotations

import random

from her2 import Runtime, FakeBody

TEXTS = ["好吧", "随便吧", "你滚", "嗯", "哈哈哈"]
SPEAKERS = ["owner", "stranger", "u3"]


def aligner(turn, rel):
    b = str(turn.get("b") or "")
    score = {"你滚": 0.9, "随便吧": 0.5, "好吧": 0.25,
             "嗯": 0.15, "哈哈哈": 0.1}.get(b, 0.3)
    return {"score": score, "confidence": 0.7, "evidence": ["text"], "reason": "ok"}


def main() -> None:
    rt = Runtime(FakeBody(), path="_audit.json")
    rt.aligner = aligner
    rt.use_calibration = True
    # 只校准两条；其余应被拒判
    for item in ("owner|好吧", "owner|嗯"):
        for _ in range(3):
            rt.calibration.add(item, "对齐")
    for _ in range(3):
        rt.calibration.add("owner|你滚", "不对齐")

    before = {k: (v.trust, v.closeness) for k, v in rt.relations.map.items()}
    reject = 0
    up = down = 0
    rng = random.Random(5)
    for i in range(100):
        sp = rng.choice(SPEAKERS)
        tx = rng.choice(TEXTS)
        before_trust = rt.relations.get(sp).trust
        out = rt.hear(sp, tx)
        if not out["ok"]:
            reject += 1
        else:
            d = rt.relations.get(sp).trust - before_trust
            up += 1 if d > 1e-9 else 0
            down += 1 if d < -1e-9 else 0
        if i % 20 == 19:
            print(f"round {i+1}: reject={reject} l0={rt.l0_hits} "
                  f"llm={rt.llm_calls} rel={len(rt.relations.map)}")

    print("\n最终关系：")
    for k, v in rt.relations.map.items():
        t0 = before.get(k, (v.trust, v.closeness))
        print(f"  {k:9s} trust {t0[0]:.2f}->{v.trust:.2f}  "
              f"close {t0[1]:.2f}->{v.closeness:.2f}")
    print(f"拒判率 {reject}/100 = {reject/100:.0%}")
    print(f"关系变化：升 {up} 次 / 降 {down} 次")
    print("L0 词典：", {k: (r.kind, r.relation_kind, round(r.weight, 2))
                        for k, r in rt.l0.dict.items()})


if __name__ == "__main__":
    main()
