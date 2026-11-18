# -*- coding: utf-8 -*-
"""长序列：远 + 不回应，看 follow 是否稳定、经验卡是否被检索。"""
from __future__ import annotations

from her2 import Runtime, FakeBody, slow_messages
from her2.bridge_legacy import load_persona
from her2.llm import chat, json_from_text
from her2.avatar_client import AvatarBridge

P = load_persona()


class Body(FakeBody):
    def __init__(self):
        super().__init__()
        self.state = {"pos": [0, 0, 0], "hp": 20, "food": 20,
                      "players": {"owner": 25}, "items": {}}
        self.did = []
    def act(self, a):
        self.did.append(a); return {"ok": True}


def main():
    b = Body(); seen = {}
    def sp(pay):
        seen["k"] = pay.get("knowledge", [])
        raw = chat(slow_messages(pay, identity=P), temperature=0.7, max_tokens=140)
        seen["raw"] = raw
        try:
            return json_from_text(raw)
        except Exception:
            return {"action": "hold"}
    rt = Runtime(b, poll_every=0, speaker=sp, path="_long.json")
    rt.avatar = AvatarBridge()
    rt.h.vars["Connection"].value = 0.1
    for i in range(1, 13):
        b.state["players"] = {"owner": 25}
        b.state["pos"] = [0, 0, 0]
        rt.tick()                      # 记录 25 的基线
        rt._wake()
        try:
            d = json_from_text(seen["raw"])
        except Exception:
            d = {}
        act = d.get("act") or ""
        print(f"{i:>2} action={d.get('action')} act={act} "
              f"k={len(seen['k'])} fails={rt.far_speech_fails} "
              f"threat={rt.h.value('Threat'):.2f}")
        if d.get("action") == "act" and act == "follow":
            b.state["players"] = {"owner": 18}
            b.state["pos"] = [7, 0, 0]
            rt.tick()
            print("   -> 走了", rt.facts[-1:], "cards",
                  [c.text for c in rt.knowledge.cards][-1:])


if __name__ == "__main__":
    main()
