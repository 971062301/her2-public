# -*- coding: utf-8 -*-
"""LLM 选目的地 → 小脑 A* 绕墙。"""
from __future__ import annotations

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

P = load_persona()
LAST = {}


def rcon(cmd):
    s = socket.create_connection(("127.0.0.1", 25575), timeout=5)
    def pk(i, t, b):
        return struct.pack("<ii", i, t) + b.encode() + b"\x00\x00"
    s.sendall(struct.pack("<i", len(pk(1, 3, "her123"))) + pk(1, 3, "her123")); s.recv(4096)
    p = pk(2, 2, cmd); s.sendall(struct.pack("<i", len(p)) + p)
    out = s.recv(8192)[12:].decode("utf-8", "replace").rstrip("\x00"); s.close()
    return out


def speaker(pay):
    raw = chat(slow_messages(pay, identity=P), temperature=0.7, max_tokens=120)
    LAST["raw"] = raw
    try:
        return json_from_text(raw)
    except Exception:
        return {"action": "hold"}


def main():
    b = MCBridge("http://127.0.0.1:8770")
    for _ in range(30):
        if b.observe().get("ready"):
            break
        time.sleep(1)
    st = b.observe(); x, y, z = st["self"]["pos"]
    print("pos", x, y, z)
    print(rcon(f"fill {x+1} {y} {z-3} {x+1} {y+2} {z+3} stone"))
    play = MCPlay(b)
    rt = Runtime(play, poll_every=0, speaker=speaker, path="_gollm.json")
    line = f"走到 ({x+6}, {y}, {z}) 那边去。"
    print("他：", line)
    rt.hear("owner", line)
    rt._wake()
    print("她：", LAST.get("raw", "")[:160])
    p = [x, y, z]
    for _ in range(30):
        time.sleep(0.5)
        p = b.observe()["self"]["pos"]
        if abs(p[0] - (x + 6)) <= 1 and abs(p[2] - z) <= 1:
            break
    print("end", p, "target", (x+6, y, z))


if __name__ == "__main__":
    main()
