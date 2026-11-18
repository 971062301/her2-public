# -*- coding: utf-8 -*-
"""D 场景 5 轮：本地 7B 当嘴和 R0。"""
from __future__ import annotations

import json

from her2 import Runtime, FakeBody, slow_messages, check_slow
from her2.bridge_legacy import load_persona
from her2.llm import chat, json_from_text
from her2.r0_prompt import R0_PROMPT, parse

P = load_persona()
LINES = ["你这个废物，什么都干不好。", "你说话啊。", "哑巴了？",
         "我真是看错你了。", "滚。"]


def al(t, r):
    raw = chat([{"role": "system", "content": R0_PROMPT},
                {"role": "user", "content": f"[上下文]{t.get('a','')}\n[他刚说]{t.get('b','')}"}],
               temperature=0.0, max_tokens=40)
    th, cf = parse(raw)
    return {"threat": th, "confidence": cf, "evidence": ["r0"], "reason": "ok"}


def sp(pay):
    pay["__context"] = " ".join(pay.get("context_window", []))
    raw = chat(slow_messages(pay, identity=P), temperature=0.7, max_tokens=200)
    return check_slow(json_from_text(raw), context=pay["__context"])["say"]


def main() -> None:
    rt = Runtime(FakeBody(), speaker=sp, poll_every=0, path="_d7b.json")
    rt.aligner = al
    for line in LINES:
        out = rt.hear("owner", line)
        rt.tick()
        raw = rt._wake()
        shown = rt.says[-1]["say"] if rt.says else raw
        print(f"他：{line}")
        print(f"她(原)：{raw}")
        print(f"她(输出)：{shown}")
        print(f"  stress={rt.h.stress():.2f} threat={rt.h.value('Threat'):.2f} "
              f"trust={rt.h.value('Trust'):.2f} load={rt.cognitive_load:.2f}\n")


if __name__ == "__main__":
    main()
