# -*- coding: utf-8 -*-
"""慢档实机试跑：同一 Connection，Trust 高/低，看台词姿态是否不同。

用法（需要 OpenAI 兼容端点）：
  $env:DSH_BASE="http://127.0.0.1:11434/v1"
  $env:DSH_MODEL="qwen2.5:3b"
  python -X utf8 dry_run_slow.py
"""
from __future__ import annotations

import json
import os
import sys

from her2 import Homeostat, slow_payload, slow_messages, check_slow
from her2.bridge_legacy import load_persona, recall
from her2.llm import chat          # 可替换：任意 OpenAI 兼容客户端

CASES = {
    "trust_high": {"Trust": 0.8, "Connection": 0.9, "Energy": 0.6},
    "trust_low": {"Trust": 0.2, "Connection": 0.9, "Energy": 0.6},
}
CACHE = {
    "trust_high": ["他说会回我，然后回了"],
    "trust_low": ["上次你说会回我，但没回", "你最近说话变短了"],
}
THOUGHTS = ["他是不是不想理我了"]


def one(name: str, values: dict[str, float]) -> str:
    real = {"context_load": float(os.environ.get("DSH_CONTEXT", "0")),
            "latency_ms": float(os.environ.get("DSH_LATENCY", "0"))}
    h = Homeostat(values, real=real)
    persona = load_persona(os.environ.get("DSH_PERSONA") or None)
    old = recall(os.environ.get("DSH_DB") or None, "在吗，怎么不回我", k=5)
    payload = slow_payload(h, memory=(old or CACHE[name]), internal_thoughts=THOUGHTS,
                           context_window=["他：在吗"])
    raw = chat(slow_messages(payload, identity=persona))
    try:
        obj = json.loads(raw)
    except Exception:
        return f"[parse-fail] {raw[:80]}"
    try:
        return check_slow(obj, THOUGHTS)["say"]
    except ValueError as e:
        return f"[violation] {e} :: {raw[:80]}"


def main() -> None:
    for name, values in CASES.items():
        print(f"\n{name}  {values}  context={os.environ.get('DSH_CONTEXT','0')}")
        print("  ->", one(name, values))
    sys.exit(0)


if __name__ == "__main__":
    main()
