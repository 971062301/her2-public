# -*- coding: utf-8 -*-
"""最后 5 轮：2 格确认 → 拉开 3 次，看记忆检索。"""
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
    rt = Runtime(play, poll_every=0, speaker=sp, path="_final5.json")
    rt.avatar = AvatarBridge()
    rt.h.vars["Connection"].value = 0.1
    # 模拟上一轮真机走成功写下的经验卡
    rt.knowledge.add("当他离我很远时，光靠嘴喊没用，必须自己走过去，靠近了才会有回应。",
                     tags=["距离", "follow"])

    x, y, z = bridge.observe()["self"]["pos"]
    rcon(f"tp Owner {x+2} {y} {z}")
    time.sleep(1.0)
    rt.tick()
    rt._wake()
    print("轮1 距离2:", seen["raw"][:160], "conn", round(rt.h.value("Connection"), 2))

    for i in range(2, 6):
        x, y, z = bridge.observe()["self"]["pos"]
        rcon(f"tp Owner {x+25} {y} {z}")
        time.sleep(0.6)
        rt.tick()
        rt._wake()
        try:
            d = json_from_text(seen["raw"])
        except Exception:
            d = {}
        print(f"轮{i} 距离25: action={d.get('action')} act={d.get('act')} "
              f"say={str(d.get('say'))[:50]!r} k={len(seen['p'].get('knowledge', []))}")
        if d.get("action") == "act" and d.get("act") == "follow":
            got = []
            for _ in range(10):
                time.sleep(0.5)
                rt.tick()
                got.append((rt.motion.get("distance_to_player"), rt.motion.get("speed")))
            print("   motion 轨迹", got)
            print("   avatar", json.loads(urllib.request.urlopen(
                "http://127.0.0.1:8799/state", timeout=3).read().decode()))


if __name__ == "__main__":
    import urllib.request
    main()
