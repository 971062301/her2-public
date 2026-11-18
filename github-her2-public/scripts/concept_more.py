# -*- coding: utf-8 -*-
"""多情境失败：看复盘器是否持续产出不同、可执行的新卡。"""
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
    SEEN["raw"] = chat(slow_messages(pay, identity=P), temperature=0.7, max_tokens=120)
    try:
        return json_from_text(SEEN["raw"])
    except Exception:
        return {"action": "hold"}


def scene(rt, tag, signs, action, fact):
    c = rt.concepts.add(tag, signs, action, "试过")
    rt.facts = [fact]
    rt.motion["distance_to_player"] = 25
    print(f"\n--- {tag} card={c.concept_id} ---")
    for i in (1, 2):
        rt._wake()
        print("  raw", SEEN["raw"][:90], "active", rt.active_concept_id)
        for _ in range(14):
            rt.tick()
    rt.sleep(1.0)
    print("  cards:")
    for x in rt.concepts.cards.values():
        print("   ", x.concept_id, x.concept_name, x.signs, x.action,
              "S/F", x.success_count, x.fail_count, "dep", x.deprecated)


def main():
    rt = Runtime(Body(), poll_every=0, speaker=speaker, path="_more.json")
    rt.concept_judge = make_judge(chat)
    rt.concept_reflector = make_reflector(chat)
    rt.tick()
    scene(rt, "目标在身后只会向前", ["他在你身后", "只会向前"], "follow",
          "他在你身后，但你只会往前走，撞墙了")
    scene(rt, "前方有墙硬走", ["前方有墙", "被挡住"], "follow",
          "前面有墙，你还是硬走，被挡住了")


if __name__ == "__main__":
    main()
