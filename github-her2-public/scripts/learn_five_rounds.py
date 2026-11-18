# -*- coding: utf-8 -*-
"""1-5 轮：叫失效 → 被迫走 → 奖励 → 经验 → 再远。"""
from __future__ import annotations

from her2 import Runtime, FakeBody, slow_messages
from her2.bridge_legacy import load_persona
from her2.llm import chat, json_from_text
from her2.avatar_client import AvatarBridge

P = load_persona()
SEEN = {}


class Body(FakeBody):
    def __init__(self):
        super().__init__()
        self.state = {"pos": [0, 0, 0], "hp": 20, "food": 20,
                      "players": {"owner": 25}, "items": {}}
        self.did = []
    def act(self, a):
        self.did.append(a)
        return {"ok": True}


def speaker(pay):
    SEEN["p"] = pay.get("pressure", {})
    SEEN["k"] = pay.get("knowledge", [])
    raw = chat(slow_messages(pay, identity=P), temperature=0.7, max_tokens=140)
    SEEN["raw"] = raw
    try:
        return json_from_text(raw)
    except Exception:
        return {"action": "hold"}


def main():
    b = Body()
    rt = Runtime(b, poll_every=0, speaker=speaker, path="_learn5.json")
    rt.avatar = AvatarBridge()
    rt.h.vars["Connection"].value = 0.1

    for i in range(1, 7):
        if i == 6:
            b.state["players"] = {"owner": 25}
            rt.recent_text = ["他很远", "想找他"]
        out = rt._wake()
        act = ""
        try:
            act = json_from_text(SEEN["raw"]).get("act", "")
        except Exception:
            pass
        print(f"\n--- 第{i}轮 ---")
        print("raw", SEEN["raw"][:160])
        print("threat", round(rt.h.value("Threat"), 2),
              "stress", round(rt.h.stress(), 2),
              "fails", rt.far_speech_fails,
              "blocked", SEEN["p"].get("last_speech_blocked"))
        print("facts", SEEN["p"].get("facts"))
        print("knowledge", SEEN["k"])
        if act in ("follow", "go_to", "forward", "back", "left", "right", "jump"):
            # 模拟她真的走过去：距离 25 → 18
            b.state["players"] = {"owner": 18}
            b.state["pos"] = [7, 0, 0]
            rt.tick()
            print("走了 → 距离 18，facts", rt.facts[-1:],
                  "cards", [c.text for c in rt.knowledge.cards][-1:])


if __name__ == "__main__":
    main()
