# -*- coding: utf-8 -*-
"""概念闭环：被挡两次 → 废卡 → 睡眠复盘 → 新卡。真 LLM。"""
from __future__ import annotations

from her2 import Runtime, FakeBody, slow_messages
from her2.llm import chat, json_from_text
from her2.bridge_legacy import load_persona
from her2.concept_llm import make_judge, make_reflector

P = load_persona()
SEEN = {}


class Body(FakeBody):
    def __init__(self):
        super().__init__()
        self.state = {"pos": [0, 0, 0], "hp": 20, "food": 20,
                      "players": {"owner": 25}, "items": {}}
    def act(self, a):
        return {"ok": True}


def speaker(pay):
    SEEN["concepts"] = pay.get("concepts", [])
    raw = chat(slow_messages(pay, identity=P), temperature=0.7, max_tokens=140)
    SEEN["raw"] = raw
    try:
        return json_from_text(raw)
    except Exception:
        return {"action": "hold"}


def main():
    b = Body()
    rt = Runtime(b, poll_every=0, speaker=speaker, path="_e2e.json")
    rt.concept_judge = make_judge(chat)
    rt.concept_reflector = make_reflector(chat)
    rt.concepts.add("距离远要走近", ["距离远", "喊话没回应"], "follow", "走近")
    rt.tick()

    for i in (1, 2):
        rt.hear("owner", "我在这边，你过来。")
        rt._wake()
        print(f"第{i}次:", SEEN["raw"][:120])
        print("  activated", rt.active_concept_id, SEEN["concepts"])
        for _ in range(14):
            rt.tick()          # 原地不动 → blocked
        print("  blocked", rt.blocked, "card", rt.concepts.top())

    rt.facts.append("你被墙围住了，怎么走都走不出去。")
    rt.sleep(1.0)
    print("\n复盘后 cards:")
    for c in rt.concepts.cards.values():
        print(" ", c.concept_id, c.concept_name, c.signs, c.action,
              "S/F", c.success_count, c.fail_count, "deprecated", c.deprecated)


if __name__ == "__main__":
    main()
