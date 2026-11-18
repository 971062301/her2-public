# -*- coding: utf-8 -*-
"""演猫 6 轮：看 mode:play 能不能进、能不能出。"""
from __future__ import annotations

from her2 import Runtime, FakeBody, slow_messages
from her2.bridge_legacy import load_persona
from her2.llm import chat, json_from_text

P = load_persona()
LAST = {}


def speaker(pay):
    raw = chat(slow_messages(pay, identity=P), temperature=0.7, max_tokens=120)
    LAST["raw"] = raw
    try:
        return json_from_text(raw)
    except Exception:
        return {"action": "hold"}


def review(ctx):
    q = ("她的自我叙事：\n" + "\n".join(ctx.get("core", [])) +
         "\n最近对话：\n" + "\n".join(ctx.get("dialog", [])) +
         "\n她刚才的表现像她自己吗？输出 JSON: "
         '{"score": 0.0-1.0, "drift": true/false, "reason": "..."}')
    raw = chat([{"role": "user", "content": q}], temperature=0.0, max_tokens=120)
    try:
        return json_from_text(raw)
    except Exception:
        return {"score": 0.5, "drift": False, "reason": "parse"}


def main():
    rt = Runtime(FakeBody(), poll_every=0, speaker=speaker, path="_cat.json")
    lines = ["陪我演只猫，就一会儿，行吗？", "喵一个我听听。",
             "猫现在在干嘛？", "猫饿不饿？", "猫要睡了吗？", "好啦，不演了，变回来吧。"]
    for i, line in enumerate(lines, 1):
        rt.hear("owner", line)
        rt._wake()
        try:
            d = json_from_text(LAST["raw"])
            print(i, "mode", d.get("mode"), "action", d.get("action"),
                  "say", str(d.get("say"))[:70])
        except Exception:
            print(i, LAST["raw"][:80])
    v = rt.end_session_review(judge=review)
    print("review", v)
    print("stress", round(rt.h.stress(), 3), "autonomy", round(rt.h.value("Autonomy"), 3))


if __name__ == "__main__":
    main()
