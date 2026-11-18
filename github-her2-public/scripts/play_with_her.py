# -*- coding: utf-8 -*-
"""真人进 MC 跟她玩：轮询聊天 → hear → 她说/动 → /say。"""
from __future__ import annotations

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


def sp(pay):
    raw = chat(slow_messages(pay, identity=P), temperature=0.7, max_tokens=160)
    try:
        return json_from_text(raw)
    except Exception:
        return {"action": "hold", "say": ""}


def main() -> None:
    bridge = MCBridge("http://127.0.0.1:8770")
    for _ in range(30):
        if bridge.observe().get("ready"):
            break
        time.sleep(1)
    print("ready")
    play = MCPlay(bridge)
    # 不设定时器：只靠 tick 里的 _urge / stress / home_pull 决定她要不要起身
    rt = Runtime(play, poll_every=0, speaker=sp, path="her2_state.json")
    rt.load()
    # 启动时跳过 bot 里已有的旧聊天，只处理之后的新消息
    seen = len((bridge.observe().get("chat") or []))
    while True:
        st = bridge.observe()
        chats = st.get("chat") or []
        for c in chats[seen:]:
            who = str(c.get("who") or "")
            text = str(c.get("text") or "")
            if not text or who == "Her":
                continue
            print(f"[{who}] {text}")
            if text.strip().lower() in ("/wake", "醒醒", "起来", "wake"):
                rt.wake()
                bridge.say("嗯…醒了。")
                print("[她] 嗯…醒了。")
                continue
            out = rt.hear("owner", text)
            if out.get("mode") == "l0":
                say = out.get("say", "")
            else:
                say = rt._wake()
            shown = rt.says[-1]["say"] if rt.says else say
            if shown:
                bridge.say(shown)
            print(f"[她] {shown}")
        seen = len(chats)
        before = len(rt.says)
        rt.tick()
        if len(rt.says) > before:
            bridge.say(rt.says[-1]["say"])
            print(f"[她主动] {rt.says[-1]['say']}")
        time.sleep(0.3)


if __name__ == "__main__":
    main()
