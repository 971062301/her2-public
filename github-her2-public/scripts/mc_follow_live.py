# -*- coding: utf-8 -*-
"""真 MC：远距离 + 叫失效 → 她 follow → bot 真走 → motion/小窗。"""
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
    st = bridge.observe(); x, y, z = st["self"]["pos"]
    rcon("difficulty peaceful"); rcon("time set day")
    rcon(f"fill {x-2} {y-1} {z-2} {x+28} {y-1} {z+2} stone")
    rcon(f"fill {x-2} {y} {z-2} {x+28} {y+3} {z+2} air")
    print("stage at", x, y, z)

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
    rt = Runtime(play, poll_every=0, speaker=sp, path="_followlive.json")
    rt.avatar = AvatarBridge()
    rt.h.vars["Connection"].value = 0.1

    for i in range(1, 7):
        rcon(f"tp Owner {x+25} {y} {z}")
        time.sleep(0.5)
        rt.tick()
        d0 = rt._nearest_player_distance(play.last) if hasattr(rt, "_nearest_player_distance") else None
        rt._wake()
        try:
            d = json_from_text(seen["raw"])
        except Exception:
            d = {}
        act = d.get("act") or ""
        print(f"\n{i} action={d.get('action')} act={act} want={d.get('intent')}")
        print("  say", str(d.get("say"))[:80])
        print("  dist_before", d0, "fails", rt.far_speech_fails,
              "threat", round(rt.h.value("Threat"), 2))
        if d.get("action") == "act" and act == "follow":
            time.sleep(4.0)
            rt.tick()
            print("  dist_after", rt.motion.get("distance_to_player"),
                  "motion", rt.motion, "avatar", json.loads(
                      urllib.request.urlopen("http://127.0.0.1:8799/state", timeout=3).read().decode("utf-8")))


if __name__ == "__main__":
    import urllib.request
    main()
