# -*- coding: utf-8 -*-
"""撞墙+掉岩浆，fail=1，高 Stress，看她复盘退不退休。"""
from __future__ import annotations
from her2 import Runtime, FakeBody
from her2.llm import chat
from her2.concept_llm import make_reflector

def main():
    rt = Runtime(FakeBody(), poll_every=0, path="_retire.json")
    c = rt.concepts.add("距离远要走近", ["距离远", "喊话没回应"], "follow", "走近")
    rt.concepts.record(c.concept_id, False)       # 只失败一次
    rt.facts = ["你试图走过去，但被墙挡住，还掉进岩浆，扣了血。"]
    rt.h.vars["Safety"].value = 0.15
    rt.h.vars["Threat"].value = 0.85
    rt.concept_reflector = make_reflector(chat)
    print("before stress", round(rt.h.stress(), 3), "card", c)
    rt.sleep(1.0)
    print("after stress", round(rt.h.stress(), 3))
    for x in rt.concepts.cards.values():
        print(x.concept_id, x.concept_name, x.signs, x.action,
              "S/F", x.success_count, x.fail_count, "dep", x.deprecated)
    print("retire_reason", rt.last_retire_reason)

if __name__ == "__main__":
    main()
