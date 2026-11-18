# -*- coding: utf-8 -*-
"""R0：对齐度判断层（只管判，不管准入）。

输入：完整轮次 + 关系上下文
输出：{score: 0..1 | None, confidence, evidence, reason}
- 没有判官（人或模型）→ unknown；
- 歧义 → unknown；
- 它不碰校准闸门、不碰 Stress/P（那是 R1）。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Alignment:
    score: float | None = None       # 冲突/威胁分（runtime 用）
    threat: float | None = None
    confidence: float = 0.0
    evidence: list[str] = field(default_factory=list)
    reason: str = "no_judge"

    @property
    def unknown(self) -> bool:
        return self.score is None or self.reason != "ok"


def align(turn: dict, relation: str = "", judge=None) -> Alignment:
    """turn = {"a": 上一句, "b": 这一句}；judge 是人/模型/规则。"""
    if not isinstance(turn, dict) or not turn.get("b"):
        return Alignment(reason="incomplete_turn")
    if judge is None:
        return Alignment(reason="no_judge")
    try:
        out = judge(dict(turn), relation)
    except Exception:
        return Alignment(reason="judge_error")
    if not isinstance(out, dict):
        return Alignment(reason="bad_output")
    if (out.get("reason") == "ambiguous"
            or (out.get("score") is None and out.get("threat") is None)):
        return Alignment(reason=out.get("reason") or "ambiguous")
    threat = out.get("threat")
    if threat is not None:
        s = max(0.0, min(1.0, float(threat)))
    else:
        s = max(0.0, min(1.0, float(out.get("score", 0.0))))
    ev = list(out.get("evidence") or [])
    c = max(0.0, min(1.0, float(out.get("confidence", 0.0))))
    if not ev:
        c = 0.0
    return Alignment(score=s, threat=s, confidence=c, evidence=ev, reason="ok")
