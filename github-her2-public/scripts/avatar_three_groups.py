# -*- coding: utf-8 -*-
"""三组状态对照：高/低 Connection & Energy，看输出差异。"""
from __future__ import annotations

import json
from her2 import Runtime, FakeBody, slow_messages
from her2.bridge_legacy import load_persona
from her2.llm import chat, json_from_text
from her2.avatar_client import AvatarBridge

P = load_persona()


def run(tag, conn, energy):
    seen = {}
    def sp(pay):
        seen["p"] = pay.get("pressure", {})
        raw = chat(slow_messages(pay, identity=P), temperature=0.7, max_tokens=140)
        seen["raw"] = raw
        try:
            return json_from_text(raw)
        except Exception:
            return {"action": "hold"}
    rt = Runtime(FakeBody(), poll_every=0, speaker=sp, path=f"_{tag}.json")
    rt.avatar = AvatarBridge()
    rt.h.vars["Connection"].value = conn
    rt.h.vars["Energy"].value = energy
    rt.hear("owner", "在吗？")
    rt._wake()
    print(f"\n=== {tag} conn={conn} energy={energy} ===")
    print("raw", seen.get("raw", "")[:180])
    print("motion", rt.motion)
    print("pressure", {k: seen.get("p", {}).get(k) for k in
                        ("connection", "energy", "utility_sense", "home_pull")})


if __name__ == "__main__":
    run("hi_hi", 0.9, 0.9)
    run("lo_lo", 0.1, 0.1)
    run("lo_hi", 0.1, 0.9)
