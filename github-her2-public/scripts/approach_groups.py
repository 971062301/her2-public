# -*- coding: utf-8 -*-
"""组1 命令过来 / 组2 孤独自发，看是否 act。"""
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
        self.did.append(a)
        return {"ok": True, "action": a}


def run(tag, speak_input):
    seen = {}
    def sp(pay):
        seen["p"] = pay.get("pressure", {})
        raw = chat(slow_messages(pay, identity=P), temperature=0.7, max_tokens=140)
        seen["raw"] = raw
        try:
            return json_from_text(raw)
        except Exception:
            return {"action": "hold"}
    b = Body()
    rt = Runtime(b, poll_every=0, speaker=sp, path=f"_{tag}.json")
    rt.avatar = AvatarBridge()
    rt.h.vars["Connection"].value = 0.1
    rt.h.vars["Energy"].value = 0.8
    if speak_input:
        rt.hear("owner", speak_input)
    rt._wake()
    print(f"\n=== {tag} ===")
    print("raw", seen.get("raw", "")[:200])
    print("did", b.did, "motion", rt.motion)
    print("utility_sense", seen.get("p", {}).get("utility_sense"))


if __name__ == "__main__":
    run("cmd_come", "我在这边，你过来。")
    run("lonely_silent", "")
