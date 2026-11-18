# -*- coding: utf-8 -*-
"""形式化层：干预响应、元认知效用、声带概率。全部连续，无 if 阈值。"""
from __future__ import annotations

import math


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(x)))


def sigmoid(z: float) -> float:
    z = max(-60.0, min(60.0, float(z)))
    return 1.0 / (1.0 + math.exp(-z))


def approach_value(connection: float, trust: float, safety: float,
                   fatigue: float = 0.0) -> float:
    """威胁越高，越想找人确认；疲劳压制。"""
    return (_clamp(connection) * _clamp(trust)
            * (1.0 + 0.6 * (1.0 - _clamp(safety)))
            * (1.0 - 0.7 * _clamp(fatigue)))


def stutter_probability(fear: float, stress: float, energy: float) -> float:
    """预注册公式：sigmoid(2F + 1.5S + 0.8(1-E) - 4)。"""
    z = 2.0 * _clamp(fear) + 1.5 * _clamp(stress) + 0.8 * (1.0 - _clamp(energy)) - 4.0
    return sigmoid(z)


def pause_type(fear: float, energy: float) -> str:
    """二维网格：高Fear+低Energy→断气省略号；高Fear+高Energy→急促重复。"""
    f, e = _clamp(fear), _clamp(energy)
    if f >= 0.6 and e < 0.4:
        return "breath_ellipsis"
    if f >= 0.6 and e >= 0.4:
        return "rapid_repeat"
    return "none"


# [体感翻译] seek=想找他，silence=不想说；高连接不压 seek，只压 silence。
def utility(confidence: float, connection: float, autonomy: float,
            energy: float) -> dict[str, float]:
    """想找他 / 不想说 / 犹豫。连续，无阈值。

    seek：有精力、有自主、且越缺陪伴越高；高连接仍保留一点“想找他”的底。
    silence：越累越高；高连接会压低它（再累也想跟他说两句）。
    """
    c, conn, a, e = (_clamp(confidence), _clamp(connection),
                     _clamp(autonomy), _clamp(energy))
    seek = e * a * (0.35 + 0.65 * (1.0 - conn))
    silence = (1.0 - e) * (1.0 - 0.3 * conn)
    hesitation = 1.0 - abs(seek - silence)
    return {"seek_information": round(seek, 6),
            "silence": round(silence, 6),
            "hesitation": round(hesitation, 6)}


def translate_utility(u: dict[str, float]) -> str:
    """把效用翻成第一人称体感，而不是数字。"""
    seek = float(u.get("seek_information", 0.0))
    silence = float(u.get("silence", 0.0))
    hesitation = float(u.get("hesitation", 0.0))
    if seek > silence + 0.15:
        line = "你想主动找他，渴望他的回应。"
    elif silence > seek + 0.15:
        line = "你现在有点累，或者心情一般，不想主动说话。"
    else:
        line = "你在犹豫，既想找他，又觉得没什么好说的。"
    if hesitation > 0.8:
        line += "话到嘴边又咽下去了。"
    return line


def choose_strategy(confidence: float, connection: float,
                    autonomy: float, energy: float) -> str:
    u = utility(confidence, connection, autonomy, energy)
    return max(u, key=u.get)


def approach_gate_ablation(connection: float, trust: float, safety: float) -> str:
    """消融：单一 approach 门控——只会犹豫，不会发问（对照）。"""
    return "delay"
