# -*- coding: utf-8 -*-
"""24 小时挂机（模拟，不接 LLM）：衰减/半衰/巩固/做梦。"""
from __future__ import annotations

from her2 import Runtime, FakeBody

HOUR = 3600


def main() -> None:
    rt = Runtime(FakeBody(), poll_every=0, path="_idle24.json")
    rt.h.change("Threat", 0.8)
    rt.h.change("Fatigue", 0.5)
    rt.l0.add("草", kind="habit")
    rt.l0.dict["草"].weight = 1.0
    rt.consolidate_every = 0
    print("t(h) threat stress fatigue safety trust l0")
    for i in range(1, 24 * HOUR + 1):
        rt.tick()
        if i % HOUR == 0:
            h = i // HOUR
            if h % 4 == 0:
                rt.dream_now()
                rt.consolidate_now()
            print(f"{h:>2} {rt.h.value('Threat'):.3f} {rt.h.stress():.3f} "
                  f"{rt.h.value('Fatigue'):.3f} {rt.h.value('Safety'):.3f} "
                  f"{rt.h.value('Trust'):.3f} {len(rt.l0.dict)} "
                  f"rel={rt.relations.get('owner').trust:.3f} "
                  f"habit={rt.l0.dict.get('草').weight if '草' in rt.l0.dict else 0:.3f}")
    rt.save()
    rt2 = Runtime(FakeBody(), path="_idle24.json")
    print("reload", rt2.load(), "tick", rt2.tick_no,
          "threat", round(rt2.h.value("Threat"), 3),
          "l0", list(rt2.l0.dict))


if __name__ == "__main__":
    main()
