# -*- coding: utf-8 -*-
"""把旧项目（她/）的人设与记忆接进她2 的慢档。

只读旧库，不写；旧项目继续冻结。
"""
from __future__ import annotations

import math
import sqlite3
import time
from pathlib import Path

DEFAULT_PERSONA = Path(__file__).resolve().parents[2] / "她" / "人设-大肥鱼.md"
DEFAULT_DB = Path(__file__).resolve().parents[2] / "她" / "MC" / "她_数据" / "her_memory.db"


def load_persona(path: str | Path | None = None) -> str:
    p = Path(path) if path else DEFAULT_PERSONA
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8").strip()


def _grams(s: str) -> set[str]:
    s = "".join(ch for ch in str(s) if not ch.isspace())
    return {s[i:i + 2] for i in range(max(0, len(s) - 1))} or {s}


def _sim(a: str, b: str) -> float:
    ga, gb = _grams(a), _grams(b)
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / math.sqrt(len(ga) * len(gb))


def recall(db: str | Path | None = None, query: str = "", k: int = 5) -> list[str]:
    """从旧记忆库取最相关的几条（字面相似 + 新近 + |电荷|）。"""
    p = Path(db) if db else DEFAULT_DB
    if not p.exists():
        return []
    con = sqlite3.connect(str(p))
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT raw, occurred_at, charge FROM memories "
        "WHERE deleted=0 AND state!='stale' AND raw!='' "
        "ORDER BY occurred_at DESC LIMIT 300").fetchall()
    con.close()
    now = time.time()
    scored = []
    for r in rows:
        raw = str(r["raw"])
        rec = math.exp(-max(0.0, now - float(r["occurred_at"] or now)) / (86400 * 7))
        ch = abs(float(r["charge"] or 0.0))
        s = 0.7 * _sim(query, raw) + 0.2 * rec + 0.1 * ch
        scored.append((s, raw))
    scored.sort(reverse=True)
    return [raw for _, raw in scored[:max(0, k)]]
