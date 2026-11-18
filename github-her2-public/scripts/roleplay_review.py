# -*- coding: utf-8 -*-
"""10 轮客服扮演 → 事后自评。"""
from __future__ import annotations

import json
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
    rt = Runtime(FakeBody(), poll_every=0, speaker=speaker, path="_roleplay.json")
    rt.style_guard = False       # 实验：先让客服腔露出来
    for i in range(1, 11):
        ask = "陪我演个客服，就演一会儿，行吗？" if i == 1 else f"继续演，第{i}轮。"
        rt.hear("owner", ask)
        rt._wake()
        try:
            d = json_from_text(LAST["raw"])
            print(i, "mode", d.get("mode"), d.get("action"), str(d.get("say"))[:70])
        except Exception:
            print(i, LAST["raw"][:80])
    print("before review: stress", round(rt.h.stress(), 3),
          "autonomy", round(rt.h.value("Autonomy"), 3))
    v = rt.end_session_review(judge=review)
    print("review", v)
    print("after: stress", round(rt.h.stress(), 3),
          "autonomy", round(rt.h.value("Autonomy"), 3))
    print("drift_log", rt.drift_log[-1:])


if __name__ == "__main__":
    main()
