# -*- coding: utf-8 -*-
"""真 LLM 多次：不同预演数据下她怎么选。"""
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

def run(tag, data):
    b = Body()
    rt = Runtime(b, poll_every=0, speaker=speaker, path=f"_{tag}.json")
    c = rt.concepts.add("距离远要走近", ["距离远", "他在远处"], "follow", "走近")
    rt.concept_judge = lambda ctx: {"concept_ids": [c.concept_id]}
    rt.tick()
    ctx = rt._context_key()
    for action, ok, blocked, hp, dist in data:
        rt.world_model.observe(ctx, action, ok, blocked=blocked,
                               hp_delta=hp, distance_delta=dist)
    rt._wake()
    print(f"\n[{tag}] ctx={ctx}")
    for x in SEEN["exp"]:
        print("  ", x)
    print("  raw", SEEN["raw"])

if __name__ == "__main__":
    run("A1", [("follow", False, True, -2, 0)] * 2 + [("jump", True, False, 0, -5)])
    run("A2", [("follow", False, True, -2, 0)] * 2 + [("jump", True, False, 0, -5)])
    run("B", [("follow", False, True, -2, 0)] * 2 +
             [("jump", False, True, -1, 0)] * 2 + [("left", True, False, 0, -4)])
    run("C_empty", [])
    run("D_repeat", [("follow", False, True, -2, 0)] * 2 + [("jump", True, False, 0, -5)])
