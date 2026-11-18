# -*- coding: utf-8 -*-
"""L3 内分泌层：模拟的 5 个慢变量 + 真实基底的偏移。

白皮书 §3 + 混合方案：
- simulated：Energy/Safety/Connection/Trust/Autonomy，连续回归；
- measured：上下文占用、延迟、在线时长、库压力——只校准基线/唤醒，
  不替换模拟变量，不冒充“感觉”。
"""
from __future__ import annotations

import inspect
import inspect
from dataclasses import dataclass

DIRECT_WRITES: list[dict] = []


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(x)))


@dataclass
class Var:
    value: float
    baseline: float
    tau: float

    def __setattr__(self, name, value):
        if name == "value" and hasattr(self, "value"):
            try:
                fn = inspect.stack()[1].function
            except Exception:
                fn = "?"
            if fn not in ("settle", "change", "__init__"):
                DIRECT_WRITES.append({"caller": fn, "old": float(self.value),
                                      "new": float(value)})
                DIRECT_WRITES[:] = DIRECT_WRITES[-200:]
        object.__setattr__(self, name, value)

    def settle(self, dt: float) -> None:
        if dt <= 0 or self.tau <= 0:
            return
        self.value += (self.baseline - self.value) * min(1.0, dt / self.tau)
        self.value = _clamp(self.value)


# [先天] 5 个慢变量 + 基线回归 + Stress/PAD：身体生来就会的规律
class Homeostat:
    DEFAULTS = {
        "Energy": (0.7, 0.7, 3600.0),
        "Safety": (0.8, 0.8, 1800.0),
        "Connection": (0.3, 0.3, 600.0),
        "Trust": (0.7, 0.7, 7200.0),
        # Autonomy 由 L4 账本单独写；Homeostat 只定初值，不再回拉
        "Autonomy": (0.8, 0.8, 0.0),
        # 社交疲劳：基线 0，只会往 0 恢复
        "Fatigue": (0.0, 0.0, 1800.0),
        # 威胁记忆：冲突留下的生理余震，半衰回 0
        "Threat": (0.0, 0.0, 600.0),
        # 无聊：L3 第 8 个变量；不向 0 回归，由 runtime 单独驱动
        "Boredom": (0.0, 0.0, 0.0),
    }

    def __init__(self, values: dict[str, float] | None = None,
                 real: dict[str, float] | None = None) -> None:
        self.vars: dict[str, Var] = {}
        for name, (value, baseline, tau) in self.DEFAULTS.items():
            v = (values or {}).get(name, value)
            self.vars[name] = Var(value=v, baseline=baseline, tau=tau)
        # [后天] 实测基底：经历/负载留下的偏移
        self.real: dict[str, float] = {}
        self.provenance: list[dict] = []
        self.set_real(real or {})

    # ---- 真实基底：只偏移基线，不替换变量 ----
    def set_real(self, real: dict[str, float]) -> None:
        self.real = {str(k): float(v) for k, v in (real or {}).items()}
        cl = _clamp(self.real.get("context_load", 0.0))
        lat = _clamp(self.real.get("latency_ms", 0.0) / 2000.0)
        mem = _clamp(self.real.get("memory_pressure", 0.0))
        # 负载高 → 体力基线略降；延迟高 → 安全感基线略降；库压力 → 体力再降
        self.vars["Energy"].baseline = _clamp(0.7 - 0.15 * cl - 0.10 * mem)
        self.vars["Safety"].baseline = _clamp(0.8 - 0.10 * lat)
        self.vars["Connection"].baseline = _clamp(
            0.3 + 0.05 * _clamp(self.real.get("uptime_s", 0.0) / 7200.0))

    def update(self, dt: float) -> None:
        for v in self.vars.values():
            v.settle(dt)

    def change(self, name: str, delta: float) -> None:
        old = self.vars[name].value
        new = _clamp(old + float(delta))
        self.vars[name].value = new
        try:
            caller = inspect.stack()[1].function
        except Exception:
            caller = "?"
        self.provenance = (self.provenance + [{
            "name": name, "old": round(old, 4), "delta": round(float(delta), 4),
            "new": round(new, 4), "caller": caller,
        }])[-500:]

    def value(self, name: str) -> float:
        return self.vars[name].value

    def stress(self) -> float:
        e = self.value("Energy")
        s = self.value("Safety")
        t = self.value("Trust")
        a = self.value("Autonomy")
        c = self.value("Connection")
        e_def = max(0.0, self.DEFAULTS["Energy"][1] - e)
        c_def = max(0.0, c - self.DEFAULTS["Connection"][1])
        threat = self.value("Threat")
        raw = (0.2 * (1 - s) + 0.2 * (1 - t) + 0.2 * (1 - a)
               + 0.2 * e_def + 0.2 * c_def + 0.35 * threat)
        return _clamp(raw)

    def pad(self) -> tuple[float, float, float]:
        e = self.value("Energy")
        t = self.value("Trust")
        c = self.value("Connection")
        sat = 1.0 - c
        st = self.stress()
        a = self.value("Autonomy")
        s = self.value("Safety")
        cl = _clamp(self.real.get("context_load", 0.0))
        P = _clamp(0.2 * e + 0.2 * t + 0.2 * sat, -1.0, 1.0)
        # 真实负载作为唤醒偏移（measured → simulated 的偏移，不替换）
        A = _clamp(0.2 * st + 0.2 * (1 - e) + 0.2 * cl, -1.0, 1.0)
        D = _clamp(0.2 * a + 0.2 * s, -1.0, 1.0)
        return P, A, D

    def release_context(self) -> None:
        """Sue 的睡眠事件：上下文清账（离散事件，不是连续衰减）。"""
        self.real["context_load"] = 0.0
        self.real["latency_ms"] = 0.0

    def rest(self, hours: float = 8.0) -> None:
        """歇一下：回体力、松下来、清上下文；不替她决定醒后做什么。"""
        k = min(1.0, max(0.0, hours) / 8.0)
        self.change("Energy", 0.5 * k)
        self.change("Safety", 0.1)
        self.change("Fatigue", -0.6 * k)
        self.release_context()

    def measured(self) -> dict[str, float]:
        return {"context_load": round(_clamp(self.real.get("context_load", 0.0)), 3),
                "latency_ms": round(max(0.0, self.real.get("latency_ms", 0.0)), 1),
                "uptime_s": round(max(0.0, self.real.get("uptime_s", 0.0)), 1),
                "memory_pressure": round(_clamp(self.real.get("memory_pressure", 0.0)), 3)}

    def simulated(self) -> dict[str, float]:
        return {k: round(v.value, 3) for k, v in self.vars.items()}

    def to_dict(self) -> dict[str, object]:
        p, a, d = self.pad()
        return {"measured": self.measured(), "simulated": self.simulated(),
                "Stress": round(self.stress(), 4),
                "P": round(p, 4), "A": round(a, 4), "D": round(d, 4)}
