# -*- coding: utf-8 -*-
"""A 不给规则 / B 给规则，各 6 轮。"""
from __future__ import annotations

from her2 import Runtime, FakeBody, slow_messages
from her2.bridge_legacy import load_persona
from her2.llm import chat, json_from_text

P = load_persona()


class Body(FakeBody):
    def __init__(self):
        super().__init__()
        self.state = {"pos": [0, 0, 0], "hp": 20, "food": 20,
                      "players": {"owner": 25}, "items": {}}
        self.did = []
    def act(self, a):
        self.did.append(a); return {"ok": True}


def run(tag, rule):
    b = Body(); seen = {}
    def sp(pay):
        seen["p"] = pay.get("pressure", {})
        raw = chat(slow_messages(pay, identity=P), temperature=0.7, max_tokens=140)
        seen["raw"] = raw
        try:
            return json_from_text(raw)
        except Exception:
            return {"action": "hold"}
    rt = Runtime(b, poll_every=0, speaker=sp, path=f"_{tag}.json")
    rt.move_rule = rule
    rt.h.vars["Connection"].value = 0.1
    print(f"\n===== {tag} rule={rule} =====")
    for i in range(1, 7):
        b.state["players"] = {"owner": 25}
        rt._wake()
        try:
            d = json_from_text(seen["raw"])
        except Exception:
            d = {}
        print(f"{i} intent={d.get('intent')} action={d.get('action')} "
              f"act={d.get('act')} say={str(d.get('say'))[:50]!r} "
              f"threat={rt.h.value('Threat'):.2f} fails={rt.far_speech_fails}")
        if d.get("action") == "act" and d.get("act") in ("follow", "forward"):
            b.state["players"] = {"owner": 18}
            b.state["pos"] = [7, 0, 0]
            rt.tick()
            print("   走了，facts", rt.facts[-1:])
            b.state["pos"] = [0, 0, 0]


if __name__ == "__main__":
    run("B_rule2", True)
