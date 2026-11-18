# -*- coding: utf-8 -*-
"""MC 玩耍模块：只在玩 MC 时注入 Runtime。

核心 runtime 不 import 这个文件；不玩 MC 就不加载，也就没有 MC 的体感/动作。
"""
from __future__ import annotations

from .body_live import MCBody


class MCPlay:
    """身体 + 动作的最小接口：see / act / set_asleep / say。"""

    allow_coords = True

    def __init__(self, bridge) -> None:
        self.bridge = bridge
        self.body = MCBody(bridge)
        self.last: dict = {}

    def see(self) -> dict:
        self.last = self.body.see()
        return self.last

    def set_asleep(self, flag: bool) -> dict:
        return self.body.set_asleep(flag)

    def act(self, action: str) -> dict:
        """一次一个动作；真结果由 bot 的 /job 轮，不在这里阻塞。"""
        s = str(action)[:80]
        if s.startswith(("say:", "js:", "/")):
            return {"ok": False, "reason": "act_not_allowed"}
        return self.bridge._post("/act", {"action": s})

    def job(self) -> dict:
        """执行器真实状态：running/finished/blocked/unknown。"""
        fn = getattr(self.bridge, "job", None)
        if fn is None:
            return {"ok": False, "why": "no_job"}
        try:
            return fn() or {"ok": False, "why": "empty_job"}
        except Exception as e:
            return {"ok": False, "why": f"job_error:{e}"}

    def say(self, text: str) -> dict:
        return self.bridge.say(text)

    def close(self) -> None:
        """卸载：停手停脚，不再读状态。"""
        try:
            self.bridge._post("/sleep", {"asleep": True})
        except Exception:
            pass
