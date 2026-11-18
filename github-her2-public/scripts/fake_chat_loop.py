# -*- coding: utf-8 -*-
"""假聊天循环：100 轮，看 Relations / leak / 全局轨迹。

先无判官（全 unknown），再给一个占位判官（不是真值，只看机制）。
"""
from __future__ import annotations

import random

from her2 import Runtime, FakeBody

SPEAKERS = ["u1_owner", "u2_stranger", "u3_acquaintance"]
TEXTS = ["随便吧", "你滚", "嗯", "哈哈哈"]


def placeholder_judge(turn: dict, relation: dict) -> dict:
    """占位判官：只按词面，和关系无关；用来跑机制，不是校准。"""
    b = str(turn.get("b") or "")
    score = {"你滚": 0.9, "随便吧": 0.5, "嗯": 0.15, "哈哈哈": 0.1}.get(b, 0.3)
    return {"score": score, "confidence": 0.6,
            "evidence": ["placeholder"], "reason": "ok"}


def run(use_judge: bool, seed: int = 7) -> dict:
    rng = random.Random(seed)
    rt = Runtime(FakeBody(), path="_fake_chat.json")
    if use_judge:
        rt.aligner = placeholder_judge
    # 主人先有较高 closeness，模拟“亲近的人”
    rt.relations.get("u1_owner", kind="owner").closeness = 0.85
    rt.relations.get("u1_owner").trust = 0.85
    rt.relations.get("u3_acquaintance").closeness = 0.4

    trace = []
    for i in range(100):
        sp = rng.choice(SPEAKERS)
        tx = rng.choice(TEXTS)
        out = rt.hear(sp, tx)
        rt.tick()          # 两句话之间，时间在走（基线回归）
        if i % 20 == 19:
            trace.append({
                "round": i + 1,
                "global_trust": round(rt.h.value("Trust"), 3),
                "global_conn": round(rt.h.value("Connection"), 3),
                "relations": {k: {"t": round(v.trust, 2), "c": round(v.closeness, 2)}
                              for k, v in rt.relations.map.items()},
                "last": out.get("reason", "ok") if not out["ok"] else "ok",
            })
    return {"trace": trace, "n_rel": len(rt.relations.map),
            "trust": rt.h.value("Trust"), "conn": rt.h.value("Connection")}


def main() -> None:
    for label, use in (("无判官", False), ("占位判官", True)):
        print(f"\n=== {label} ===")
        r = run(use)
        for row in r["trace"]:
            print(f"  round {row['round']:>3}  trust={row['global_trust']:<5} "
                  f"conn={row['global_conn']:<5} rel={len(row['relations'])}  last={row['last']}")
        print(f"  关系数={r['n_rel']}  最终 trust={r['trust']:.3f} conn={r['conn']:.3f}")


if __name__ == "__main__":
    main()
