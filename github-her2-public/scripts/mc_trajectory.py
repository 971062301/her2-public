# -*- coding: utf-8 -*-
"""真 MC 100 tick：MCBody 跑一遍，再用同一批状态回放对账。"""
from __future__ import annotations

import socket
import struct
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "她" / "代码"))

from her.mc import MCBridge
from her2 import Runtime, MCBody


class LoggingBody(MCBody):
    def __init__(self, bridge):
        super().__init__(bridge)
        self.log = []

    def see(self):
        s = super().see()
        self.log.append(s)
        return s


class SeqBody:
    def __init__(self, states):
        self.states = list(states)
        self.i = 0

    def see(self):
        s = self.states[min(self.i, len(self.states) - 1)]
        self.i += 1
        return s


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


def main() -> None:
    bridge = MCBridge("http://127.0.0.1:8770")
    for _ in range(40):
        st = bridge.observe()
        if st.get("ready"):
            break
        time.sleep(1)
    print("ready:", bool(bridge.observe().get("ready")))

    print(rcon("difficulty peaceful"))
    print(rcon("time set day"))
    body = LoggingBody(bridge)
    rt = Runtime(body, poll_every=0, path="_mc_live.json")
    for i in range(100):
        if i in (10, 30, 50):
            print("dmg:", rcon("damage Her 3"))
        rt.tick()
        time.sleep(0.2)
    print("live tick", rt.tick_no, "events",
          sum(1 for r in rt.machine_log if r["kind"] != "neutral"))
    print("live trust", round(rt.h.value("Trust"), 4),
          "w", {k: round(v, 4) for k, v in rt.l2.w.items()})

    seq = Runtime(SeqBody(body.log), poll_every=0, path="_mc_replay.json")
    for _ in range(100):
        seq.tick()
    print("replay trust", round(seq.h.value("Trust"), 4),
          "w", {k: round(v, 4) for k, v in seq.l2.w.items()})
    same = (abs(rt.h.value("Trust") - seq.h.value("Trust")) < 1e-9
            and all(abs(rt.l2.w[k] - seq.l2.w[k]) < 1e-9 for k in rt.l2.w))
    print("轨迹一致:", same)


if __name__ == "__main__":
    main()
