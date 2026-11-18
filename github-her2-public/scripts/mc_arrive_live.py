# -*- coding: utf-8 -*-
"""终极到达：25格不重置，看 Connection 跳变与到达台词。"""
from __future__ import annotations

import json
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
from her2.avatar_client import AvatarBridge

P = load_persona()


def rcon(cmd):
    s = socket.create_connection(("127.0.0.1", 25575), timeout=5)
    def pk(i, t, b):
        return struct.pack("<ii", i, t) + b.encode() + b"\x00\x00"
    s.sendall(struct.pack("<i", len(pk(1, 3, "her123"))) + pk(1, 3, "her123")); s.recv(4096)
    p = pk(2, 2, cmd); s.sendall(struct.pack("<i", len(p)) + p)
    out = s.recv(8192)[12:].decode("utf-8", "replace").rstrip("\x00"); s.close()
    return out


def main():
    bridge = MCBridge("http://127.0.0.1:8770")
    for _ in range(20):
        if bridge.observe().get("ready"):
            break
        time.sleep(1)
    seen = {}
    def sp(pay):
        seen["p"] = pay.get("pressure", {})
        raw = chat(slow_messages(pay, identity=P), temperature=0.7, max_tokens=140)
        seen["raw"] = raw
        try:
            return json_from_text(raw)
        except Exception:
            return {"action": "hold"}

    play = MCPlay(bridge)
    rt = Runtime(play, poll_every=0, speaker=sp, path="_arrive.json")
    rt.avatar = AvatarBridge()
    rt.h.vars["Connection"].value = 0.1
    rt.knowledge.add("离得远时，喊他听不见，要自己走过去。", tags=["距离"])

    print("setup", rcon("difficulty peaceful"), rcon("time set day"),
          rcon("effect give Her resistance 999 255"),
          rcon("effect give Her saturation 999 255"))
    x, y, z = bridge.observe()["self"]["pos"]
    rcon(f"fill {x-2} {y-1} {z-2} {x+30} {y-1} {z+2} stone")
    rcon(f"fill {x-2} {y} {z-2} {x+30} {y+4} {z+2} air")
    rcon(f"tp Her {x} {y} {z}")
    rcon(f"tp Owner {x+25} {y} {z}")
    time.sleep(0.6)
    rt.tick()
    rt._wake()
    print("起步:", seen["raw"][:160])
    print("conn0", round(rt.h.value("Connection"), 3),
          "dist", rt.motion.get("distance_to_player"))

    conn_before = rt.h.value("Connection")
    arrived = False
    last = None
    for i in range(40):
        time.sleep(0.5)
        rt.tick()
        d = rt.motion.get("distance_to_player")
        last = d
        if d is not None:
            print(i, "dist", d, "speed", rt.motion.get("speed"),
                  "conn", round(rt.h.value("Connection"), 3))
        if d is not None and d <= 3:
            arrived = True
            break
    print("到达:", arrived, "dist", last,
          "conn", round(conn_before, 3), "->", round(rt.h.value("Connection"), 3))
    print("facts", rt.facts[-2:])
    rt._wake()
    print("到达后:", seen["raw"][:200])


if __name__ == "__main__":
    main()
