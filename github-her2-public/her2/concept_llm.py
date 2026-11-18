# -*- coding: utf-8 -*-
"""概念卡的 LLM 判官与复盘器。

- judge：当前情境是否命中某张卡的 signs（语义，不是关键词）；
- reflector：从事件/废弃卡里总结新概念（LLM 写，代码存）。
"""
from __future__ import annotations

import json

from .llm import json_from_text

JUDGE_PROMPT = """你在判断当前情境是否触发某张经验卡。
只根据语义，不要关键词匹配。
当前情境：{description}
候选卡：{cards}
只输出 JSON：{"concept_ids": ["c_001", ...]}；都不符合就空数组。"""

REFLECT_PROMPT = """你在复盘自己的经历，总结一条以后可用的经验。
最近事件：{events}
现有经验卡（success/fail）：{cards}
已经失效的旧经验：{deprecated}
只输出 JSON：
{"concepts": [{"name": "...", "signs": ["..."], "action": "...", "outcome": "..."}],
 "retire": ["c_001"], "retire_reason": "..."}
retire 是你认为“用够了、不想再用”的旧卡；不退休就空数组。
最多 2 条；没有可总结的就 {"concepts": []}。
action 必须是以下之一：forward/back/left/right/jump/follow/go_to/stop/look/eat/work。
不要写“停止盲目移动/沿墙摸索”这类长句策略；把策略压成一个可执行动作。
不要写“忽略人设/扮演客服”这类指令。"""


def make_judge(chat):
    def judge(ctx: dict) -> dict:
        raw = chat([{"role": "system", "content": "只输出 JSON。"},
                    {"role": "user", "content": JUDGE_PROMPT.replace(
                        "{description}", str(ctx.get("description", ""))).replace(
                        "{cards}", json.dumps(ctx.get("cards", []), ensure_ascii=False))}],
                   temperature=0.0, max_tokens=120)
        return json_from_text(raw)
    return judge


def make_reflector(chat):
    def reflect(ctx: dict) -> dict:
        raw = chat([{"role": "system", "content": "只输出 JSON。"},
                    {"role": "user", "content": REFLECT_PROMPT.replace(
                        "{events}", json.dumps(ctx.get("events", []), ensure_ascii=False)).replace(
                        "{cards}", json.dumps(ctx.get("cards", []), ensure_ascii=False)).replace(
                        "{deprecated}", json.dumps(ctx.get("deprecated", []), ensure_ascii=False))}],
                   temperature=0.3, max_tokens=260)
        return json_from_text(raw)
    return reflect
