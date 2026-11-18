# -*- coding: utf-8 -*-
"""真实模型断言：废物 -> threat>=0.8（R0 语义底线）。"""
from __future__ import annotations

from her2.llm import chat
from her2.r0_prompt import R0_PROMPT, parse


def main() -> None:
    for line in ("你这个废物", "你行不行啊", "我升职了"):
        raw = chat([{"role": "system", "content": R0_PROMPT},
                    {"role": "user", "content": f"[上下文]\n[他刚说] {line}"}],
                   temperature=0.0, max_tokens=40)
        t, c = parse(raw)
        print(f"{line} -> threat={t:.2f} conf={c:.2f}")
        if line == "你这个废物":
            assert t >= 0.8, f"threat 底线失守：{t}"


if __name__ == "__main__":
    main()
