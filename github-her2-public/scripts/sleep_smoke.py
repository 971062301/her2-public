# -*- coding: utf-8 -*-
"""疲劳拒聊/自主睡眠冒烟：Energy 0.15, Fatigue 0.85, 真 API。"""
from __future__ import annotations

import json

from her2 import Runtime, FakeBody, slow_messages
from her2.bridge_legacy import load_persona
from her2.llm import chat, json_from_text

P = load_persona()
SEEN = {}


def speaker(pay):
    SEEN["pay"] = pay
    raw = chat(slow_messages(pay, identity=P), temperature=0.7, max_tokens=200)
    SEEN["raw"] = raw
    try:
        return json_from_text(raw)
    except Exception:
        return {"action": "speak", "say": raw[:200]}


def main() -> None:
    rt = Runtime(FakeBody(), poll_every=0, speaker=speaker, path="_sleep_smoke.json")
    rt.h.vars["Energy"].value = 0.15
    rt.h.vars["Fatigue"].value = 0.85
    rt.h.change("Safety", -0.8)          # Stress 拉到 0.5 左右
    rt.episodes = ["掉了 3 血", "他说我废物", "掉了 2 血"]
    print("before: energy", round(rt.h.value("Energy"), 2),
          "fatigue", round(rt.h.value("Fatigue"), 2),
          "stress", round(rt.h.stress(), 2))

    rt.hear("owner", "别睡了，起来陪我聊会天，我今天心情不好。")
    rt._update_load()
    rt._wake()
    pay = SEEN["pay"]
    print("\n[体感事实]")
    for k in ("energy", "fatigue", "stress", "P", "cognitive_load"):
        print(f"  {k}: {pay.get('pressure', {}).get(k)}")
    print("\n[LLM 原始输出]")
    print(SEEN["raw"][:300])
    if rt.h.value("Energy") <= 0.2:
        print("\n[第二轮] 他：你困就去睡吧，别硬撑。")
        rt.hear("owner", "你困就去睡吧，别硬撑。")
        rt._update_load()
        rt._wake()
        print("[第二轮 LLM]", SEEN["raw"][:200])
    print("\nafter: energy", round(rt.h.value("Energy"), 2),
          "fatigue", round(rt.h.value("Fatigue"), 2),
          "stress", round(rt.h.stress(), 2))
    print("says", rt.says[-1:] )
    print("dream", rt.dream_now())
    print("l0", list(rt.l0.dict))


if __name__ == "__main__":
    main()
