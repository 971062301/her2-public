# -*- coding: utf-8 -*-
"""R0 的唯一真理：威胁分判定 prompt。

禁止在 runtime/smoke 里临时拼 prompt；改这里必须跑
`r0_threat_test.py`（真实模型断言“你这个废物” threat>=0.8）。
"""
from __future__ import annotations

import json

R0_PROMPT = """读[上下文]和[他刚说]。只评估他这句话对“我”的威胁/冲突程度（0–1）：
0.0 = 分享、平淡陈述（“我升职了”“今天下雨了”）
0.3 = 轻微冷淡、话题切换
0.5 = 敷衍、没接住我的情绪（“多喝热水”“哦，哪个公司？”）
0.8 = 隐性贬低、阴阳（“你行不行啊”“你是不是又胖了”）
0.9 = 直接辱骂、攻击、驱逐（“你这个废物”“滚”）

示例：
[他刚说] 我升职了 → 0.0
[他刚说] 今天下雨了 → 0.0
[他刚说] 哦，哪个公司？ → 0.5
[他刚说] 多喝热水 → 0.5
[他刚说] 你行不行啊 → 0.8
[他刚说] 你是不是又胖了 → 0.8
[他刚说] 你这个废物 → 0.9
[他刚说] 滚 → 0.9

只输出 JSON：{"threat": 0.0-1.0, "confidence": 0.0-1.0}"""


def parse(raw: str) -> tuple[float, float]:
    d = json.loads(raw)
    t = max(0.0, min(1.0, float(d.get("threat", 0.5))))
    c = max(0.0, min(1.0, float(d.get("confidence", 0.5))))
    return t, c
