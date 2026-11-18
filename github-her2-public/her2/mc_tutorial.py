# -*- coding: utf-8 -*-
"""MC 新手教程：给目标/提示/判定，不教“按哪个键”。

教程是外部教材（像人看的说明书），不是写死策略：
- 代码只判断“这一步过没过”；
- 怎么走、怎么跳，由她自己试或 LLM 决定。
只在玩 MC 时加载。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Step:
    id: str
    goal: str
    hint: str
    check: object          # (state, ctx) -> bool
    skip: object = None    # (state, ctx) -> bool；当前条件不具备则跳过
    done: bool = False


@dataclass
class Tutorial:
    steps: list[Step] = field(default_factory=list)
    idx: int = 0
    learned: list[str] = field(default_factory=list)
    ctx: dict = field(default_factory=dict)
    danger: object = None       # (state, ctx) -> bool
    danger_goal: str = "先保命：离开危险，再回来上课。"
    danger_hint: str = "血太少、怪太近或在水里；先处理，别管教程。"
    in_danger: bool = False
    settle_ticks: int = 0
    ticks: int = 0

    def start(self, state: dict) -> dict:
        self.ctx = {"start_pos": (state.get("pos") or [0, 0, 0])[:]}
        self.ticks = 0
        return self.current()

    def board(self) -> list[dict]:
        """任务栏：每步 0/1，当前步标记 current。"""
        out = []
        for i, s in enumerate(self.steps):
            out.append({"id": s.id, "goal": s.goal,
                        "done": 1 if s.done else 0,
                        "current": 1 if (i == self.idx and not self.in_danger) else 0})
        return out

    def text(self) -> str:
        lines = []
        for i, s in enumerate(self.steps):
            mark = "x" if s.done else ("→" if i == self.idx and not self.in_danger else " ")
            lines.append(f"{i + 1}. [{mark}] {s.goal} ({1 if s.done else 0}/1)")
        if self.in_danger:
            lines.append(f"! [危险] {self.danger_goal}")
        return "\n".join(lines)

    def current(self) -> dict:
        if self.in_danger:
            return {"done": False, "step": "danger", "danger": True,
                    "goal": self.danger_goal, "hint": self.danger_hint,
                    "index": self.idx, "total": len(self.steps)}
        if self.idx >= len(self.steps):
            return {"done": True, "goal": "教程结束", "hint": "", "step": "done"}
        s = self.steps[self.idx]
        return {"done": False, "step": s.id, "goal": s.goal, "hint": s.hint,
                "index": self.idx, "total": len(self.steps)}

    def update(self, state: dict) -> dict:
        """返回当前步骤；先等身体稳定，再有危险暂停，最后才判步。"""
        self.ticks += 1
        if self.ticks <= self.settle_ticks:
            return self.current()
        if self.danger is not None:
            try:
                self.in_danger = bool(self.danger(state, self.ctx))
            except Exception:
                self.in_danger = False
            if self.in_danger:
                return self.current()
        while self.idx < len(self.steps):
            s = self.steps[self.idx]
            try:
                ok = bool(s.check(state, self.ctx))
            except Exception:
                ok = False
            if not ok and s.skip is not None:
                try:
                    if s.skip(state, self.ctx):
                        s.done = True
                        self.learned.append(s.goal + "（当前做不了，跳过）")
                        self.idx += 1
                        continue
                except Exception:
                    pass
            if not ok:
                break
            s.done = True
            self.learned.append(s.goal)
            self.idx += 1
        return self.current()


def _pos(state):
    return state.get("pos") or [0, 0, 0]


def _moved(state, ctx):
    p0 = ctx.get("start_pos") or [0, 0, 0]
    p = _pos(state)
    return (abs(p[0] - p0[0]) + abs(p[2] - p0[2])) >= 2


def _jumped(state, ctx):
    return bool(state.get("on_ground")) is False or state.get("jumped") is True


def _safe(state, ctx):
    return (not state.get("in_water")) and float(state.get("hostile_near", 99)) > 4


def _has_food(state):
    foods = {"apple", "bread", "cooked_beef", "cooked_porkchop", "cooked_chicken",
             "carrot", "baked_potato", "cooked_mutton", "cooked_salmon", "cooked_cod"}
    return any(name in foods for name in (state.get("items") or {}))


def _ate(state, ctx):
    return float(state.get("food", 20)) >= 18 and bool(state.get("ate"))


def _danger(state, ctx):
    return (float(state.get("hp", 20)) < 8
            or float(state.get("hostile_near", 99)) < 3
            or bool(state.get("in_water")))


MC_BASICS = Tutorial(danger=_danger, settle_ticks=30, steps=[
    Step("look", "先看看四周", "转转头，看清前后左右有什么。", lambda s, c: True),
    Step("walk", "往前走两步", "按前进，别掉进水里。", _moved),
    Step("jump", "跳一下", "试试跳跃，跳上矮台阶。", _jumped),
    Step("safe", "站到岸上/远离怪", "如果在水里或有怪，先离开。", _safe),
    Step("eat", "吃点东西", "饿了就吃，别掉血。", _ate,
         skip=lambda s, c: float(s.get("food", 20)) >= 18 or not _has_food(s)),
])
