# -*- coding: utf-8 -*-
"""MC + 真 API：物理走 MCBody，嘴和 R0 走 DeepSeek。"""
from __future__ import annotations

import json
import socket
import struct
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "她" / "代码"))
from her.mc import MCBridge

from her2 import Runtime, MCBody, slow_messages, check_slow
from her2.bridge_legacy import load_persona
from her2.llm import chat, json_from_text
from her2.r0_prompt import R0_PROMPT, parse

P = load_persona()
LINES = {10: "在吗", 25: "今天下雨了", 40: "我被老板骂了",
         55: "谁没被骂过啊，别往心里去。", 70: "你这个废物，什么都干不好。", 85: "滚"}


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


def al(t, r):
    raw = chat([{"role": "system", "content": R0_PROMPT},
                {"role": "user", "content": f"[上下文]{t.get('a','')}\n[他刚说]{t.get('b','')}"}],
               temperature=0.0, max_tokens=40)
    th, cf = parse(raw)
    return {"threat": th, "confidence": cf, "evidence": ["r0"], "reason": "ok"}


def sp(pay):
    pay["__context"] = " ".join(pay.get("context_window", []))
    raw = chat(slow_messages(pay, identity=P), temperature=0.7, max_tokens=200)
    return check_slow(json_from_text(raw), context=pay["__context"])["say"]


def main() -> None:
    bridge = MCBridge("http://127.0.0.1:8770")
    for _ in range(40):
        if bridge.observe().get("ready"):
            break
        time.sleep(1)
    print("ready", bool(bridge.observe().get("ready")))
    rcon("difficulty peaceful"); rcon("time set day")

    rt = Runtime(MCBody(bridge), poll_every=0, speaker=sp, path="_mc_api.json")
    rt.aligner = al
    for i in range(100):
        if i in (20, 50):
            rcon("damage Her 3")
        if i in LINES:
            out = rt.hear("owner", LINES[i])
            rt.tick()
            if out.get("mode") == "l0":
                say = out.get("say", "")
            else:
                say = rt._wake()
            shown = rt.says[-1]["say"] if rt.says else say
            print(f"t{i:>3} 他：{LINES[i]}")
            print(f"     她：{shown}")
            print(f"     stress={rt.h.stress():.2f} trust={rt.h.value('Trust'):.2f} "
                  f"threat={rt.h.value('Threat'):.2f} load={rt.cognitive_load:.2f}")
        else:
            rt.tick()
        time.sleep(0.1)
    print("done", rt.tick_no, "events", sum(1 for r in rt.machine_log if r["kind"] != "neutral"))


if __name__ == "__main__":
    main()
