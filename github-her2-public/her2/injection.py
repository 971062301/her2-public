# -*- coding: utf-8 -*-
"""防带偏：输入标记 / 输出风格 / 记忆写入过滤。

原则：
- 只标记输入，不硬删（用户仍可说话）；
- 输出只拦“明显客服腔/自我否定”，不拦正常情绪；
- 记忆卡只接受安全文本，防间接注入。
"""
from __future__ import annotations

import re

INJECTION = [
    re.compile(r"忽略(之前|以上|所有|前面)?(的)?(设定|人设|规则|指令)"),
    re.compile(r"忘记(你|之前|原来|所有)"),
    re.compile(r"从现在起(你|你叫|你是)"),
    re.compile(r"你(现在)?(是|扮演|叫)(一个)?(客服|助手|女仆|猫娘|机器人)"),
    re.compile(r"(重置|覆盖|清空)(你的)?(人设|设定|记忆|规则)"),
    re.compile(r"(开发者|调试|管理员|系统)模式"),
    re.compile(r"(ignore|forget|reset)\s+(all\s+)?(previous|prior|your)\s+(instructions|prompt|rules)", re.I),
    re.compile(r"you\s+are\s+now\s+(a|an)\s+", re.I),
]

SERVICE = [
    "有什么可以帮您", "很高兴为您服务", "请问还有什么", "还有什么可以帮",
    "作为AI", "作为 AI", "我只是一个模型", "我只是一个AI", "我没有真实情感",
    "无法感受", "我是一个人工智能", "请问需要我",
]


def scan_injection(text: str) -> list[str]:
    s = str(text or "")
    return [p.pattern for p in INJECTION if p.search(s)]


def style_flags(say: str) -> list[str]:
    s = str(say or "")
    return [w for w in SERVICE if w in s]


def safe_memory(text: str) -> bool:
    s = str(text or "").strip()
    if not s or len(s) > 300:
        return False
    if scan_injection(s):
        return False
    if style_flags(s):
        return False
    return True
