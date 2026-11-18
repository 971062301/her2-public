# -*- coding: utf-8 -*-
"""最小 OpenAI 兼容客户端（stdlib，无依赖）。"""
from __future__ import annotations

import json
import os
import urllib.request


def chat(messages: list[dict], model: str | None = None,
         temperature: float = 0.8, max_tokens: int = 200) -> str:
    base = os.environ.get("DSH_BASE", "http://127.0.0.1:11434/v1").rstrip("/")
    key = os.environ.get("DSH_KEY", "sk-local")
    model = model or os.environ.get("DSH_MODEL", "qwen2.5:3b")
    payload = {"model": model, "messages": messages,
               "temperature": temperature, "max_tokens": max_tokens}
    if os.environ.get("DSH_SEED"):
        payload["seed"] = int(os.environ["DSH_SEED"])
    if os.environ.get("DSH_JSON_MODE", "1") != "0":
        payload["response_format"] = {"type": "json_object"}
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(base + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + key})
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"] or ""


def json_from_text(text: str) -> dict:
    """从模型输出里抠出第一个完整 JSON 对象；容忍前后废话。"""
    import json as _json
    s = str(text or "").strip()
    try:
        return _json.loads(s)
    except Exception:
        pass
    start = s.find("{")
    if start < 0:
        raise ValueError("no json")
    depth = 0
    for i in range(start, len(s)):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return _json.loads(s[start:i + 1])
    raise ValueError("unclosed json")
