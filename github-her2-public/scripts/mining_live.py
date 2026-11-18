# -*- coding: utf-8 -*-
"""强制 act:mine，验持续挖 + 结算（不走 LLM）。"""
from __future__ import annotations
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "她" / "代码"))
from her.mc import MCBridge
from her2 import Runtime
from her2.mc_play import MCPlay

def main():
    bridge = MCBridge("http://127.0.0.1:8770")
    for _ in range(20):
        if bridge.observe().get("ready"):
            break
        time.sleep(1)
    rt = Runtime(MCPlay(bridge), poll_every=0,
                 speaker=lambda pay: {"action": "hold", "say": "", "act": "mine"},
                 path="_mining_live.json")
    rt.boredom = 0.9
    rt.mine_timeout_ticks = 25
    rt.tick()
    rt._wake()
    print("start mining", rt.mining, "job", bridge.observe().get("ready"))
    for i in range(25):
        time.sleep(0.5)
        rt.tick()
        job = bridge._get("/job") if hasattr(bridge, "_get") else {}
        print(i, "mining", rt.mining, "loot", rt.mine_loot,
              "boredom", round(rt.boredom, 2), "pos", rt.body.last.get("pos"),
              "items", sum(x.get("count", 0) for x in bridge.observe().get("inventory", [])))
        if not rt.mining:
            break
    print("world", rt.world_model.table, "boredom", rt.boredom)

if __name__ == "__main__":
    main()
