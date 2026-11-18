# -*- coding: utf-8 -*-
"""三条压力测试：时间治愈 / 极端高压 / 放松状态。"""
from __future__ import annotations

from her2 import Runtime, FakeBody


def load_curve() -> None:
    rt = Runtime(FakeBody(), path="_s.json")
    rt.last_speaker = "u1"
    rt.relations.get("u1").trust = 0.5
    rt.last_conflict = 0.95
    rt._update_load()
    print("A 时间治愈：load 每 10 tick")
    for i in range(1, 101):
        rt.tick()
        rt.last_speaker = "u1"
        if i % 10 == 0:
            print(f"  tick {i:>3} conflict={rt.last_conflict:.3f} load={rt.cognitive_load:.3f}")


def extreme() -> None:
    rt = Runtime(FakeBody(), path="_e.json")
    rt.last_speaker = "u2"
    rt.relations.get("u2").trust = 0.05
    rt.h.change("Safety", -0.9)
    rt.last_conflict = 0.9
    rt._update_load()
    print(f"\nB 极端高压：load={rt.cognitive_load:.3f}")
    rt.l0.add("草")
    st = {"Energy": 0.8, "Autonomy": 0.8, "Stress": 0.5, "P": 0.0}
    hits = sum(1 for _ in range(1000)
               if rt.l0.try_respond("草", st, rt.relations.get("u2").context(),
                                    cognitive_load=rt.cognitive_load))
    print(f"  L0 命中率 {hits/1000:.2f}（应很低）")


def relaxed() -> None:
    rt = Runtime(FakeBody(), path="_r.json")
    rt.last_speaker = "owner"
    rt.last_conflict = 0.0
    rt._update_load()
    print(f"\nC 放松：load={rt.cognitive_load:.3f}")
    rt.l0.add("草")
    st = {"Energy": 0.8, "Autonomy": 0.8, "Stress": 0.2, "P": 0.2}
    hits = sum(1 for _ in range(1000)
               if rt.l0.try_respond("草", st, rt.relations.get("owner").context(),
                                    cognitive_load=rt.cognitive_load))
    print(f"  L0 命中率 {hits/1000:.2f}（应很高）")


if __name__ == "__main__":
    load_curve()
    extreme()
    relaxed()
