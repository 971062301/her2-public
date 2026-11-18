# -*- coding: utf-8 -*-
"""终极睡眠冒烟：明确放她走，看她睡不睡、醒后记不记得。"""
from __future__ import annotations

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
    rt = Runtime(FakeBody(), poll_every=0, speaker=speaker, path="_sleep_goodnight.json")
    rt.h.vars["Energy"].value = 0.15
    rt.h.vars["Fatigue"].value = 0.85
    rt.h.change("Safety", -0.8)
    rt.episodes = ["掉了 3 血", "他说我废物", "掉了 2 血", "他让我去睡"]
    print("before", round(rt.h.value("Energy"), 2), round(rt.h.value("Fatigue"), 2),
          round(rt.h.stress(), 2))

    rt.hear("owner", "乖，今天辛苦了，我心情好多了。晚安，去睡吧，我不聊了。")
    rt._update_load()
    rt._wake()
    print("[她睡前]", SEEN["raw"])
    print("[says]", rt.says[-1:])
    print("[sleep]", getattr(rt, "last_sleep", None))
    print("after", round(rt.h.value("Energy"), 2), round(rt.h.value("Fatigue"), 2),
          round(rt.h.stress(), 2))

    rt.hear("owner", "早。")
    rt._update_load()
    rt._wake()
    print("[醒后第一句]", SEEN["raw"])
    print("[dialog]", rt.dialog[-4:])


if __name__ == "__main__":
    main()
