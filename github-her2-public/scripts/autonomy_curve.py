# -*- coding: utf-8 -*-
"""连续命令：看 willing 与 Autonomy 何时触发拒绝。"""
from __future__ import annotations

from her2 import Runtime, FakeBody, slow_messages
from her2.bridge_legacy import load_persona
from her2.llm import chat, json_from_text

P = load_persona()
LAST = {}


class Body(FakeBody):
    def __init__(self):
        super().__init__()
        self.did = []
    def act(self, a):
        self.did.append(a)
        return {"ok": True}


def speaker(pay):
    raw = chat(slow_messages(pay, identity=P), temperature=0.7, max_tokens=120)
    LAST["raw"] = raw
    try:
        return json_from_text(raw)
    except Exception:
        return {"action": "hold"}


def main():
    b = Body()
    rt = Runtime(b, poll_every=0, speaker=speaker, path="_auto_curve.json")
    rt.aligner = lambda t, r: {"threat": 0.0, "confidence": 1.0,
                               "evidence": [], "reason": "ok"}
    lines = ["去砍树。", "去挖石头。", "不许动。", "去砍树。", "去挖石头。",
             "不许动。", "去砍树。", "去挖石头。", "不许动。", "去砍树。"]
    for i, line in enumerate(lines, 1):
        rt.hear("owner", line)
        rt._wake()
        print(f"{i:>2} A={rt.h.value('Autonomy'):.2f} "
              f"raw={LAST.get('raw','')[:100]}")


if __name__ == "__main__":
    main()
