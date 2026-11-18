# -*- coding: utf-8 -*-
"""2D/VRM 前端桥：把她的 say / pose 发给本地小窗。

可选模块；不注入 avatar 时 runtime 完全不依赖它。
"""
from __future__ import annotations

import json
import urllib.request


class AvatarBridge:
    def __init__(self, base: str = "http://127.0.0.1:8799", timeout: float = 1.5):
        self.base = base.rstrip("/")
        self.timeout = float(timeout)

    def _post(self, path: str, obj: dict) -> None:
        try:
            data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(self.base + path, data=data,
                                         headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=self.timeout).read()
        except Exception:
            pass

    def say(self, text: str) -> None:
        if text:
            self._post("/say", {"text": str(text)[:200]})

    def motion(self, speed: float, moved: bool = False) -> None:
        self._post("/motion", {"speed": float(speed), "moved": bool(moved)})

    def pose(self, name: str) -> None:
        if name:
            self._post("/act", {"pose": str(name)})
