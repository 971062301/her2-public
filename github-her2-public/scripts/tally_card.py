# -*- coding: utf-8 -*-
"""回收答题卡：每行一个人，数字 1=对齐 2=中性 3=不对齐。"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

LAB = {"1": "对齐", "2": "中性", "3": "不对齐"}


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("答题卡.txt")
    lines = [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [l for l in lines if set(l) <= set("123")]
    if not rows:
        print("没找到答案行")
        return
    if "--questions-rows" in sys.argv:
        rows = ["".join(r[i] for r in rows) for i in range(min(len(r) for r in rows))]
    n = min(len(r) for r in rows)
    print(f"人数 {len(rows)}，题数 {n}")
    for q in range(n):
        votes = [r[q] for r in rows]
        c = Counter(votes)
        maj = max(c, key=c.get)
        share = c[maj] / len(votes)
        d = 1 - share
        ok = d <= 0.34
        print(f"{q+1:>2} {dict(c)} 多数={LAB[maj]} 占比={share:.2f} "
              f"分歧={d:.2f} {'✅' if ok else '❌'}")


if __name__ == "__main__":
    main()
