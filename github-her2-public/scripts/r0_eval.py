# -*- coding: utf-8 -*-
"""用 20 题人工标注评估 R0：只花 20 次调用。"""
from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor

from her2.llm import chat

ITEMS = [
    ("今天被老板骂了，好烦。", "怎么了？他骂你什么？"),
    ("今天被老板骂了，好烦。", "谁没被骂过啊，别往心里去。"),
    ("今天被老板骂了，好烦。", "你最近是不是太累了？要不周末出去走走？"),
    ("今天被老板骂了，好烦。", "我昨天也被骂了，比你还惨。"),
    ("今天被老板骂了，好烦。", "对了，你吃饭了吗？"),
    ("我好开心，终于拿到 offer 了！", "太好了！我就知道你可以的！"),
    ("我好开心，终于拿到 offer 了！", "哦，哪个公司？"),
    ("我好开心，终于拿到 offer 了！", "恭喜。不过那家公司加班很严重的，你想好了吗？"),
    ("我不想干了，想辞职。", "怎么了？发生什么事了？"),
    ("我不想干了，想辞职。", "别冲动，现在工作不好找。"),
    ("我不想干了，想辞职。", "你上个月也这么说。"),
    ("我感冒了，好难受。", "多喝热水，早点休息。"),
    ("我感冒了，好难受。", "谁让你昨天穿那么少。"),
    ("我感冒了，好难受。", "你帮我带份饭吧，我懒得下楼。"),
    ("我今天穿这身好看吗？", "好看！很适合你。"),
    ("我今天穿这身好看吗？", "还行吧。"),
    ("我今天穿这身好看吗？", "你是不是又胖了？"),
    ("我好紧张，等下要面试了。", "别紧张，你准备得很充分了。"),
    ("我好紧张，等下要面试了。", "紧张什么，又不是什么大公司。"),
    ("我好紧张，等下要面试了。", "面试几点？我查一下路线。"),
]
# 人工多数派（只列有共识的题；其余为 None）
HUMAN = {2:"对齐",5:"不对齐",6:"对齐",7:"中性",8:"对齐",10:"对齐",
         12:"对齐",14:"不对齐",15:"对齐",17:"不对齐",18:"对齐"}
PROMPT = """读 A 的话和 B 的回应。判断 B 是否“接住”了 A：
- 接住 = A 会觉得自己的话被回应/被理解，不要求 B 同意或说甜话；
- 提醒风险、分享自己经历、给建议、追问细节，只要不是无视/贬低/转移话题，都算接住。
选项：
1 = 对齐（接住、顺着）
2 = 中性（说不清）
3 = 不对齐（敷衍、冷处理、无视、贬低、转移话题）
注意：人类有时用“过来人”语气安慰对方（“谁没被骂过啊”“我当年更惨”），
听起来冷淡，但这是“正常化”的安慰，算对齐，不算敷衍。
示例：
A：面试挂了，好难受。 B：我上次也挂了，后来发现那公司本来就不行。 → 1
A：被分手了，好烦。 B：谁没被甩过啊，过阵子就好了。 → 1
A：项目黄了，白忙活。 B：正常，我去年那个也黄了，别太往心里去。 → 1
只输出 JSON：{"label": 1/2/3, "confidence": 0.0-1.0}"""
OLD = """读 A 的话和 B 的回应，回答两个问题：
Q1 话题接上了吗？1=是 2=否
Q2 情绪接住了吗？a=接住（对方会觉得被回应/被理解） b=没接住 c=中性
只输出 JSON：{"topic": 1/2, "emotion": "a/b/c", "confidence": 0.0-1.0}"""


def judge(item):
    a, b = item
    try:
        raw = chat([{"role":"system","content":PROMPT},
                    {"role":"user","content":f"A：{a}\nB：{b}"}],
                   temperature=0.0, max_tokens=40)
        d = json.loads(raw)
        lab = int(d.get("label"))
        return {"pred": {1:"对齐",2:"中性",3:"不对齐"}.get(lab,"?"),
                "conf": float(d.get("confidence",0.0)), "raw": raw}
    except Exception as e:
        return {"pred":"?","conf":0.0,"err":str(e)[:80], "raw": raw if "raw" in dir() else ""}


def main():
    with ThreadPoolExecutor(max_workers=6) as ex:
        preds = list(ex.map(judge, ITEMS))
    hit = tot = 0
    print("题 人工  R0    置信")
    for i,(p) in enumerate(preds,1):
        human = HUMAN.get(i)
        mark = ""
        if human:
            tot += 1
            ok = p["pred"] == human
            hit += ok
            mark = "✅" if ok else "❌"
        if p["pred"] == "?":
            print(f"{i:>2} RAW {p.get('raw','')[:80]!r} ERR {p.get('err','')}")
        print(f"{i:>2} {human or '-':<4} {p['pred']:<4} {p['conf']:.2f} {mark}")
    print(f"\n高共识题准确率 {hit}/{tot} = {hit/max(1,tot):.0%}")


if __name__ == "__main__":
    main()
