# -*- coding: utf-8 -*-
"""延迟顿悟：普通对话也入情景库；负面结果出现时回溯“因”，再判一次。

- 存：每句话带时间/说话人/当时分数；
- 触发：强负面事件（冲突/掉血/Trust 骤降）；
- 回溯：窗口内、同一说话人的“当时好话”；
- 复盘：交给 judge（人/LLM），代码不自己诊断；
- 清算：只有 judge 说“是”，才倒扣 + 记事实。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TurnRecord:
    text: str
    speaker: str
    at: float
    score: float          # 当时判的对齐分：低=好话
    kind: str = "chat"


def remember(log: list[TurnRecord], text: str, speaker: str,
             at: float, score: float) -> TurnRecord:
    r = TurnRecord(str(text)[:120], str(speaker), float(at), float(score))
    log.append(r)
    return r


def find_cause(log: list[TurnRecord], now: float, speaker: str,
               window: float = 3600.0, good_below: float = 0.35) -> TurnRecord | None:
    """找窗口内、同一说话人、当时被判为好话的最近一条。"""
    cands = [r for r in log
             if r.speaker == speaker and 0 <= now - r.at <= window
             and r.score < good_below]
    if not cands:
        return None
    return max(cands, key=lambda r: r.at)


def reappraise(prior: TurnRecord, trigger: str, judge=None) -> dict:
    """返回 {label: unknown|retro_bad|retro_ok, confidence, why}。"""
    if judge is None:
        return {"label": "unknown", "confidence": 0.0, "why": "no_judge"}
    try:
        out = judge({"a": prior.text, "speaker": prior.speaker,
                     "at": prior.at}, trigger) or {}
    except Exception:
        return {"label": "unknown", "confidence": 0.0, "why": "judge_error"}
    label = out.get("label")
    if label not in ("retro_bad", "retro_ok"):
        return {"label": "unknown", "confidence": 0.0, "why": "bad_label"}
    return {"label": label,
            "confidence": max(0.0, min(1.0, float(out.get("confidence", 0.0)))),
            "why": str(out.get("why") or ""),
            "lesson": str(out.get("lesson") or "")[:300]}


def correction_amount(confidence: float, base: float = 0.12) -> float:
    """清算幅度：置信越高，倒扣越多；有界。"""
    return round(base * max(0.0, min(1.0, float(confidence))), 4)
