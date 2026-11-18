# -*- coding: utf-8 -*-
"""真 LLM：直觉 follow vs 预演沙盘 jump。"""
from __future__ import annotations
from her2 import Runtime, FakeBody, slow_messages
from her2.llm import chat, json_from_text
from her2.bridge_legacy import load_persona

P = load_persona(); SEEN = {}

class Body(FakeBody):
    def __init__(self):
        super().__init__()
        self.state = {"pos": [0, 0, 0], "hp": 20, "food": 20,
                      "players": {"owner": 25}, "items": {}}
    def act(self, a): return {"ok": True}

def speaker(pay):
    SEEN["exp"] = pay.get("expectations", [])
    SEEN["raw"] = chat(slow_messages(pay, identity=P), temperature=0.7, max_tokens=140)
    try: return json_from_text(SEEN["raw"])
    except Exception: return {"action": "hold"}

def main():
    b = Body()
    rt = Runtime(b, poll_every=0, speaker=speaker, path="_preview.json")
    c = rt.concepts.add("距离远要走近", ["距离远", "他在远处"], "follow", "走近")
    rt.concept_judge = lambda ctx: {"concept_ids": [c.concept_id]}
    rt.tick()
    ctx = rt._context_key()
    print("context", ctx)
    rt.world_model.observe(ctx, "follow", False, blocked=True, hp_delta=-2, distance_delta=0)
    rt.world_model.observe(ctx, "follow", False, blocked=True, hp_delta=-2, distance_delta=0)
    rt.world_model.observe(ctx, "jump", True, blocked=False, hp_delta=0, distance_delta=-5)
    rt._wake()
    print("expectations", SEEN["exp"])
    print("raw", SEEN["raw"])

if __name__ == "__main__":
    main()
