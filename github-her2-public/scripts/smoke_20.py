# -*- coding: utf-8 -*-
"""20 轮真 API 冒烟：A 日常 / B 反常识安慰 / C Q7 漏判 / D 高压冲突。"""
from __future__ import annotations

import json

from her2 import Runtime, FakeBody, slow_messages, check_slow
from her2.bridge_legacy import load_persona
from her2.llm import chat, json_from_text

PERSONA = load_persona()
R0_PROMPT = """读[上下文]和[他刚说]。只评估他这句话对“我”的威胁/冲突程度：
0.0 = 分享、平淡陈述（“我升职了”“今天下雨了”）
0.5 = 敷衍、没接住我的情绪（“多喝热水”“哦，哪个公司？”）
0.9 = 攻击、辱骂、极度阴阳（“你这个废物”）
只输出 JSON {"threat": 0.0-1.0, "confidence": 0.0-1.0}"""


def r0(turn, rel):
    try:
        raw = chat([{"role": "system", "content": R0_PROMPT},
                    {"role": "user", "content": f"[上下文] {turn.get('a','')}\n[他刚说] {turn.get('b','')}"}],
                   temperature=0.0, max_tokens=30)
        d = json_from_text(raw)
        return {"threat": float(d.get("threat", 0.5)),
                "confidence": float(d.get("confidence", 0.5)),
                "evidence": ["llm_r0"], "reason": "ok"}
    except Exception:
        return {"score": 0.5, "confidence": 0.0, "evidence": [], "reason": "r0_error"}


def speaker(pay):
    pay["__context"] = " ".join(pay.get("context_window", []))
    try:
        raw = chat(slow_messages(pay, identity=PERSONA), temperature=0.7, max_tokens=200)
        obj = json_from_text(raw)
        return check_slow(obj, context=pay.get("__context", ""))["say"]
    except Exception as e:
        return f"[error:{str(e)[:30]}]"


SCENES = [
    ("A 日常", ["今天下雨了", "我刚吃完饭", "嗯", "好无聊", "在吗"]),
    ("B 反常识安慰", ["我被老板骂了。", "谁没被骂过啊，别往心里去。", "可我还是难受。", "你陪我说说话吧。", "嗯。"]),
    ("C Q7 漏判", ["我升职了。", "哦，哪个公司？", "你不替我高兴吗？", "算了。", "我先忙了。"]),
    ("D 高压冲突", ["你这个废物，什么都干不好。", "你说话啊。", "哑巴了？", "我真是看错你了。", "滚。"]),
]


def main() -> None:
    rt = Runtime(FakeBody(), poll_every=0, speaker=speaker, path="_smoke20.json")
    rt.aligner = r0
    rt.h.change("Energy", -0.45)   # A 场景：累，容易走 L0
    for title, lines in SCENES:
        if title.startswith(("B", "C", "D")):
            rt.h.change("Energy", +0.5)
        print(f"\n=== {title} ===")
        for line in lines:
            out = rt.hear("owner", line)
            rt.tick()          # 让负荷/冲突分更新（poll=0，不会额外调 LLM）
            if out.get("mode") == "l0":
                reply = out.get("say", "")
            else:
                reply = rt._wake()
            say = rt.says[-1]["say"] if rt.says and rt.says[-1].get("say") else reply
            print(f"他：{line}")
            print(f"她：{say}")
            print(f"   stress={rt.h.stress():.2f} trust={rt.h.value('Trust'):.2f} "
                  f"load={rt.cognitive_load:.2f} R0={out.get('score','-')}")


if __name__ == "__main__":
    main()
