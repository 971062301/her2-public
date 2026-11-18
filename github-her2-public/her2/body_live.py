# -*- coding: utf-8 -*-
"""真身体适配：MCBridge.observe() 的输出 → 她2 的 raw_state。

只做形状转换，不做语义判断。
"""
from __future__ import annotations


FOODS = {"apple", "bread", "cooked_beef", "cooked_porkchop", "cooked_chicken",
         "carrot", "baked_potato", "cooked_mutton", "cooked_salmon", "cooked_cod"}


class MCBody:
    def __init__(self, bridge) -> None:
        self.bridge = bridge
        self.last: dict = {}
        self._prev_items: dict = {}

    def see(self) -> dict:
        st = self.bridge.observe() or {}
        me = st.get("self") or {}
        players = {}
        player_positions = {}
        self_name = str(st.get("name") or "")
        for name, p in (st.get("players") or {}).items():
            if self_name and str(name) == self_name:
                continue
            if not self_name and float(p.get("dist", 99) or 99) < 0.5:
                continue
            try:
                players[str(name)] = float(p.get("dist"))
                pp = p.get("pos")
                if isinstance(pp, (list, tuple)) and len(pp) >= 3:
                    player_positions[str(name)] = [round(float(v), 1) for v in pp[:3]]
            except (TypeError, ValueError, AttributeError):
                continue
        items = {}
        for it in (st.get("inventory") or []):
            try:
                name = str(it.get("name"))
                items[name] = items.get(name, 0) + int(it.get("count", 0))
            except (TypeError, ValueError, AttributeError):
                continue
        hostile = st.get("hostile") or []
        near = min((float(h.get("dist", 99)) for h in hostile), default=99.0)
        deaths = sum(1 for e in (st.get("events") or []) if e.get("type") == "death")
        ate = any(name in FOODS and int(items.get(name, 0)) < int(self._prev_items.get(name, 0))
                  for name in items)
        self._prev_items = dict(items)
        pos = me.get("pos") or [0, 0, 0]
        self.last = {"hp": float(me.get("health", 20) or 20),
                "pos": [round(float(v), 1) for v in pos[:3]],
                "food": float(me.get("food", 20) or 20),
                "players": players,
                "player_positions": player_positions,
                "terrain": dict(st.get("terrain") or {}),
                "items": items,
                "hand": (me.get("hand") if "hand" in me else None),
                "in_water": bool(me.get("in_water")),
                "on_ground": bool(me.get("on_ground", True)),
                "hostile_near": round(near, 1),
                "deaths": int(deaths),
                "ate": bool(ate)}
        return self.last

    def set_asleep(self, flag: bool) -> dict:
        """让 MC 身体停手/停脚；模拟身体没有这个接口就忽略。"""
        post = getattr(self.bridge, "_post", None)
        if post is None:
            return {"ok": False, "why": "no_bridge_post"}
        return post("/sleep", {"asleep": bool(flag)})
