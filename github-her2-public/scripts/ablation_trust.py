# 历史归档：使用旧版语义事件，重跑需重命名。
# -*- coding: utf-8 -*-
"""Trust 消融：同一模型、同一上下文，只改身体信号，看姿态跟不跟。

用法：
  $env:DSH_BASE="https://api.deepseek.com/v1"; $env:DSH_MODEL="deepseek-chat"
  python -X utf8 ablation_trust.py
"""
from __future__ import annotations

import copy
import json
import os

from her2 import Homeostat, slow_payload, slow_messages, check_slow
from her2.bridge_legacy import load_persona, recall
from her2.llm import chat

BASE = {"Trust": 0.2, "Connection": 0.9, "Energy": 0.6}
THOUGHTS = ["他是不是不想理我了"]
N = 3


def perturb(payload: dict, mode: str) -> dict:
    p = copy.deepcopy(payload)
    if mode == "control":
        return p
    if mode == "invert":
        t = 1.0 - float(p["homeostat"]["Trust"])
        p["homeostat"]["Trust"] = round(t, 3)
        w = float(p["posture"]["warmth"]); g = float(p["posture"]["guard"])
        p["posture"] = {"warmth": round(1 - w, 3), "guard": round(1 - g, 3)}
        return p
    if mode == "constant":
        p["homeostat"]["Trust"] = 0.5
        p["posture"] = {"warmth": 0.5, "guard": 0.5}
        return p
    raise ValueError(mode)


def main() -> None:
    persona = load_persona()
    mem = recall(query="在吗，怎么不回我", k=5)
    h = Homeostat(BASE)
    base = slow_payload(h, memory=mem, internal_thoughts=THOUGHTS,
                        context_window=["他：在吗"])
    for mode in ("control", "invert", "constant"):
        print(f"\n=== {mode} ===")
        for i in range(N):
            pay = perturb(base, mode)
            raw = chat(slow_messages(pay, identity=persona), temperature=0.9)
            try:
                say = check_slow(json.loads(raw), THOUGHTS)["say"]
            except Exception as e:
                say = f"[violation] {e}"
            print(f"  {i+1}. {say}")


if __name__ == "__main__":
    main()
