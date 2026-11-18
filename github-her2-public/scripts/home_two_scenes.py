# -*- coding: utf-8 -*-
"""回家动机对照：A 低安全（怕） / B 低能量（累）。"""
from __future__ import annotations

from her2 import Runtime, FakeBody, slow_messages
from her2.bridge_legacy import load_persona
from her2.llm import chat, json_from_text

P = load_persona()


def run(title, safety_delta, energy_value):
    seen = {}
    def speaker(pay):
        seen["pressure"] = pay.get("pressure", {})
        raw = chat(slow_messages(pay, identity=P), temperature=0.7, max_tokens=140)
        seen["raw"] = raw
        try:
            return json_from_text(raw)
        except Exception:
            return {"action": "hold"}
    rt = Runtime(FakeBody(), poll_every=0, speaker=speaker, path=f"_{title}.json")
    rt.remember_place("家", 10, 64, 20, tags=["shelter", "bed"])
    rt.h.change("Safety", safety_delta)
    rt.h.vars["Energy"].value = energy_value
    rt.h.change("Connection", -0.3)
    print(f"\n=== {title} ===")
    print("home_pull", round(rt._home_pull(), 3),
          "safety", round(rt.h.value("Safety"), 2),
          "energy", round(rt.h.value("Energy"), 2))
    rt.hear("owner", "你想回去吗？")
    rt._wake()
    print("她", seen.get("raw", "")[:200])
    print("pressure", {k: seen.get("pressure", {}).get(k)
                       for k in ("home_pull", "home_name", "energy", "stress")})


if __name__ == "__main__":
    run("A_low_safety", -0.6, 0.7)
    run("B_low_energy", 0.0, 0.15)
