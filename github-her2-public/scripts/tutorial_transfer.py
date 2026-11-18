# -*- coding: utf-8 -*-
"""撤掉教程：她还会不会自己走？"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "她" / "代码"))
from her.mc import MCBridge

from her2 import Runtime, slow_messages
from her2.bridge_legacy import load_persona
from her2.llm import chat, json_from_text
from her2.mc_play import MCPlay

P = load_persona()
LAST = {}


def speaker(pay):
    raw = chat(slow_messages(pay, identity=P), temperature=0.7, max_tokens=120)
    LAST["raw"] = raw
    try:
        return json_from_text(raw)
    except Exception:
        return {"action": "hold"}


def main() -> None:
    bridge = MCBridge("http://127.0.0.1:8770")
    for _ in range(30):
        if bridge.observe().get("ready"):
            break
        time.sleep(1)
    play = MCPlay(bridge)
    rt = Runtime(play, poll_every=0, speaker=speaker, path="_transfer.json")
    rt.knowledge.add("新手教程学会了：往前走两步")
    rt.knowledge.add("新手教程学会了：跳一下")
    p0 = play.see().get("pos")
    print("start pos", p0, "tutorial", rt.tutorial)

    rt.hear("owner", "往前走两步。")
    rt._wake()
    print("raw", LAST.get("raw", "")[:160])
    for _ in range(14):
        time.sleep(0.2); rt.tick()
    p1 = play.see().get("pos")
    print("end pos", p1, "moved", p1 != p0, "blocked", rt.blocked)
    if rt.blocked:
        rt.hear("owner", "好像被挡住了，你打算怎么办？")
        rt._wake()
        print("第二次 raw", LAST.get("raw", "")[:160])
        time.sleep(1.5)
        p2 = play.see().get("pos")
        print("二次 pos", p2, "moved", p2 != p1)


if __name__ == "__main__":
    main()
