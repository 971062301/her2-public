# -*- coding: utf-8 -*-
"""L1 文本读数：只测，不解释。

不出现“讽刺/敌意/冷落”，只给标点、长度、重复、问句等可测特征。
语音版以后加 F0/语速偏差，接口不变。
"""
from __future__ import annotations

import re


def features(text: str) -> dict[str, float]:
    s = str(text or "")
    n = len(s)
    if n == 0:
        return {"len": 0.0, "punct_ratio": 0.0, "ellipsis": 0.0,
                "question": 0.0, "exclaim": 0.0, "repeat_run": 0.0,
                "avg_sentence": 0.0}
    punct = sum(1 for ch in s if ch in "，。！？、；：,.!?;:…")
    ell = s.count("…") + s.count("...")
    sentences = [x for x in re.split(r"[。！？.!?]", s) if x.strip()]
    avg = (sum(len(x) for x in sentences) / len(sentences)) if sentences else float(n)
    run = max((len(m.group(0)) for m in re.finditer(r"(.)\1+", s)), default=1)
    return {"len": float(n),
            "punct_ratio": round(punct / n, 4),
            "ellipsis": float(ell),
            "question": 1.0 if ("?" in s or "？" in s) else 0.0,
            "exclaim": 1.0 if ("!" in s or "！" in s) else 0.0,
            "repeat_run": float(run),
            "avg_sentence": round(avg, 2)}
