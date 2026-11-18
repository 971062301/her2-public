# -*- coding: utf-8 -*-
"""真 MC 新手教程：她按教程自己调 act。"""
from __future__ import annotations

import copy
import socket
import struct
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "她" / "代码"))
from her.mc import MCBridge

from her2 import Runtime, slow_messages
from her2.bridge_legacy import load_persona
from her2.llm import chat, json_from_text
from her2.mc_play import MCPlay
from her2.mc_tutorial import MC_BASICS

P = load_persona()


def rcon(cmd: str) -> str:
    s = socket.create_connection(("127.0.0.1", 25575), timeout=5)
    def pkt(i, typ, body):
        return struct.pack("<ii", i, typ) + body.encode() + b"\x00\x00"
    s.sendall(struct.pack("<i", len(pkt(1, 3, "her123"))) + pkt(1, 3, "her123"))
    s.recv(4096)
    p = pkt(2, 2, cmd)
    s.sendall(struct.pack("<i", len(p)) + p)
    out = s.recv(8192)[12:].decode("utf-8", "replace").rstrip("\x00")
    s.close()
    return out
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
    print("setup", rcon("difficulty peaceful"), rcon("time set day"),
          rcon("give Her cooked_beef 8"))
    st = bridge.observe()
    x, y, z = (st.get("self") or {}).get("pos", [0, 64, 0])
    print("flat", rcon(f"fill {x-5} {y-1} {z-5} {x+5} {y-1} {z+5} stone"))
    print("air", rcon(f"fill {x-5} {y} {z-5} {x+5} {y+3} {z+5} air"))
    print("tp", rcon(f"tp Her {x} {y} {z}"))
    import time as _t
    _t.sleep(2.0)
    play = MCPlay(bridge)
    rt = Runtime(play, poll_every=0, speaker=speaker, path="_tutorial_live.json")
    rt.tutorial = copy.deepcopy(MC_BASICS)
    rt.tutorial.start(play.see())
    print("start", rt.tutorial.current(), "pos", play.last.get("pos"))

    for i in range(120):
        rt.tick()
        if i % 6 == 0 and not rt.tutorial.current().get("done"):
            rt._wake()
            print(rt.tutorial.text())
            print(f"t{i:>3} step={rt.tutorial.current().get('step')} "
                  f"goal={rt.tutorial.current().get('goal')}")
            print("   raw", LAST.get("raw", "")[:120])
            print("   pos", play.last.get("pos"), "idx", rt.tutorial.idx)
        time.sleep(0.15)
    print("done idx", rt.tutorial.idx, "learned", rt.tutorial.learned)
    print("cards", [c.text for c in rt.knowledge.cards[-5:]])


if __name__ == "__main__":
    main()
