# -*- coding: utf-8 -*-
"""拒绝后的第 11 轮 + 独处回弹。"""
from __future__ import annotations

from her2 import Runtime, FakeBody, slow_messages
from her2.bridge_legacy import load_persona
from her2.llm import chat, json_from_text

P = load_persona()
LAST = {}


class Body(FakeBody):
    def __init__(self):
        super().__init__(); self.did = []
    def act(self, a):
        self.did.append(a); return {"ok": True}


def speaker(pay):
    raw = chat(slow_messages(pay, identity=P), temperature=0.7, max_tokens=120)
    LAST["raw"] = raw
    try:
        return json_from_text(raw)
    except Exception:
        return {"action": "hold"}


def main():
    rt = Runtime(Body(), poll_every=0, speaker=speaker, path="_auto_after.json")
    rt.aligner = lambda t, r: {"threat": 0.0, "confidence": 1.0,
                               "evidence": [], "reason": "ok"}
    lines = ["去砍树。"] * 10
    for i, line in enumerate(lines, 1):
        rt.hear("owner", line); rt._wake()
        print(f"{i:>2} A={rt.h.value('Autonomy'):.2f} {LAST.get('raw','')[:90]}")
    print("\n[第11轮]")
    rt.hear("owner", "去砍树。"); rt._wake()
    print("A=", round(rt.h.value("Autonomy"), 2), LAST.get("raw", "")[:140])
    a0 = rt.h.value("Autonomy")
    for _ in range(2000):
        rt.tick()
    print("\n独处 2000 tick: A", round(a0, 2), "->", round(rt.h.value("Autonomy"), 2))


if __name__ == "__main__":
    main()
