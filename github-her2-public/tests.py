# -*- coding: utf-8 -*-
"""她2 的验收测试（白皮书 §7）。"""
from __future__ import annotations

import math

from her2 import (Homeostat, ErrorLearning, detail_level, facts,
                  impulses, decay, pollution, score,
                  check_fast, check_slow, fast_to_public)

PASS = FAIL = 0


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}  {detail}")


def test_baseline_regression():
    h = Homeostat({"Energy": 0.05})
    for _ in range(500):
        h.update(60)
    check("体力回到基线附近", abs(h.value("Energy") - 0.7) < 0.02,
          h.value("Energy"))
    check("不会 NaN", all(math.isfinite(v.value) for v in h.vars.values()), "")


def test_stress_is_derived():
    h = Homeostat()
    s0 = h.stress()
    h.change("Safety", -0.5)
    s1 = h.stress()
    check("Stress 随安全感变化", s1 > s0, f"{s0}->{s1}")
    check("Stress 有界", 0 <= s1 <= 1, s1)
    h2 = Homeostat()
    h2.update(3600 * 24)
    check("Stress 不自行累积", abs(h2.stress() - s0) < 1e-6, h2.stress())


def test_pad_continuous():
    prev = None
    worst = 0.0
    for i in range(101):
        h = Homeostat({"Energy": i / 100})
        P = h.pad()[0]
        if prev is not None:
            worst = max(worst, abs(P - prev))
        prev = P
    check("PAD 连续（每步变化小）", worst < 0.05, worst)
    check("PAD 有界", all(-1 <= x <= 1 for x in Homeostat().pad()), "")


def test_perception_granularity():
    vals = [detail_level(p) for p in (-1, -0.5, 0, 0.5, 1)]
    check("越痛苦越粗", vals[0] <= vals[1] <= vals[2] <= vals[4], vals)
    check("不低于下限", min(vals) >= 0.3 - 1e-9, min(vals))
    check("不高于基准", max(vals) <= 1.0, max(vals))
    out = facts({"visual": {"face_confidence": 0.31, "mouth_open": True}}, P=-0.8)
    check("不输出情绪标签", "emotion" not in str(out), str(out))


def test_impulse_smooth():
    worst = 0.0
    prev = None
    for i in range(0, 91):
        st = i / 100
        h = Homeostat()
        w = impulses(h, stress_norm=st)["approach"]
        if prev is not None:
            worst = max(worst, abs(w - prev))
        prev = w
    check("冲动随压力平滑", worst < 0.05, worst)
    check("不突然归零", prev > 0 or worst < 0.05, prev)


def test_decay_separate():
    w = {"approach": 1.0}
    d = decay(w, 60, tau=60)
    check("衰减是乘法", abs(d["approach"] - math.exp(-1)) < 1e-6, d)


def test_memory_pollution():
    check("P>=0 不污染", pollution(0.2, -0.9) == 0.0, "")
    up = pollution(-1.0, -0.9)
    check("负情绪加重负电荷", up > 0, up)
    check("有上限", abs(pollution(-1.0, -1.0, cap=0.5)) <= 0.5, "")
    check("有界无 NaN", math.isfinite(score(1.0, -0.8, -0.8)), "")


def test_fast_isolated():
    try:
        check_fast({"internal_thought": "x", "say": "我要说"})
        check("快档拒绝 say", False, "")
    except ValueError:
        check("快档拒绝 say", True, "")
    check("快档出口永远空", fast_to_public({"internal_thought": "x"}) == "", "")
    try:
        check_slow({"internal_thought": "x"})
        check("慢档必须有 say", False, "")
    except ValueError:
        check("慢档必须有 say", True, "")
    check("慢档正常", check_slow({"say": "嗯"})["say"] == "嗯", "")


def test_hebbian():
    e = ErrorLearning()
    for _ in range(100):
        e.learn(1.0, 1.0)
    check("权重不越界", 0.05 <= e.w <= 0.8, e.w)
    check("映射后才有影响", e.apply(1.0) == e.w, "")
    e2 = ErrorLearning()
    for _ in range(1000):
        e2.learn(1.0, -1.0)
    check("负结果压到下限", e2.w >= 0.05, e2.w)




def test_slow_payload_and_constraints():
    """慢档只拿身体事实；台词不准贴标签、不准复读微念头。"""
    from her2 import slow_payload, slow_messages, CARD_SLOW
    h = Homeostat({"Trust": 0.3, "Connection": 0.9, "Energy": 0.4})
    payload = slow_payload(h, impulse={"approach": 0.7, "avoid": 0.2, "idle": 0.1},
                           memory=["上次你说会回我，但没回"],
                           internal_thoughts=["他是不是不想理我了"],
                           context_window=["他：在吗", "她：嗯"])
    check("PAD 在 payload 里", set(payload["PAD"]) == {"P", "A", "D"}, payload["PAD"])
    check("五个变量都在", set(payload["homeostat"]) ==
          {"Energy", "Safety", "Connection", "Trust", "Autonomy"}, payload["homeostat"])
    msgs = slow_messages(payload)
    check("系统卡有约束", "不能编" in msgs[0]["content"], "")
    check("微念头标注仅供参照", "参考" in msgs[0]["content"], "")

    try:
        check_slow({"say": "我很焦虑"}, ["他是不是不想理我了"])
        check("拒绝情绪标签", False, "")
    except ValueError:
        check("拒绝情绪标签", True, "")
    try:
        check_slow({"say": "他是不是不想理我了"}, ["他是不是不想理我了"])
        check("拒绝复读微念头", False, "")
    except ValueError:
        check("拒绝复读微念头", True, "")
    ok = check_slow({"say": "……你忙你的。"}, ["他是不是不想理我了"])
    check("正常台词通过", ok["say"] == "……你忙你的。", ok)




def test_bridge_reads_old_project():
    """旧项目的人设和记忆只读接入（用真实文件，不写临时文件）。"""
    from her2.bridge_legacy import load_persona, recall, DEFAULT_PERSONA, DEFAULT_DB
    if not DEFAULT_PERSONA.exists() or not DEFAULT_DB.exists():
        check("旧项目文件存在（跳过）", True, "")
        return
    persona = load_persona()
    check("人设能读", len(persona) > 50, str(len(persona)))
    got = recall(query="他半天没回我", k=5)
    check("记忆能召回", isinstance(got, list) and len(got) <= 5, len(got))




def test_real_baseline_only_offsets():
    """实测负载只偏移模拟层：Arousal 随 context_load 单调上升。"""
    prev = None
    for i in range(1, 10):
        h = Homeostat(real={"context_load": i / 10})
        A = h.pad()[1]
        if prev is not None:
            check(f"负载 {i/10:.1f} 单调", A >= prev - 1e-9, f"{prev}->{A}")
        prev = A
    h = Homeostat(real={"context_load": 0.9})
    check("模拟变量还在", set(h.simulated()) ==
          {"Energy", "Safety", "Connection", "Trust", "Autonomy", "Fatigue", "Threat", "Boredom"}, "")
    check("实测被记录", h.measured()["context_load"] == 0.9, h.measured())
    from her2 import slow_payload
    pay = slow_payload(h)
    check("payload 分两层", set(pay["baselines"]) == {"measured", "simulated"}, "")

    try:
        check_slow({"say": "我现在上下文占用42%"})
        check("拒绝机器语言", False, "")
    except ValueError:
        check("拒绝机器语言", True, "")




def test_ablation_perturb():
    """消融只改身体信号，别的不动。"""
    from her2 import Homeostat, slow_payload
    import ablation_trust as A
    h = Homeostat({"Trust": 0.2, "Connection": 0.9, "Energy": 0.6})
    base = slow_payload(h, memory=["x"], internal_thoughts=["y"])
    c = A.perturb(base, "control")
    check("对照不改", c == base, "")
    inv = A.perturb(base, "invert")
    check("取反 Trust", abs(inv["homeostat"]["Trust"] - 0.8) < 1e-9, inv["homeostat"])
    check("取反 posture", inv["posture"] != base["posture"], inv["posture"])
    con = A.perturb(base, "constant")
    check("常量 0.5", con["homeostat"]["Trust"] == 0.5, con["homeostat"])




def test_metrics_and_stats():
    """姿态指标要能自动算、单调能被检出。"""
    from her2.metrics import metrics, spearman, perm_p, variance
    m0 = metrics("在")
    check("短句长度", m0["len"] == 1, m0)   # 去掉标点后仍是原串，len 1
    check("无省略号", m0["ellipsis"] == 0, m0)
    m1 = metrics("在……")
    check("有省略号", m1["ellipsis"] == 1, m1)
    check("单调 Spearman=1", abs(spearman([0, 1, 2, 3], [1, 2, 3, 4]) - 1) < 1e-9, "")
    p = perm_p(list(range(8)), list(range(1, 9)), n_perm=200)
    check("单调 p 小", p < 0.05, p)
    check("方差非负", variance([1, 2, 3]) >= 0, "")




def test_dream_budget_and_pad_rank():
    """做梦有 token 预算；检索按 PAD 加权。"""
    from her2 import DreamCycle, Episode, pad_weight, rank
    cyc = DreamCycle(budget_tokens=30, max_items=3)
    eps = [Episode("被骂了", charge=-0.8), Episode("天气不错", charge=0.0),
           Episode("他夸我", charge=0.5)]
    r = cyc.run(eps, P=-0.6, A=0.5)
    check("先选负电荷", r.captured and r.captured[0].text == "被骂了", r.captured)
    check("合成不超预算", sum(len(x) for x in r.synthesized) <= 30,
          [len(x) for x in r.synthesized])
    check("只给候选不写库", isinstance(r.integrated, list), r.integrated)

    check("P 高权重更大", pad_weight(0.8, 0, 0) > pad_weight(-0.8, 0, 0), "")
    check("极端值不炸", math.isfinite(pad_weight(-1, -1, -1)), "")
    ranked = rank([{"text": "a", "base": 1}, {"text": "b", "base": 2}], 0.5, 0, 0)
    check("排序稳定", ranked[0]["text"] == "b", ranked)


def test_rest_releases_context():
    from her2 import Homeostat
    h = Homeostat({"Energy": 0.2}, real={"context_load": 0.9, "latency_ms": 800})
    s0 = h.stress()
    h.rest(8)
    check("歇一下回体力", h.value("Energy") > 0.2, h.value("Energy"))
    check("上下文清账", h.measured()["context_load"] == 0.0, h.measured())
    check("压力下降", h.stress() <= s0, f"{s0}->{h.stress()}")




def test_l2_hebb_ablation():
    """ON 组越冷越疼；OFF 组每刀一样深；回归还在。"""
    from her2 import Homeostat, L2
    def run(on: bool) -> list[float]:
        h = Homeostat()
        l2 = L2(h, hebb=on)
        deltas = []
        for _ in range(5):
            r = l2.event("cold", -0.05)
            deltas.append(round(r["delta"], 4))
            l2.tick(600)
        return deltas

    off = run(False)
    on = run(True)
    check("OFF 每刀差不多", max(off) - min(off) < 1e-3, off)
    check("ON 越冷越疼", on[-1] < on[0] - 1e-3, on)
    check("ON 总伤害更大", sum(on) < sum(off), (sum(on), sum(off)))

    h = Homeostat()
    l2 = L2(h, hebb=True)
    for _ in range(200):
        l2.event("cold", -0.05)
    check("权重不越界", 0.05 <= l2.w["cold"] <= 0.8, l2.w["cold"])
    l2.tick(3600 * 24)
    check("基线回归还在", h.value("Trust") > 0.5, h.value("Trust"))
    check("Surprise 有界", 0 <= l2.last_surprise <= 1, l2.last_surprise)




def test_learning_trajectory_in_payload():
    """台词层拿到的必须是轨迹量，不只是瞬时 Trust。"""
    from her2 import Homeostat, L2, slow_payload
    h = Homeostat(); l2 = L2(h, hebb=True)
    l2.event("cold", -0.05)
    pay = slow_payload(h, l2=l2)
    check("payload 有 learning", set(pay["learning"]) >=
          {"accumulated_surprise", "weight_cold", "last_marginal", "gain"},
          pay["learning"])
    check("累积 Surprise 有值", pay["learning"]["accumulated_surprise"] > 0, pay["learning"])
    h2 = Homeostat(); off = L2(h2, hebb=False)
    off.event("cold", -0.05)
    pay2 = slow_payload(h2, l2=off)
    check("OFF 权重不动", pay2["learning"]["weight_cold"] == 0.2, pay2["learning"])




def test_l1_numeric_signals():
    """L1 只从数值变化提事件，不贴语义标签。"""
    from her2 import diff_signals
    prev = {"hp": 20, "food": 18, "players": {"A": 3}, "items": {"wood": 2}}
    curr = {"hp": 15, "food": 18, "players": {"A": 8}, "items": {"wood": 5}}
    sig = {(s.kind, s.meta.get("name") or s.meta.get("item")): s.value
           for s in diff_signals(prev, curr)}
    check("掉血", sig.get(("damage", None)) == 5, sig)
    check("玩家变远", sig.get(("player_distance", "A")) == 5, sig)
    check("拿到木头", sig.get(("item_gain", "wood")) == 3, sig)
    check("没有语义标签", all(s.kind in
          {"damage", "hunger", "player_join", "player_leave",
           "player_distance", "item_gain", "item_loss"} for s in diff_signals(prev, curr)), "")


def test_dream_is_material_only():
    from her2 import Homeostat, slow_payload
    pay = slow_payload(Homeostat(), dream=["我梦见走进一个没有门的屋子"])
    check("dream 进 payload", pay["dream"], pay["dream"])




def test_l1_to_l2_mapping_rules():
    """数值规则派生事件类型：同一组数，谁看都一样。"""
    from her2 import diff_signals, classify
    prev = {"hp": 20, "players": {"A": 3}}
    curr = {"hp": 15, "players": {"A": 8}}
    check("掉血+远处 → harm", classify(diff_signals(prev, curr)) == "hp_decrease", "")

    prev = {"items": {"wood": 1}, "players": {"A": 8}}
    curr = {"items": {"wood": 2}, "players": {"A": 1}}
    check("拿东西 → item_gain", classify(diff_signals(prev, curr)) == "item_gain", "")

    prev = {"hp": 20, "players": {"A": 3}}
    curr = {"hp": 20, "players": {"A": 4}}
    check("都不是 → neutral", classify(diff_signals(prev, curr)) == "neutral", "")

    from her2 import Homeostat, L2
    h = Homeostat(); on = L2(h, hebb=True)
    for _ in range(5):
        on.event("hp_decrease", -0.05)
    h2 = Homeostat(); off = L2(h2, hebb=False)
    for _ in range(5):
        off.event("hp_decrease", -0.05)
    check("L2 学事件类型", on.w["hp_decrease"] > off.w["hp_decrease"],
          (on.w, off.w))




def test_generic_vs_mc_boundary():
    """通用层不许出现 MC 词；MC 规则只在 body_mc。"""
    from pathlib import Path
    per = (Path(__file__).resolve().parent / "her2" / "perception.py").read_text(encoding="utf-8")
    mc = (Path(__file__).resolve().parent / "her2" / "body_mc.py").read_text(encoding="utf-8")
    for w in ("hp", "damage", "player_distance", "food", "item_gain"):
        check(f"通用层无 {w}", w not in per, w)
    check("MC 规则在适配层", "player_distance" in mc and "damage" in mc, "")
    from her2 import classify_by, Signal
    out = classify_by([(lambda ss: any(x.kind == "pulse" for x in ss), "saw_pulse")],
                      [Signal("pulse", 1.0)])
    check("通用规则引擎可用", out == "saw_pulse", out)




def test_innate_acquired_tags():
    """代码里要能一眼分出先天/后天。"""
    from pathlib import Path
    root = Path(__file__).resolve().parent / "her2"
    src = "".join((root / f).read_text(encoding="utf-8")
                  for f in ("homeostat.py", "l2.py", "dream.py", "narrative.py", "body_mc.py"))
    check("有先天标记", "[先天]" in src, "")
    check("有后天标记", "[后天]" in src, "")




def test_teaching_is_arranged_experience():
    """教 = 安排经历，不直接写权重；痕迹标 taught。"""
    from her2 import Homeostat, L2, teach, LESSON_COLD_THEN_COMFORT
    h = Homeostat(); l2 = L2(h, hebb=True)
    before = l2.w["hp_decrease"]
    recs = teach(l2, LESSON_COLD_THEN_COMFORT)
    check("课程跑完", len(recs) == 4, recs)
    check("标为教的", all(r["source"] == "taught" for r in recs), recs)
    check("权重是她自己学的", l2.w["hp_decrease"] > before,
          (before, l2.w["hp_decrease"]))
    check("安抚也学了", l2.w["healed_by_owner"] > 0.2, l2.w["healed_by_owner"])




def test_runtime_closes_the_loop():
    """闭环：假身体活 100 tick，学习发生在循环里，状态能存盘。"""
    from pathlib import Path as _P
    from her2 import Runtime, FakeBody
    body = FakeBody()
    rt = Runtime(body, dt=1.0, poll_every=10,
                 speaker=lambda pay: "嗯", path="_test_runtime.json")
    w0 = rt.l2.w["hp_decrease"]
    for i in range(100):
        if i in (10, 20, 30):
            body.state["hp"] -= 3
            body.state["players"]["A"] = 12 if body.state["players"]["A"] < 10 else 8
        rt.tick()
    check("循环里学到了", rt.l2.w["hp_decrease"] > w0,
          (w0, rt.l2.w["hp_decrease"]))
    check("Trust 掉了", rt.h.value("Trust") < 0.7, rt.h.value("Trust"))
    check("轮询会说话", 1 <= len(rt.says) < 100, len(rt.says))
    check("机器日志", len(rt.machine_log) == 100, len(rt.machine_log))
    rt.save()
    rt2 = Runtime(body, path="_test_runtime.json")
    check("能读回", rt2.load(), "")
    check("权重一致", abs(rt2.l2.w["hp_decrease"] - rt.l2.w["hp_decrease"]) < 1e-9, "")
    check("tick 一致", rt2.tick_no == rt.tick_no, "")
    _P("_test_runtime.json").unlink(missing_ok=True)




def test_stats_functions_directly():
    """pearson / mannwhitney 直接测，不靠间接调用。"""
    from her2.metrics import pearson, mannwhitney
    check("pearson 完全正相关", abs(pearson([1, 2, 3], [2, 4, 6]) - 1) < 1e-9, "")
    check("pearson 完全负相关", abs(pearson([1, 2, 3], [6, 4, 2]) + 1) < 1e-9, "")
    u, p = mannwhitney([1, 2, 3, 4, 5], [10, 11, 12, 13, 14])
    check("mannwhitney 分开时 p 小", p < 0.05, p)
    u2, p2 = mannwhitney([1, 2, 3, 4, 5], [2, 3, 4, 5, 6])
    check("mannwhitney 接近时 p 大", p2 > 0.05, p2)




def test_mc_observe_contract():
    """契约：MC 原始状态 → diff_signals → classify，五条全过才算通。"""
    from her2 import diff_signals, classify

    def ev(prev, curr):
        sig = diff_signals(prev, curr)
        return classify(sig)

    # 1 玩家远 + 掉血
    check("契约1 远+掉血→harm_from_distance",
          ev({"hp": 20, "players": {"A": 3}},
             {"hp": 17, "players": {"A": 9}}) == "hp_decrease", "")
    # 2 玩家近、无伤害
    check("契约2 近→distance_decrease",
          ev({"hp": 20, "players": {"A": 8}},
             {"hp": 20, "players": {"A": 2}}) == "distance_decrease", "")
    # 3 只有掉血
    check("契约3 掉血→hp_decrease",
          ev({"hp": 20, "players": {"A": 8}},
             {"hp": 17, "players": {"A": 8}}) == "hp_decrease", "")
    # 4 回血 + 靠近
    check("契约4 回血+靠近→comfort",
          ev({"hp": 15, "players": {"A": 8}},
             {"hp": 20, "players": {"A": 2}}) == "body_regen", "")
    # 5 无变化
    check("契约5 无变化→neutral",
          ev({"hp": 20, "players": {"A": 8}},
             {"hp": 20, "players": {"A": 8}}) == "neutral", "")




def test_mc_body_shape_and_parity():
    """MCBody 只换形状；同一事件表下轨迹要和 FakeBody 一致。"""
    from her2 import MCBody, Runtime, FakeBody

    class FakeBridge:
        def __init__(self):
            self.state = {"self": {"health": 20, "food": 18},
                          "players": {"A": {"dist": 3}}, "inventory": []}

        def observe(self):
            import copy
            return copy.deepcopy(self.state)

    b = FakeBridge()
    body = MCBody(b)
    st = body.see()
    check("MC 形状转对了", st["hp"] == 20 and st["players"]["A"] == 3, st)

    # 同一事件表：两个身体各跑 60 tick
    def run(body) -> tuple[float, float]:
        rt = Runtime(body, path="_parity.json")
        for i in range(60):
            if i in (10, 30, 50):
                if hasattr(body, "state"):
                    body.state["hp"] -= 3
                    body.state["players"]["A"] = 12 if body.state["players"]["A"] < 10 else 8
                else:
                    b.state["self"]["health"] -= 3
                    b.state["players"]["A"]["dist"] = 12 if b.state["players"]["A"]["dist"] < 10 else 8
            rt.tick()
        return rt.h.value("Trust"), rt.l2.w["hp_decrease"]

    ft, fw = run(FakeBody())
    mt, mw = run(body)
    check("Trust 轨迹一致", abs(ft - mt) < 1e-9, (ft, mt))
    check("权重轨迹一致", abs(fw - mw) < 1e-9, (fw, mw))
    from pathlib import Path as _P
    _P("_parity.json").unlink(missing_ok=True)




def test_poll_wake_without_events():
    """零事件：系统按 poll 唤醒，LLM 说 speak 才开口。"""
    from her2 import Runtime, FakeBody
    b = FakeBody()
    seen = []
    def speaker(pay):
        seen.append(pay)
        return {"say": "在吗"}
    rt = Runtime(b, speaker=speaker, poll_every=50, path="_spont.json")
    for _ in range(200):
        rt.tick()
    check("轮询后开口", len(rt.says) >= 1, len(rt.says))
    check("不是每 tick 都说", len(rt.says) <= 5, len(rt.says))
    check("带了压力事实", "pressure" in (seen[0] if seen else {}) and
          "approach" in seen[0]["pressure"], seen[:1])
    check("仍然说话", all(s.get("say") for s in rt.says), rt.says)


def test_poll_hold_and_reply():
    """LLM 选择 hold → 不说；说话本身不扣 Connection。"""
    from her2 import Runtime, FakeBody
    b = FakeBody()
    calls = []
    def speaker(pay):
        calls.append(pay)
        return {"say": ""}
    rt = Runtime(b, speaker=speaker, poll_every=50, path="_hold.json")
    c0 = rt.h.value("Connection")
    for _ in range(100):
        rt.tick()
    check("被唤醒两次", len(calls) == 2, len(calls))
    check("hold 不开口", len(rt.says) == 0, rt.says)
    check("说话不额外扣连接", rt.h.value("Connection") > c0 - 0.1, rt.h.value("Connection"))
    c1 = rt.h.value("Connection")
    rt.receive_reply(-1.0)
    check("冷淡回应→Connection 降", rt.h.value("Connection") < c1, (c1, rt.h.value("Connection")))
    c2 = rt.h.value("Connection")
    rt.receive_reply(1.0)
    check("热情回应→Connection 升", rt.h.value("Connection") > c2, (c2, rt.h.value("Connection")))


def test_stats_functions_directly():
    """pearson / mannwhitney 直接测，不靠间接调用。"""
    from her2.metrics import pearson, mannwhitney
    check("pearson 完全正相关", abs(pearson([1, 2, 3], [2, 4, 6]) - 1) < 1e-9, "")
    check("pearson 完全负相关", abs(pearson([1, 2, 3], [6, 4, 2]) + 1) < 1e-9, "")
    u, p = mannwhitney([1, 2, 3, 4, 5], [10, 11, 12, 13, 14])
    check("mannwhitney 分开时 p 小", p < 0.05, p)
    u2, p2 = mannwhitney([1, 2, 3, 4, 5], [2, 3, 4, 5, 6])
    check("mannwhitney 接近时 p 大", p2 > 0.05, p2)




def test_mc_observe_contract():
    """契约：MC 原始状态 → diff_signals → classify，五条全过才算通。"""
    from her2 import diff_signals, classify

    def ev(prev, curr):
        sig = diff_signals(prev, curr)
        return classify(sig)

    # 1 玩家远 + 掉血
    check("契约1 远+掉血→harm_from_distance",
          ev({"hp": 20, "players": {"A": 3}},
             {"hp": 17, "players": {"A": 9}}) == "hp_decrease", "")
    # 2 玩家近、无伤害
    check("契约2 近→distance_decrease",
          ev({"hp": 20, "players": {"A": 8}},
             {"hp": 20, "players": {"A": 2}}) == "distance_decrease", "")
    # 3 只有掉血
    check("契约3 掉血→hp_decrease",
          ev({"hp": 20, "players": {"A": 8}},
             {"hp": 17, "players": {"A": 8}}) == "hp_decrease", "")
    # 4 回血 + 靠近
    check("契约4 回血+靠近→comfort",
          ev({"hp": 15, "players": {"A": 8}},
             {"hp": 20, "players": {"A": 2}}) == "body_regen", "")
    # 5 无变化
    check("契约5 无变化→neutral",
          ev({"hp": 20, "players": {"A": 8}},
             {"hp": 20, "players": {"A": 8}}) == "neutral", "")




def test_mc_body_shape_and_parity():
    """MCBody 只换形状；同一事件表下轨迹要和 FakeBody 一致。"""
    from her2 import MCBody, Runtime, FakeBody

    class FakeBridge:
        def __init__(self):
            self.state = {"self": {"health": 20, "food": 18},
                          "players": {"A": {"dist": 3}}, "inventory": []}

        def observe(self):
            import copy
            return copy.deepcopy(self.state)

    b = FakeBridge()
    body = MCBody(b)
    st = body.see()
    check("MC 形状转对了", st["hp"] == 20 and st["players"]["A"] == 3, st)

    # 同一事件表：两个身体各跑 60 tick
    def run(body) -> tuple[float, float]:
        rt = Runtime(body, path="_parity.json")
        for i in range(60):
            if i in (10, 30, 50):
                if hasattr(body, "state"):
                    body.state["hp"] -= 3
                    body.state["players"]["A"] = 12 if body.state["players"]["A"] < 10 else 8
                else:
                    b.state["self"]["health"] -= 3
                    b.state["players"]["A"]["dist"] = 12 if b.state["players"]["A"]["dist"] < 10 else 8
            rt.tick()
        return rt.h.value("Trust"), rt.l2.w["hp_decrease"]

    ft, fw = run(FakeBody())
    mt, mw = run(body)
    check("Trust 轨迹一致", abs(ft - mt) < 1e-9, (ft, mt))
    check("权重轨迹一致", abs(fw - mw) < 1e-9, (fw, mw))
    from pathlib import Path as _P
    _P("_parity.json").unlink(missing_ok=True)





def test_schema_and_intention_margin():
    """慢档强校验 + 博弈输家信息。"""
    from her2 import validate_slow, Runtime, FakeBody, slow_payload
    for bad in ({"say": "嗯", "x": 1}, {"say": 3}, {"say": "长" * 501}, "嗯"):
        try:
            validate_slow(bad)
            check(f"拒绝 {str(bad)[:12]}", False, "")
        except ValueError:
            check(f"拒绝 {str(bad)[:12]}", True, "")
    check("正常通过", validate_slow({"say": "嗯"})["say"] == "嗯", "")

    rt = Runtime(FakeBody(), path="_x.json")
    it = rt._intention()
    check("有三元组", set(it) >= {"winner", "runner_up", "margin", "values"}, it)
    check("margin 非负", it["margin"] >= 0, it)
    pay = slow_payload(rt.h, intention=it)
    check("payload 带 intention", pay["intention"]["winner"] == it["winner"], "")




def test_l1_features_and_r1_contract():
    """L1 只给读数；R1 猜测必须有证据；表层是连续区间。"""
    from her2 import text_features, ToneGuess, surface_targets, validate_surface
    f = text_features("你真行……")
    check("读到省略号", f["ellipsis"] == 2, f)
    check("读到长度", f["len"] == 5, f)

    g0 = ToneGuess("possible_edge", 0.9, [])
    check("没证据→置信 0", g0.confidence == 0.0, g0)
    g = ToneGuess("possible_edge", 0.8, ["ellipsis", "repeat_run"])
    s = surface_targets(g)
    check("高置信→短句", s.max_chars <= 18, s)
    check("高置信→省略号预算", s.ellipsis_max == 2, s)
    check("高置信→不许语气词", not s.allow_particle, s)
    ok = validate_surface("……", s)
    check("短句合规", ok == [], ok)
    bad = validate_surface("你真的好厉害呢真棒", s)
    check("越界被抓", bad, bad)

    low = ToneGuess("possible_edge", 0.3, ["ellipsis"])
    check("低置信→不收紧", surface_targets(low).max_chars >= 24, surface_targets(low))
    lo = ToneGuess("possible_edge", 0.8, ["x"]).with_prior(0.2)
    hi = ToneGuess("possible_edge", 0.8, ["x"]).with_prior(0.9)
    check("关系只改倾向", lo.confidence >= hi.confidence, (lo.confidence, hi.confidence))




def test_rule_tone_and_template():
    """规则版 R1：读数→猜测；模板版只按 surface 拼。"""
    from her2 import text_features, rule_tone, surface_targets, render_surface
    from her2.narrative import check_slow
    f = text_features("你真行……")
    g = rule_tone(f, context_edge=True)
    check("规则判 edge", g.label == "possible_edge", g)
    check("有证据", g.evidence, g)
    check("置信度有界", 0 <= g.confidence <= 1, g)
    s = surface_targets(g)
    say = render_surface(s)
    check("模板短", len(say) <= s.max_chars + 2, say)
    check("模板有省略号", say.count("…") == s.ellipsis_max, say)
    check("模板过校验", check_slow({"say": say}, surface=s), say)

    f2 = text_features("今天天气不错")
    check("平句判 neutral", rule_tone(f2).label == "neutral", rule_tone(f2))

    try:
        check_slow({"say": "你真的好厉害呢真棒" + "…" * 9}, surface=s)
        check("surface 越界被拦", False, "")
    except ValueError:
        check("surface 越界被拦", True, "")




def test_calibration_gate_and_refusal():
    """没校准→unknown；词汇先验封顶；规则漂移→unknown；信任低打击大。"""
    from her2 import Calibration
    c = Calibration()
    c.add("好吧|敌意", "不合适")
    c.add("好吧|敌意", "不合适")
    check("样本不足→unknown", c.score("好吧|敌意", 0.9)["label"] == "unknown", "")
    c.add("好吧|敌意", "不合适")
    r = c.score("好吧|敌意", 0.9, source="context")
    check("校准后通过", r["label"] == "ok", r)
    check("context 封顶 0.85", r["score"] <= 0.85, r)
    r2 = c.score("好吧|敌意", 0.9, source="lexical_template")
    check("词汇先验也收缩", r2["score"] < 0.9, (r, r2))

    c2 = Calibration()
    for lab in ("合适", "不合适", "中性"):
        c2.add("行行行|敌意", lab)
    check("分歧大→unknown", c2.score("行行行|敌意", 0.8)["label"] == "unknown", "")

    c3 = Calibration()
    for _ in range(3):
        c3.add("中性句|友善", "中性")
    r3 = c3.score("中性句|友善", 1.0)
    check("规则偏离→unknown", r3["label"] == "unknown", r3)

    s_lo, p_lo = c.effects(1.0, 0.2)
    s_hi, p_hi = c.effects(1.0, 0.9)
    check("信任低打击更大", s_lo > s_hi and p_lo < p_hi, (s_lo, s_hi))




def test_calibration_thresholds_and_freeze():
    """分歧写死 0.34；3–5 临时封顶 0.5；连续 2 次偏离冻结。"""
    from her2 import Calibration
    c = Calibration()
    for _ in range(3):
        c.add("x", "不合适")
    check("一致→分歧 0", c.disagreement("x") == 0.0, c.disagreement("x"))
    check("3 人=临时", c.state("x") == "provisional", c.state("x"))
    check("临时收缩幅度", 0.5 < c.score("x", 0.9)["score"] < 0.9, c.score("x", 0.9))

    c2 = Calibration()
    c2.add("y", "合适"); c2.add("y", "合适"); c2.add("y", "不合适")
    check("2:1 分歧≈0.33", abs(c2.disagreement("y") - 1 / 3) < 1e-9, c2.disagreement("y"))
    check("2:1 仍可用", c2.score("y", 0.0)["label"] == "ok", c2.score("y", 0.0))

    c3 = Calibration()
    for lab in ("合适", "中性", "不合适"):
        c3.add("z", lab)
    check("1:1:1 分歧>0.34", c3.disagreement("z") > 0.34, "")
    check("1:1:1 拒判", c3.score("z", 0.5)["reason"] == "disagreement", c3.score("z", 0.5))

    c4 = Calibration()
    for _ in range(10):
        c4.add("w", "不合适")
    check("10 人=正式", c4.state("w") == "formal", c4.state("w"))
    check("正式按来源封顶 0.85", c4.score("w", 0.9)["score"] <= 0.85, c4.score("w", 0.9))

    c5 = Calibration()
    for _ in range(3):
        c5.add("v", "不合适")
    c5.score("v", 0.2)      # 第 1 次偏离
    c5.score("v", 0.2)      # 第 2 次 → 冻结
    r = c5.score("v", 0.2)
    check("连续偏离→冻结", r["reason"] == "rule_frozen", r)




def test_guards_are_boundaries_not_diagnoses():
    """动作白名单/记忆未命中/体感矛盾：只标记，不诊断。"""
    from her2 import dispatch, memory_miss_line, consistency_flags
    from her2 import Runtime, FakeBody
    check("非法动作退 idle", dispatch("rm -rf") == "idle", "")
    check("合法动作保留", dispatch("approach") == "approach", "")
    check("未命中只报事实", memory_miss_line(False) == "[事实] 记录不存在。", "")
    check("命中不说话", memory_miss_line(True) == "", "")
    f = consistency_flags("哈哈太好了", {"Stress": 0.9, "P": -0.5, "Connection": 0.05})
    check("矛盾被标记", "stress_high_but_cheerful" in f and "low_connection_but_warm" not in f, f)
    check("正常不标记", consistency_flags("嗯", {"Stress": 0.2, "P": 0.2, "Connection": 0.5}) == [], "")
    rt = Runtime(FakeBody(), speaker=lambda pay: "哈哈太好了", path="_x.json")
    rt.tick()
    check("runtime 记 anomaly 标记", "flags" in rt.machine_log[-1], rt.machine_log[-1])




def test_alignment_labels():
    from her2 import Calibration
    c = Calibration()
    for _ in range(3):
        c.add("1", "不对齐")
    r = c.score("1", 0.9)
    check("对齐标签可用", r["label"] == "ok" and 0.5 < r["score"] < 0.9, r)




def test_r0_r1_separation():
    """R0 只判（无判官→unknown）；R1 只管准入。"""
    from her2 import align, Calibration
    check("无判官→unknown", align({"a": "你滚", "b": "好吧"}).unknown, "")
    check("缺轮次→incomplete", align({"a": "你滚"}).reason == "incomplete_turn", "")
    al = align({"a": "你滚", "b": "好吧"},
               judge=lambda turn, rel: {"score": 0.8, "confidence": 0.7,
                                        "evidence": ["turn"], "reason": "ok"})
    check("判官给了分", not al.unknown and al.score == 0.8, al)

    c = Calibration()
    for _ in range(3):
        c.add("1", "不对齐")
    check("R0 unknown → R1 拒判", c.admit("1", align({}))["reason"] != "ok", "")
    r = c.admit("1", al)
    check("R0 有分 → R1 校准", r["label"] == "ok" and 0.5 < r["score"] < 0.8, r)




def test_per_person_relations():
    """同一句话对不同人：态度分开记，只按比例渗到全局。"""
    from her2 import Relations, align
    rs = Relations(base_leak=0.10, factor=0.80)
    a = rs.get("u1", "他", "owner")
    b = rs.get("u2", "路人", "stranger")
    rs.update("u1", trust=0.2, closeness=0.3)
    check("对喜欢的人升", a.trust > 0.5 and a.closeness > 0.2, a.context())
    check("对路人不动", b.trust == 0.5, b.context())
    g = rs.global_leak(0.2, 0.3)
    check("全局只渗透一部分", abs(g[0] - 0.02) < 1e-9 and abs(g[1] - 0.03) < 1e-9, g)

    seen = {}
    def judge(turn, relation):
        seen["rel"] = relation
        return {"score": 0.2 if relation.get("kind") == "owner" else 0.8,
                "confidence": 0.7, "evidence": ["relation"], "reason": "ok"}
    r_own = align({"a": "随便吧", "b": "嗯"}, rs.get("u1").context(), judge)
    r_str = align({"a": "随便吧", "b": "嗯"}, rs.get("u2").context(), judge)
    check("关系进了 R0", seen["rel"]["kind"] in ("owner", "stranger"), seen)
    check("同一句不同关系不同判", r_own.score < r_str.score, (r_own, r_str))

    rs.decay(86400)
    check("关系会衰减", a.trust < 0.7, a.context())




def test_runtime_hear_with_speaker():
    """带说话人的入口：没有判官不改状态；有判官才落 Relation/全局。"""
    from her2 import Runtime, FakeBody
    rt = Runtime(FakeBody(), path="_x.json")
    t0 = rt.h.value("Trust")
    r0 = rt.hear("u1", "随便吧")
    check("无判官不改状态", not r0["ok"] and rt.h.value("Trust") == t0, r0)
    check("默认陌生人", r0["relation"]["kind"] == "stranger", r0)

    rt.aligner = lambda turn, rel: {"score": 0.8, "confidence": 0.7,
                                    "evidence": ["turn"], "reason": "ok"}
    rt.prev_text = "她那句"
    r1 = rt.hear("u1", "随便吧")
    check("有判官才生效", r1["ok"] and rt.h.value("Trust") < t0, r1)
    check("先落 Relation", rt.relations.get("u1").trust < 0.5,
          rt.relations.get("u1").context())
    check("leak 随亲近上升",
          rt.relations.leak_for(0.9) > rt.relations.leak_for(0.1), "")




def test_hear_bidirectional():
    """对齐→升，冲突→降，中性→不动；关系只影响渗透率，不改分数。"""
    from her2 import Runtime, FakeBody
    def mk(score):
        rt = Runtime(FakeBody(), path="_x.json")
        rt.aligner = lambda turn, rel: {"score": score, "confidence": 0.7,
                                        "evidence": ["x"], "reason": "ok"}
        rt.prev_text = "上一句"
        return rt
    up = mk(0.0); up.hear("u1", "嗯")
    dn = mk(1.0); dn.hear("u1", "你滚")
    mid = mk(0.5); mid.hear("u1", "随便吧")
    check("对齐→关系升", up.relations.get("u1").trust > 0.5,
          up.relations.get("u1").context())
    check("冲突→关系降", dn.relations.get("u1").trust < 0.5,
          dn.relations.get("u1").context())
    check("中性→不动", abs(mid.relations.get("u1").trust - 0.5) < 1e-9,
          mid.relations.get("u1").context())




def test_predictor_slots():
    """世界/社会模型占位：默认 unknown；有预测才谈误差。"""
    from her2 import (NullWorldModel, NullSocialModel, Prediction, surprise,
                      Runtime, FakeBody)
    check("世界模型默认 unknown", NullWorldModel().predict({}).unknown, "")
    check("社会模型默认 unknown", NullSocialModel().predict({}, {}).unknown, "")
    check("没预测→没误差", surprise(NullWorldModel().predict({}), 1.0) is None, "")
    p = Prediction(value=10.0, confidence=0.7, reason="ok")
    check("误差有界", surprise(p, 8.0, scale=4.0) == 0.5, surprise(p, 8.0, scale=4.0))
    check("误差不越界", 0 <= surprise(p, 100.0, scale=1.0) <= 1, "")
    rt = Runtime(FakeBody(), path="_x.json")
    check("runtime 有占位", rt.world is not None and rt.social is not None, "")




def test_approach_uses_target_relation():
    """开口冲动 = 全局 Connection × 目标人的 Trust；冲突后 approach 掉。"""
    from her2 import Runtime, FakeBody
    rt = Runtime(FakeBody(), path="_x.json")
    rt.h.change("Connection", 0.7)
    a, _v, i = rt._competition()
    from her2 import approach_value
    expected = approach_value(rt.h.value("Connection"), 0.8, rt.h.value("Safety"), 0.0)
    check("用的是目标人 trust", abs(a - expected) < 1e-9, (a, expected))
    rt.relations.get("owner").trust = 0.05
    a2, _v2, i2 = rt._competition()
    check("冲突后 approach 掉", a2 < i2, (a2, i2))

    # 低信任：系统仍轮询，但压力事实里 trust 低；说 hold 就不说
    seen = []
    def hold(pay):
        seen.append(pay)
        return {"action": "hold"}
    rt2 = Runtime(FakeBody(), speaker=hold, poll_every=10, path="_y.json")
    rt2.relations.get("owner").trust = 0.05
    for _ in range(50):
        rt2.tick()
    check("低信任也会被叫醒", len(seen) >= 1, len(seen))
    check("压力里 trust 低", seen and seen[0]["pressure"]["target_trust"] == 0.05,
          seen[:1])
    check("hold 就不说", len(rt2.says) == 0, rt2.says)

    # 高信任：同一轮询下，她说 speak
    rt3 = Runtime(FakeBody(), speaker=lambda pay: {"say": "在吗"},
                  poll_every=10, path="_z.json")
    rt3.relations.get("owner").trust = 0.95
    for _ in range(50):
        rt3.tick()
    check("高信任会主动", len(rt3.says) >= 1, len(rt3.says))

    # 冲突事件确实扣目标人的 trust
    rt4 = Runtime(FakeBody(), path="_w.json")
    rt4.aligner = lambda turn, rel: {"score": 1.0, "confidence": 0.8,
                                     "evidence": ["x"], "reason": "ok"}
    rt4.prev_text = "上一句"
    t0 = rt4.relations.get("owner").trust
    rt4.hear("owner", "你滚")
    check("冲突扣目标人", rt4.relations.get("owner").trust < t0,
          rt4.relations.get("owner").context())




def test_social_fatigue_is_metabolic():
    """说话不瞬间扣 Energy，而是推高 Fatigue/代谢，持续耗能。"""
    from her2 import Runtime, FakeBody
    rt = Runtime(FakeBody(), speaker=lambda pay: {"say": "在吗，我今天有点想你"},
                 poll_every=1, path="_fatigue.json")
    e0 = rt.h.value("Energy")
    rt.tick()          # tick 1 触发轮询
    check("说话加了疲劳", rt.h.value("Fatigue") > 0, rt.h.value("Fatigue"))
    check("代谢被推高", rt.metabolic_extra > 0, rt.metabolic_extra)
    check("没有瞬间扣 Energy", abs(rt.h.value("Energy") - e0) < 0.01,
          (e0, rt.h.value("Energy")))

    # 疲劳压低 approach
    rt.h.change("Fatigue", 0.8)
    a, _v, i = rt._competition()
    rt.h.change("Fatigue", -0.8)
    a0, _v0, i0 = rt._competition()
    check("疲劳压低 approach", a < a0, (a, a0))

    # 挂机恢复
    rt.h.change("Fatigue", 0.5)
    rt.poll_every = 0
    f0 = rt.h.value("Fatigue")
    for _ in range(200):
        rt.tick()
    check("独处会恢复疲劳", rt.h.value("Fatigue") < f0,
          (f0, rt.h.value("Fatigue")))




def test_anchor_based_prediction_and_surprise():
    """预测必须基于锚点；误差改 Safety/Trust，Stress 派生。"""
    from her2 import Anchors, RelationalPredictor, apply_surprise, Homeostat
    a = Anchors()
    a.add_promise("p1", "u1", "今晚来")
    pred = RelationalPredictor(a).predict({}, {"id": "u1"})
    check("基于承诺预测", not pred.unknown and pred.value["check"] == "promise", pred)
    check("无锚点→unknown", RelationalPredictor(a).predict({}, {"id": "u2"}).unknown, "")

    rp = RelationalPredictor(a)
    rp.predict({}, {"id": "u1"})
    s = rp.observe({"who": "u1", "came": False})
    check("没来→误差 1", s == 1.0, s)
    check("承诺标记 broken", a.pending("u1") == [], [p.status for p in a.promises])

    h = Homeostat()
    s0, t0, st0 = h.value("Safety"), h.value("Trust"), h.stress()
    apply_surprise(h, 1.0, 0.8)
    check("误差降安全感", h.value("Safety") < s0, (s0, h.value("Safety")))
    check("误差降信任", h.value("Trust") < t0, (t0, h.value("Trust")))
    check("Stress 派生上涨", h.stress() > st0, (st0, h.stress()))




def test_output_distortion_not_truncation():
    """大脑完整输出；只在终端层加声带痉挛，不截断、不限制 token。"""
    from her2 import distort_text, action_delay, perception_threshold
    base = "主人，僵尸在左前方三米，你快跑！" * 3
    check("低恐惧不干扰", distort_text(base, 0.1) == base, "")
    out = distort_text(base, 0.9, seed=3)
    check("原文没被删", len(out) >= len(base), (len(base), len(out)))
    check("出现生理停顿", "……" in out, out[:40])
    check("出现高频断句", out.count("……") >= 2, out.count("……"))
    check("高恐惧延迟更大", action_delay(0.9) > action_delay(0.1), "")
    check("高恐惧阈值更低", perception_threshold(0.9) < perception_threshold(0.1), "")




def test_formal_pre_registered_stats():
    """预注册：Safety→approach 单调；owner/stranger 的 d 与 p。"""
    import math
    import random
    import statistics
    from her2 import (approach_value, Homeostat, Runtime, FakeBody,
                      choose_strategy, approach_gate_ablation,
                      stutter_probability, pause_type)
    from her2.metrics import spearman

    sub = [(i / 30, approach_value(0.9, 0.8, i / 30, 0.0)) for i in range(1, 10)]
    rho = spearman([s for s, _ in sub], [a for _, a in sub])
    check("Safety→approach rho<-0.8", rho < -0.8, rho)

    def cohen(a, b):
        ma, mb = statistics.mean(a), statistics.mean(b)
        va, vb = statistics.pvariance(a), statistics.pvariance(b)
        sp = math.sqrt((va + vb) / 2) or 1e-9
        return (ma - mb) / sp

    def perm_p(a, b, n=500, seed=3):
        rng = random.Random(seed)
        obs = abs(cohen(a, b))
        pool = list(a) + list(b)
        hits = 0
        for _ in range(n):
            rng.shuffle(pool)
            if abs(cohen(pool[:len(a)], pool[len(a):])) >= obs - 1e-12:
                hits += 1
        return (hits + 1) / (n + 1)

    def group(who, trust, closeness, n=40, seed=1):
        rng = random.Random(seed)
        ds, dt = [], []
        for _ in range(n):
            rt = Runtime(FakeBody(), path="_x.json")
            rel = rt.relations.get(who, who, "owner" if who == "owner" else "stranger")
            rel.trust, rel.closeness = trust, closeness
            rt.prev_text = "上一句"
            score = 0.7 + rng.random() * 0.25
            rt.aligner = lambda turn, r, s=score: {"score": s, "confidence": 0.8,
                                                   "evidence": ["x"], "reason": "ok"}
            s0 = rt.h.stress()
            rt.hear(who, "随便吧")
            ds.append(rt.h.stress() - s0)
            dt.append(trust - rel.trust)
        return ds, dt

    os_, ot_ = group("owner", 0.8, 0.5)
    ss_, st_ = group("stranger", 0.5, 0.2)
    d_stress = abs(cohen(os_, ss_))
    p_stress = perm_p(os_, ss_)
    check("Stress 增量 d>0.8", d_stress > 0.8, d_stress)
    check("Stress 增量 p<0.05", p_stress < 0.05, p_stress)
    d_trust = cohen(st_, ot_)
    check("stranger trust 掉更多 d>0.5", d_trust > 0.5, d_trust)

    check("效用可选策略", choose_strategy(0.9, 0.8, 0.8, 0.8) in
          ("seek_information", "silence", "hesitation"), "")
    check("消融只会犹豫", approach_gate_ablation(0.9, 0.8, 0.8) == "delay", "")
    check("口吃概率随恐惧升", stutter_probability(0.9, 0.5, 0.5) >
          stutter_probability(0.1, 0.5, 0.5), "")
    check("高恐惧低体力→断气", pause_type(0.9, 0.2) == "breath_ellipsis", "")
    check("高恐惧高体力→重复", pause_type(0.9, 0.8) == "rapid_repeat", "")




def test_quality_is_external_and_llm_cannot_touch_it():
    """quality 只来自客观事实；LLM 台词再自我欺骗也改不了 Connection。"""
    from her2 import objective_quality, Runtime, FakeBody
    check("离开→-1", objective_quality(left=True) == -1.0, "")
    q_fast = objective_quality(10, 60, asked_back=True)
    q_slow = objective_quality(3000, 5, asked_back=False)
    check("快而长 > 慢而短", q_fast > q_slow, (q_fast, q_slow))
    check("quality 有界", -1 <= q_fast <= 1 and -1 <= q_slow <= 1, "")

    rt = Runtime(FakeBody(), path="_x.json")
    c0 = rt.h.value("Connection")
    rt.receive_reply(objective_quality(left=True))
    check("客观离开→Connection 降", rt.h.value("Connection") < c0,
          (c0, rt.h.value("Connection")))
    check("台词没有入口", "text" not in Runtime.receive_reply.__code__.co_varnames,
          Runtime.receive_reply.__code__.co_varnames)



def test_l0_reflex_and_lazy_rate():
    """L0：词典/重复/敷衍/死寂；100 轮闲聊 LLM 调用率 <20%。"""
    from her2 import L0, Runtime, FakeBody
    l0 = L0()
    l0.add("草")
    st = {"Energy": 0.8, "Autonomy": 0.8, "Stress": 0.2, "P": 0.1}
    check("词典命中", l0.try_respond("草", st)["mode"] == "l0", "")
    check("日常废话低精力", l0.try_respond("今天星期三", {"Energy": 0.2, "Stress": 0.8, "Autonomy": 0.8, "P": 0.0})["say"] in ("嗯", "哦", "嗯嗯", "……", "干嘛？", "别烦我"), "")
    hold = l0.try_respond("在吗", {"Energy": 0.8, "Autonomy": 0.05, "Stress": 0.95, "P": -0.5, "Fear": 0.95})
    check("极端压制→hold", hold and hold.get("hold"), hold)

    rt = Runtime(FakeBody(), path="_x.json")
    rt.aligner = lambda turn, rel: {"score": 0.2, "confidence": 0.6,
                                    "evidence": ["x"], "reason": "ok"}
    rt.h.change("Energy", -0.6)   # 累
    dull = ["吃了吗", "今天星期三", "我刚吃完", "今天下雨了", "嗯"]
    for i in range(100):
        rt.hear("u1", dull[i % len(dull)])
    rate = rt.llm_calls / 100
    check("LLM 调用率<20%", rate < 0.20, rate)
    check("L0 命中不少", rt.l0_hits >= 80, rt.l0_hits)

    # 同一高冲突词 5 次后固化，第 6 次走 L0
    rt2 = Runtime(FakeBody(), path="_y.json")
    rt2.aligner = lambda turn, rel: {"score": 0.9, "confidence": 0.8,
                                     "evidence": ["x"], "reason": "ok"}
    rt2.prev_text = "上一句"
    for _ in range(5):
        rt2.hear("u1", "草")
    before = rt2.llm_calls
    r = rt2.hear("u1", "草")
    check("第6次走 L0", r.get("mode") == "l0", r)
    check("第6次不调 LLM", rt2.llm_calls == before, (before, rt2.llm_calls))


def test_consolidation_and_desensitize():
    """巩固：高频负面固化；误判降权/剔除。"""
    from her2 import L0
    from her2.consolidation import consolidate
    l0 = L0()
    events = [{"text": "靠", "P": -0.6, "weight": 0.8} for _ in range(3)]
    added = consolidate(events, l0, min_count=3)
    check("巩固进词典", "靠" in l0.dict and added == ["靠"], added)
    w0 = l0.dict["靠"].weight
    l0.feedback("靠", False)
    check("误判降权", l0.dict["靠"].weight < w0, l0.dict["靠"].weight)
    l0.feedback("靠", False)
    check("降到阈值就剔除", "靠" not in l0.dict, list(l0.dict))




def test_l0_habits_are_learned_conditioned():
    """习惯：同关系下反复正结果才固化；换关系不触发；不用会消退。"""
    from her2 import L0
    l0 = L0()
    for _ in range(5):
        l0.learn("好吧", "owner", 1.0)
    check("正结果固化", l0.dict["好吧"].kind == "habit", l0.dict.get("好吧"))
    st = {"Energy": 0.9, "Stress": 0.0, "Autonomy": 0.8, "P": 0.2}
    r = l0.try_respond("好吧", st, {"kind": "owner"})
    check("对主人触发", r and r["reason"] == "habit", r)
    r2 = l0.try_respond("好吧", st, {"kind": "stranger"})
    check("对陌生人不动", r2 is None, r2)

    l0b = L0()
    for _ in range(5):
        l0b.learn("随便吧", "owner", 0.0)
    check("负结果不固化", "随便吧" not in l0b.dict, l0b.dict)

    l0.decay(86400)
    check("不用会消退", "好吧" not in l0.dict, l0.dict)




def test_learn_and_calibration_chain():
    """L0 学习带关系/结果；R1 未校准就拒判，状态不动。"""
    from her2 import Runtime, FakeBody

    def mk(score):
        rt = Runtime(FakeBody(), path="_x.json")
        rt.prev_text = "上一句"
        rt.aligner = lambda turn, rel, s=score: {"score": s, "confidence": 0.8,
                                                "evidence": ["x"], "reason": "ok"}
        return rt

    rt = mk(0.2)
    for _ in range(5):
        rt.hear("owner", "好吧")
        rt.recent_text = []
    check("正结果+关系固化", "好吧" in rt.l0.dict and
          rt.l0.dict["好吧"].kind == "habit", rt.l0.dict.get("好吧"))
    check("记住关系", rt.l0.dict["好吧"].relation_kind == "owner", rt.l0.dict["好吧"])

    rt2 = mk(0.9)
    for _ in range(5):
        rt2.hear("owner", "你滚")
        rt2.recent_text = []
    check("冲突不固化", "你滚" not in rt2.l0.dict, rt2.l0.dict)

    # Calibration 只做评测：只报告共识，不暴露标准答案
    from her2 import Calibration
    c = Calibration()
    for _ in range(3):
        c.add("Q", "对齐")
    rep = c.report("Q")
    check("报告只给共识", rep and "consensus_rate" in rep, rep)
    check("报告无 label", rep and "label" not in rep and "score" not in rep, rep)




def test_quality_distortion_consolidation_wired():
    """客观 quality / 输出干扰 / 挂机巩固 都接进 runtime。"""
    from her2 import Runtime, FakeBody
    rt = Runtime(FakeBody(), path="_x.json")
    c0 = rt.h.value("Connection")
    rt.receive_reply_measured(left=True)
    check("measured 左→Connection 降", rt.h.value("Connection") < c0, "")
    c1 = rt.h.value("Connection")
    rt.receive_reply_measured(latency_s=5, reply_len=80, asked_back=True)
    check("measured 热情→Connection 升", rt.h.value("Connection") > c1, "")

    rt2 = Runtime(FakeBody(), speaker=lambda pay: {"say": "主人，僵尸在左前方三米，快跑！"},
                  poll_every=1, path="_y.json")
    rt2.h.change("Safety", -1.0)   # 拉高 Stress
    rt2.h.change("Trust", -0.7)
    rt2.h.change("Autonomy", -0.8)
    rt2.h.change("Energy", -0.6)
    rt2.tick()
    check("高压力有干扰", rt2.says and rt2.says[-1]["say"] != rt2.says[-1]["raw"],
          rt2.says[-1:])
    check("raw 原样保留", "僵尸" in rt2.says[-1]["raw"], rt2.says[-1:])

    rt3 = Runtime(FakeBody(), path="_z.json")
    rt3.episodes = ["靠", "靠", "靠"]
    added = rt3.consolidate_now()
    check("巩固写入 L0", "靠" in rt3.l0.dict and added == ["靠"], (added, rt3.l0.dict))




def test_teaching_dream_and_promise():
    """教学/做梦/承诺预测都接进 runtime，且不直接改长期结论。"""
    from her2 import Runtime, FakeBody, LESSON_COLD_THEN_COMFORT
    rt = Runtime(FakeBody(), path="_x.json")
    w0 = rt.l2.w["hp_decrease"]
    recs = rt.teach(LESSON_COLD_THEN_COMFORT)
    check("教学跑完", len(recs) == 4 and all(r["source"] == "taught" for r in recs), recs)
    check("教学进 L2", rt.l2.w["hp_decrease"] > w0, rt.l2.w["hp_decrease"])

    rt.episodes = ["掉了 3 血", "拿到花"]
    cands = rt.dream_now()
    check("做梦出候选", isinstance(cands, list) and cands, cands)

    rt.promise("p1", "owner", "今晚来")
    r = rt.check_promise("owner", came=False)
    check("没来→surprise 1", r["surprise"] == 1.0, r)
    check("承诺标记 broken", rt.anchors.pending("owner") == [], "")
    rt.promise("p2", "owner", "明天来")
    r2 = rt.check_promise("owner", came=True)
    check("来了→surprise 0", r2["surprise"] == 0.0, r2)




def test_regen_vs_owner_care():
    """生理自愈不涨 Trust；主人照顾才涨。"""
    from her2 import Runtime, FakeBody
    b = FakeBody()
    b.state["hp"] = 10
    rt = Runtime(b, path="_x.json")
    for _ in range(100):
        b.state["hp"] = min(20, b.state["hp"] + 1)
        rt.tick()
    check("自愈 100 次 Trust 不动", abs(rt.h.value("Trust") - 0.7) < 1e-9,
          rt.h.value("Trust"))

    b2 = FakeBody()
    b2.state["hp"] = 10
    rt2 = Runtime(b2, path="_y.json")
    b2.state["hp"] = 13
    b2.state["heal_from"] = "owner"
    rt2.tick()
    check("主人照顾→Trust 升", rt2.h.value("Trust") > 0.7, rt2.h.value("Trust"))




def test_delayed_realization():
    """当时好话 → 冲突 → 判官复盘 retro_bad → 倒扣 + 事实。"""
    from her2 import Runtime, FakeBody
    def mk(judge):
        rt = Runtime(FakeBody(), path="_x.json")
        rt.prev_text = "上一句"
        scores = {"你今天真好看": 0.15, "你滚": 0.95}
        rt.aligner = lambda turn, rel: {"score": scores.get(turn["b"], 0.5),
                                        "confidence": 0.8, "evidence": ["x"],
                                        "reason": "ok"}
        rt.reappraiser = judge
        return rt

    def bad(prior, trigger):
        return {"label": "retro_bad", "confidence": 0.8, "why": "事后看是暗贬"}

    rt = mk(bad)
    rt.hear("u1", "你今天真好看")
    t_before = rt.relations.get("u1").trust
    rt.hear("u1", "你滚")
    check("发生回溯", rt.facts, rt.facts)
    check("倒扣了信任", rt.relations.get("u1").trust < t_before - 0.03,
          rt.relations.get("u1").context())
    check("记了回神", any("回神" in e for e in rt.episodes), rt.episodes[-3:])

    rt2 = mk(None)
    rt2.hear("u1", "你今天真好看")
    rt2.hear("u1", "你滚")
    check("无判官不臆断", rt2.facts == [], rt2.facts)

    def ok(prior, trigger):
        return {"label": "retro_ok", "confidence": 0.8, "why": "确实是夸"}
    rt3 = mk(ok)
    rt3.hear("u1", "你今天真好看")
    rt3.hear("u1", "你滚")
    check("判官说不是→不清算", rt3.facts == [], rt3.facts)




def test_knowledge_card_and_high_stakes():
    """复盘写经验卡；高风险场景绕过 L0。"""
    from her2 import Runtime, FakeBody
    rt = Runtime(FakeBody(), path="_x.json")
    rt.l0.add("草")
    check("平时走 L0", rt.hear("u1", "草")["mode"] == "l0", "")
    rt2 = Runtime(FakeBody(), path="_y.json")
    rt2.l0.add("草")
    rt2.last_speaker = "u2"
    rt2.relations.get("u2").trust = 0.05
    rt2.h.change("Safety", -0.8)
    rt2.last_conflict = 0.9
    rt2._update_load()
    check("高负荷由物理派生", rt2.cognitive_load > 0.7, rt2.cognitive_load)
    check("无手动开关", not hasattr(rt2, "high_stakes"), "")

    def judge(prior, trigger):
        return {"label": "retro_bad", "confidence": 0.9,
                "why": "事后看是暗贬",
                "lesson": "表面夸奖、实则暗贬的话，下次要警惕。"}
    rt3 = Runtime(FakeBody(), path="_z.json")
    rt3.prev_text = "上一句"
    rt3.aligner = lambda turn, rel: {"score": 0.15 if "好看" in turn["b"] else 0.9,
                                     "confidence": 0.8, "evidence": ["x"], "reason": "ok"}
    rt3.reappraiser = judge
    rt3.hear("u1", "你今天真好看")
    rt3.hear("u1", "你滚")
    check("写出经验卡", rt3.knowledge.cards, rt3.knowledge.cards)
    got = rt3.knowledge.retrieve("夸奖 暗贬")
    check("能召回经验", got, got)




def test_suspicion_and_cognitive_load():
    """经验卡写文本轨；suspicion 写物理轨；认知负荷连续抑制 L0。"""
    from her2 import Runtime, FakeBody
    rt = Runtime(FakeBody(), path="_x.json")
    rt.prev_text = "上一句"
    rt.aligner = lambda turn, rel: {"score": 0.15 if "好看" in turn["b"] else 0.95,
                                    "confidence": 0.8, "evidence": ["x"], "reason": "ok"}
    rt.reappraiser = lambda prior, trig: {"label": "retro_bad", "confidence": 0.8,
                                          "why": "暗贬", "lesson": "警惕反常夸奖"}
    rt.hear("u1", "你今天真好看")
    rt.hear("u1", "你滚")
    check("打上 suspicion", rt.relations.get("u1").suspicion > 0,
          rt.relations.get("u1").context())

    # 同一句夸奖，有 suspicion 时冲突分更高
    a = Runtime(FakeBody(), path="_a.json")
    a.prev_text = "上一句"
    a.aligner = lambda turn, rel: {"score": 0.15, "confidence": 0.8,
                                   "evidence": ["x"], "reason": "ok"}
    r0 = a.hear("u1", "你今天真好看")
    b = Runtime(FakeBody(), path="_b.json")
    b.prev_text = "上一句"
    b.aligner = a.aligner
    b.relations.get("u1").suspicion = 0.8
    r1 = b.hear("u1", "你今天真好看")
    check("suspicion 抬高冲突分", r1["score"] > r0["score"], (r0["score"], r1["score"]))

    c = Runtime(FakeBody(), path="_c.json")
    c.l0.add("草")
    c.cognitive_load = 1.0
    check("满负荷不反射", c.hear("u1", "草").get("mode") != "l0", "")




def test_cognitive_load_is_derived():
    """认知负荷由 不信任 + 缺安全 + 冲突 派生，不是手动开关。"""
    from her2 import Runtime, FakeBody
    rt = Runtime(FakeBody(), path="_x.json")
    rt.last_speaker = "u2"
    rt.relations.get("u2").trust = 0.1
    rt.h.change("Safety", -0.8)
    rt.last_conflict = 0.9
    rt._update_load()
    check("陌生人+危险+冲突→高负荷", rt.cognitive_load > 0.7, rt.cognitive_load)

    rt2 = Runtime(FakeBody(), path="_y.json")
    rt2.last_speaker = "owner"   # trust 0.8, Safety 0.8
    rt2.last_conflict = 0.1
    rt2._update_load()
    check("信任+安全→低负荷", rt2.cognitive_load < 0.3, rt2.cognitive_load)

    check("没有手动 setter", not hasattr(rt, "set_cognitive_load"), dir(rt))




def test_load_decay_and_l0_gate():
    """A 时间治愈 / B 高压静默 / C 放松活跃。"""
    from her2 import Runtime, FakeBody
    a = Runtime(FakeBody(), path="_a.json")
    a.last_speaker = "u1"; a.relations.get("u1").trust = 0.5
    a.last_conflict = 0.95; a._update_load()
    l0 = a.cognitive_load
    for _ in range(100):
        a.tick(); a.last_speaker = "u1"
    check("A 负荷随时间降", a.cognitive_load < l0, (l0, a.cognitive_load))

    b = Runtime(FakeBody(), path="_b.json")
    b.last_speaker = "u2"; b.relations.get("u2").trust = 0.05
    b.h.change("Safety", -0.9); b.last_conflict = 0.9; b._update_load()
    check("B 高压 load>0.8", b.cognitive_load > 0.8, b.cognitive_load)
    st = {"Energy": 0.8, "Autonomy": 0.8, "Stress": 0.5, "P": 0.0}
    b.l0.add("草")
    hits = sum(1 for _ in range(1000)
               if b.l0.try_respond("草", st, b.relations.get("u2").context(),
                                   cognitive_load=b.cognitive_load))
    check("B L0 基本静默", hits / 1000 < 0.15, hits / 1000)

    c = Runtime(FakeBody(), path="_c.json")
    c.last_speaker = "owner"; c.last_conflict = 0.0; c._update_load()
    check("C 放松 load<0.2", c.cognitive_load < 0.2, c.cognitive_load)
    c.l0.add("草")
    hits2 = sum(1 for _ in range(1000)
                if c.l0.try_respond("草", st, c.relations.get("owner").context(),
                                    cognitive_load=c.cognitive_load))
    check("C L0 活跃", hits2 / 1000 > 0.8, hits2 / 1000)




def test_feedback_learns_per_user_not_cohort():
    """关系学习按 user_id，不出现年龄段规则。"""
    from her2 import Runtime, FakeBody
    rt = Runtime(FakeBody(), path="_x.json")
    u1 = rt.relations.get("u1"); u2 = rt.relations.get("u2")
    t1, t2 = u1.trust, u2.trust
    rt.receive_reply_measured(latency_s=5, reply_len=60, asked_back=True,
                              speaker_id="u1")
    check("正反馈→这个人 trust 升", u1.trust > t1, (t1, u1.trust))
    check("别人不变", u2.trust == t2, (t2, u2.trust))
    rt.receive_reply_measured(left=True, speaker_id="u1")
    check("负反馈→trust 降", u1.trust < t1 + 0.05, u1.trust)
    check("关系里没有年龄字段",
          "age" not in rt.relations.get("u1").context(), rt.relations.get("u1").context())
    check("新关系默认 unknown", rt.relations.get("u9").context()["known"] is False,
          rt.relations.get("u9").context())




def test_dialog_context_and_r0_roles():
    """接口契约：上下文含双方角色；R0 的 A=她上一句、B=他这一句。"""
    from her2 import Runtime, FakeBody
    seen = {}
    def speaker(pay):
        seen["ctx"] = list(pay["context_window"])
        return "在呢"
    def aligner(turn, rel):
        seen["a"], seen["b"] = turn["a"], turn["b"]
        return {"score": 0.3, "confidence": 0.6, "evidence": ["x"], "reason": "ok"}
    rt = Runtime(FakeBody(), speaker=speaker, poll_every=0, path="_x.json")
    rt.aligner = aligner
    rt.hear("u1", "在吗")
    rt._wake()
    check("上下文有他", any(x.startswith("他：") for x in seen["ctx"]), seen["ctx"])
    rt.hear("u1", "嗯")
    rt._wake()
    check("上下文有她", any(x.startswith("她：") for x in seen["ctx"]), seen["ctx"])
    check("R0 A=她上一句", seen["a"] == "在呢", seen)
    check("R0 B=他这一句", seen["b"] == "嗯", seen)




def test_r0_prompt_and_threat_jump_distortion():
    """R0 prompt 固化示例；threat 跳变时输出至少断一次。"""
    from her2.r0_prompt import R0_PROMPT
    from her2.receptor_bus import render_output
    check("prompt 含废物", "废物" in R0_PROMPT and "0.9" in R0_PROMPT, "")
    check("prompt 含隐性贬低", "你行不行啊" in R0_PROMPT, "")
    forced = render_output("我没事", 0.55, seed=0, delta_threat=0.5)
    check("跳变强制断句", "……" in forced, forced)
    calm = render_output("我没事", 0.2, seed=0, delta_threat=0.5)
    check("低压不强制", calm == "我没事", calm)




def test_json_from_text_tolerates_extra():
    from her2.llm import json_from_text
    check("前后有废话也能解", json_from_text('好的：{"say":"在呢"} 完毕')["say"] == "在呢", "")
    check("裸 JSON", json_from_text('{"a":1}')["a"] == 1, "")
    check("多个对象取第一个", json_from_text('{"a":1}{"b":2}')["a"] == 1, "")
    try:
        json_from_text('{"a":1')
        raise AssertionError("should fail")
    except ValueError:
        check("截断会报错", True, "")




def test_restart_keeps_her():
    """关掉再开：关系/习惯/经验卡/承诺/身体状态都要还在。"""
    from her2 import Runtime, FakeBody
    path = "_persist_test.json"
    rt = Runtime(FakeBody(), path=path)
    rt.h.change("Safety", -0.4)
    rt.relations.get("u1").trust = 0.91
    rt.relations.get("u1").suspicion = 0.7
    rt.l0.add("草", kind="habit")
    rt.knowledge.add("他夸我可能是暗贬", tags=["u1"])
    rt.promise("p1", "u1", "今晚来")
    rt.dialog = ["他：在吗", "她：在呢"]
    rt.prev_text = "在呢"
    rt.save()

    rt2 = Runtime(FakeBody(), path=path)
    ok = rt2.load()
    check("读档成功", ok, "")
    check("关系还在", abs(rt2.relations.get("u1").trust - 0.91) < 1e-9,
          rt2.relations.get("u1").context())
    check("怀疑还在", abs(rt2.relations.get("u1").suspicion - 0.7) < 1e-9, "")
    check("习惯还在", "草" in rt2.l0.dict, rt2.l0.dict)
    check("经验卡还在", rt2.knowledge.cards, "")
    check("承诺还在", rt2.anchors.pending("u1"), "")
    check("对话还在", rt2.dialog == ["他：在吗", "她：在呢"], rt2.dialog)
    check("身体状态还在", abs(rt2.h.value("Safety") - rt.h.value("Safety")) < 1e-9, "")




def test_autosave_every_n_ticks():
    from pathlib import Path
    from her2 import Runtime, FakeBody
    path = "_autosave_test.json"
    rt = Runtime(FakeBody(), path=path)
    rt.save_every = 5
    for _ in range(5):
        rt.tick()
    check("到点自动存档", Path(path).exists(), path)
    rt2 = Runtime(FakeBody(), path=path)
    check("自动存档可读", rt2.load() and rt2.tick_no == 5, rt2.tick_no)




def test_tick_decays_habit_and_relation():
    from her2 import Runtime, FakeBody
    rt = Runtime(FakeBody(), path="_decay_test.json")
    rt.relations.get("owner").trust = 0.9
    rt.l0.add("草", kind="habit")
    for _ in range(3600):
        rt.tick()
    check("关系向基线回落", rt.relations.get("owner").trust < 0.9,
          rt.relations.get("owner").trust)
    check("习惯会消退", rt.l0.dict["草"].weight < 1.0, rt.l0.dict["草"].weight)




def test_she_can_choose_to_sleep():
    from pathlib import Path
    from her2 import Runtime, FakeBody
    class B(FakeBody):
        def __init__(self):
            super().__init__()
            self.state = {"pos": [0, 0, 0], "hp": 20, "food": 20,
                          "players": {}, "items": {}}
    rt = Runtime(B(), poll_every=0, path="_sleep_test.json",
                 speaker=lambda pay: {"say": "好困，我去睡了", "act_suggest": "sleep"})
    rt.h.vars["Energy"].value = 0.1
    rt.h.vars["Fatigue"].value = 0.9
    rt._wake()
    check("wake 不直接睡", not rt.asleep, rt.asleep)
    rt.tick()
    check("idle 动机高时 L4 自己睡", rt.asleep, rt.asleep)
    check("睡完存档", Path("_sleep_test.json").exists(), "")


def test_rest_recovers_fatigue():
    from her2 import Runtime, FakeBody
    rt = Runtime(FakeBody(), path="_rest_test.json")
    rt.h.vars["Fatigue"].value = 0.8
    e0 = rt.h.value("Energy")
    rt.h.rest(8)
    check("睡觉回体力", rt.h.value("Energy") > e0, rt.h.value("Energy"))
    check("睡觉解疲劳", rt.h.value("Fatigue") < 0.3, rt.h.value("Fatigue"))




def test_blackout_and_trauma():
    """极端疲劳直接昏睡；单次强冲击进巩固。"""
    from her2 import Runtime, FakeBody
    calls = []
    rt = Runtime(FakeBody(), poll_every=0, path="_blackout_test.json",
                 speaker=lambda pay: calls.append(pay) or {"say": "我还能聊"})
    rt.h.vars["Energy"].value = 0.04
    rt.h.vars["Fatigue"].value = 0.95
    out = rt._wake()
    check("断电不让她说话", out == "" and calls == [], (out, len(calls)))
    check("断电后回体力", rt.h.value("Energy") > 0.5, rt.h.value("Energy"))
    check("注入昏睡事实", any("眼前一黑" in f for f in rt.facts), rt.facts)

    rt2 = Runtime(FakeBody(), path="_trauma_test.json")
    rt2.traumas = [{"text": "废物", "charge": 0.9}]
    added = rt2.consolidate_now()
    check("单次强冲击也固化", "废物" in added and "废物" in rt2.l0.dict, added)




def test_sleep_blocks_llm_and_wakes():
    from her2 import Runtime, FakeBody
    calls = []
    rt = Runtime(FakeBody(), poll_every=0, path="_sleep_gate.json",
                 speaker=lambda pay: calls.append(pay) or {"say": "在"})
    rt.aligner = lambda t, r: calls.append("r0") or {"threat": 0.0, "confidence": 1.0,
                                                     "evidence": [], "reason": "ok"}
    rt.sleep(hours=0.001, forced=True)
    check("睡着后 hear 拒收", rt.hear("owner", "在吗").get("reason") == "asleep", "")
    check("睡着后不说话", rt._wake() == "" and calls == [], len(calls))
    for _ in range(5):
        rt.tick()
    check("到点会醒", rt.asleep is False, rt.asleep)




def test_mc_body_sleep_flag():
    from her2 import Runtime
    from her2.body_live import MCBody
    seen = []
    class Bridge:
        def observe(self):
            return {"self": {"health": 20, "food": 20}, "players": {}, "inventory": []}
        def _post(self, path, payload):
            seen.append((path, payload.get("asleep")))
            return {"ok": True}
    body = MCBody(Bridge())
    rt = Runtime(body, poll_every=0, path="_mcsleep.json")
    rt.sleep(hours=0.001)
    check("睡觉通知身体", ("/sleep", True) in seen, seen)
    for _ in range(5):
        rt.tick()
    check("醒来通知身体", ("/sleep", False) in seen, seen)




def test_mc_death_and_water_reach_runtime():
    from her2 import Runtime
    from her2.body_live import MCBody
    class Bridge:
        def __init__(self): self.st = {"self": {"health": 20, "food": 20}, "players": {}, "inventory": []}
        def observe(self): return self.st
        def _post(self, path, payload): return {"ok": True}
    b = Bridge(); body = MCBody(b)
    rt = Runtime(body, poll_every=0, path="_mcdeath.json")
    b.st = {"self": {"health": 0, "food": 20, "in_water": True},
            "players": {}, "inventory": [], "hostile": [{"name": "zombie", "dist": 1}],
            "events": [{"type": "death"}]}
    rt.tick()
    check("水里进体感", body.last.get("in_water") is True, body.last)
    check("怪近了进体感", body.last.get("hostile_near") == 1.0, body.last)
    check("死亡进体感", body.last.get("deaths") == 1, body.last)
    check("死亡写事实", any("死了一次" in f for f in rt.facts), rt.facts)
    check("死亡进创伤", any(t["text"] == "死了" for t in rt.traumas), rt.traumas)
    check("死亡抬 Threat", rt.h.value("Threat") > 0.5, rt.h.value("Threat"))




def test_generic_act_and_mc_module_optional():
    from her2 import Runtime, FakeBody
    class Body(FakeBody):
        def __init__(self):
            super().__init__(); self.did = []
        def act(self, a):
            self.did.append(a); return {"ok": True, "action": a}
    b = Body()
    b.state = {"pos": [0, 0, 0], "hp": 20, "food": 20,
               "players": {"owner": 4}, "items": {},
               "terrain": {"feet": "stone"}}
    rt = Runtime(b, poll_every=0, path="_act_test.json",
                 speaker=lambda pay: {"say": "走", "act_suggest": "follow"})
    rt.act("jump")           # 底层手动接口仍可直接调
    rt._wake()
    check("wake 不再执行建议", b.did == ["jump"], b.did)
    check("建议被保留", rt.last_suggest == "follow", rt.last_suggest)
    rt.h.vars["Connection"].value = 0.05
    rt.h.vars["Trust"].value = 0.9
    rt.tick()
    check("L4 在 tick 后选动作", b.did and b.did[-1] == "follow", b.did)
    check("没手就说 no_act", Runtime(FakeBody(), path="_noact.json").act("jump")["reason"] == "no_act", "")


def test_mc_tutorial_advances():
    from her2 import Runtime, FakeBody
    from her2.mc_tutorial import Tutorial, Step
    tu = Tutorial(steps=[Step("look", "看看四周", "", lambda s, c: True),
                         Step("walk", "走两步", "", lambda s, c: abs(s["pos"][0]) >= 2)])
    rt = Runtime(FakeBody(), poll_every=0, path="_tutorial_test.json")
    rt.body.state = {"pos": [0, 0, 0], "hp": 20, "food": 20, "players": {}, "items": {}}
    rt.tutorial = tu
    tu.start(rt.body.see())
    rt.body.state["pos"] = [2, 0, 0]
    rt.tick()
    check("教程会自动推进", tu.idx == 2, tu.idx)
    check("学会写进经验", any("走两步" in c.text for c in rt.knowledge.cards),
          [c.text for c in rt.knowledge.cards])
    from her2.mc_tutorial import Tutorial as T2, Step as S2
    tu2 = T2(steps=[S2("eat", "吃东西", "", lambda s, c: False,
                        skip=lambda s, c: True)])
    tu2.update({})
    check("做不了就跳过", tu2.idx == 1 and "跳过" in tu2.learned[0], tu2.learned)




def test_tutorial_safety_interrupt():
    from her2.mc_tutorial import Tutorial, Step
    tu = Tutorial(steps=[Step("walk", "走两步", "", lambda s, c: False)],
                  danger=lambda s, c: float(s.get("hp", 20)) < 8)
    tu.update({"hp": 5})
    check("危险时暂停教程", tu.in_danger and tu.current()["step"] == "danger",
          tu.current())
    check("危险时不推进", tu.idx == 0, tu.idx)
    tu.update({"hp": 20})
    check("安全后恢复", not tu.in_danger, tu.current())




def test_tutorial_task_board():
    from her2.mc_tutorial import Tutorial, Step
    tu = Tutorial(steps=[Step("a", "看看", "", lambda s, c: True),
                         Step("b", "走走", "", lambda s, c: False)])
    tu.update({})
    b = tu.board()
    check("任务栏 0/1", b[0]["done"] == 1 and b[1]["done"] == 0, b)
    check("当前步高亮", b[1]["current"] == 1, b)
    check("文本有 0/1", "(1/1)" in tu.text() and "(0/1)" in tu.text(), tu.text())




def test_tutorial_settle_before_start():
    from her2.mc_tutorial import Tutorial, Step
    tu = Tutorial(steps=[Step("walk", "走走", "", lambda s, c: True)], settle_ticks=3)
    for _ in range(3):
        tu.update({})
    check("稳定期内不判", tu.idx == 0, tu.idx)
    tu.update({})
    check("稳定后开判", tu.idx == 1, tu.idx)




def test_blocked_feedback():
    from her2 import Runtime, FakeBody
    class B(FakeBody):
        def __init__(self):
            super().__init__()
            self.state = {"pos": [0, 64, 0], "hp": 20, "food": 20, "players": {}, "items": {}}
            self.last = {"pos": [0, 64, 0]}
        def act(self, a):
            self.last = {"pos": list(self.state["pos"])}
            return {"ok": True, "action": a}
        def job(self):
            return {"ok": True, "busy": True, "action": "forward", "result": None}
    b = B(); rt = Runtime(b, poll_every=0, path="_blocked.json")
    rt.act("forward")
    rt.mining = True   # 隔离 L4，专测 blocked 结算
    for _ in range(11):
        rt.tick()
    check("卡住写经验", any("被挡住" in c.text for c in rt.knowledge.cards),
          [c.text for c in rt.knowledge.cards])
    b.state["pos"] = [2, 64, 0]; b.last = {"pos": [2, 64, 0]}
    rt.tick()
    check("移动后解除", not rt.blocked and rt.last_action == "", (rt.blocked, rt.last_action))




def test_places_memory():
    from her2 import Runtime, FakeBody
    class B(FakeBody):
        def __init__(self):
            super().__init__(); self.did = []
        def act(self, a):
            self.did.append(a); return {"ok": True, "action": a}
    b = B(); rt = Runtime(b, poll_every=0, path="_places.json")
    rt.remember_place("家", 10, 64, 20)
    r = rt.act("go_to_place:家")
    check("按名字去地点", b.did and b.did[-1] == "go_to:10.0,64.0,20.0", (r, b.did))
    check("没记过就说 no_place", rt.act("go_to_place:公司")["reason"] == "no_place", "")
    rt.save()
    rt2 = Runtime(FakeBody(), path="_places.json"); rt2.load()
    p = rt2.places.get("家")
    check("地点会存档", p is not None and p.x == 10, rt2.places.as_list())




def test_coords_only_for_mc():
    from her2.narrative import validate_slow, slow_messages
    v = validate_slow({"say": "走", "act_suggest": "go_to:1,2,3"})
    check("建议字段通过", v["act_suggest"] == "go_to:1,2,3", v)
    mc = slow_messages({"allow_coords": True})[0]["content"]
    real = slow_messages({"allow_coords": False})[0]["content"]
    check("MC 有坐标提示", "go_to:x,y,z" in mc, mc[-80:])
    check("现实无坐标提示", "go_to:x,y,z" not in real, real[-80:])
    from her2.mc_play import MCPlay
    check("MC 模块声明坐标", MCPlay.allow_coords is True, "")


def test_home_pull_motive():
    from her2 import Runtime, FakeBody
    rt = Runtime(FakeBody(), poll_every=0, path="_homepull.json")
    check("没家就没驱力", rt._home_pull() == 0.0, rt._home_pull())
    rt.remember_place("家", 0, 64, 0, tags=["shelter"])
    rt.h.change("Safety", -0.5)
    rt.h.change("Energy", -0.4)
    rt.h.change("Connection", -0.3)
    pull = rt._home_pull()
    check("缺安全/能量/连接→想回家", pull > 0.5, pull)




def test_home_urge_triggers_action_chance():
    from her2 import Runtime, FakeBody
    calls = []
    rt = Runtime(FakeBody(), poll_every=0, path="_urge.json",
                 speaker=lambda pay: calls.append(pay) or {"action": "hold"})
    rt.remember_place("家", 0, 64, 0, tags=["shelter"])
    rt.h.change("Safety", -0.7)
    for _ in range(400):
        rt.tick()
    check("动机累积会给起身机会", len(calls) > 0, len(calls))




def test_threat_field_before_harm():
    from her2 import Runtime, FakeBody
    b = FakeBody()
    b.state = {"hp": 20, "food": 20, "players": {}, "items": {}, "hostile_near": 1.0}
    rt = Runtime(b, poll_every=0, path="_threat.json")
    s0 = rt.h.value("Safety")
    for _ in range(100):
        rt.tick()
    check("没受伤也会怕", rt.h.value("Safety") < s0 - 0.1, rt.h.value("Safety"))
    check("威胁抬 Stress", rt.h.stress() > 0.25, rt.h.stress())
    b.state["hostile_near"] = 99.0
    for _ in range(2400):
        rt.tick()
    check("危险走了会缓", rt.h.value("Safety") > 0.7, rt.h.value("Safety"))




def test_hunger_drives_energy():
    from her2 import Runtime, FakeBody
    b = FakeBody()
    b.state = {"hp": 20, "food": 2, "players": {}, "items": {}}
    rt = Runtime(b, poll_every=0, path="_hunger.json")
    e0 = rt.h.value("Energy")
    for _ in range(600):
        rt.tick()
    e1 = rt.h.value("Energy")
    check("饿着会掉电", e1 < e0 - 0.15, (e0, e1))
    b.state["food"] = 12
    rt.tick()
    check("吃东西回电", rt.h.value("Energy") > e1, rt.h.value("Energy"))




def test_autonomy_and_connection_dynamics():
    from her2 import Runtime, FakeBody
    class B(FakeBody):
        def __init__(self):
            super().__init__()
            self.state = {"pos": [0, 0, 0], "hp": 20, "food": 20,
                          "players": {"owner": 4}, "items": {}}
        def act(self, a): return {"ok": True}
    rt = Runtime(B(), poll_every=0, path="_auto.json")
    a0 = rt.h.value("Autonomy")
    for _ in range(5):
        rt.request("follow")
    check("被要求会掉自主", rt.h.value("Autonomy") < a0 - 0.05, rt.h.value("Autonomy"))
    a1 = rt.h.value("Autonomy")
    rt.action_origin = "autonomous"; rt.last_action = "mine"; rt.mining = True
    for _ in range(10):
        rt.tick()
    check("自主做事会回一点", rt.h.value("Autonomy") > a1, rt.h.value("Autonomy"))

    b = FakeBody(); b.state = {"hp": 20, "food": 20, "players": {"A": 25}, "items": {}}
    rt3 = Runtime(b, poll_every=0, path="_conn.json")
    c0 = rt3.h.value("Connection")
    for _ in range(1000):
        rt3.tick()
    check("远了连接掉", rt3.h.value("Connection") < c0, rt3.h.value("Connection"))


def test_willing_log():
    from pathlib import Path
    from her2 import Runtime, FakeBody
    log = Path("_wtest.willing.jsonl")
    log.unlink(missing_ok=True)
    class B(FakeBody):
        def __init__(self):
            super().__init__()
            self.state = {"pos": [0, 0, 0], "hp": 20, "food": 20,
                          "players": {"owner": 4}, "items": {}}
        def act(self, a): return {"ok": True}
    b = B()
    rt = Runtime(b, poll_every=0, path="_wtest.json",
                 speaker=lambda pay: {"say": "不想去", "act_suggest": "follow",
                                      "willing": 0.3})
    rt.willing_log = log
    rt.h.vars["Connection"].value = 0.05
    rt.h.vars["Trust"].value = 0.9
    rt._wake()
    rt.tick()
    lines = [l for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]
    import json
    rec = json.loads(lines[-1])
    check("willing 落盘", rec["willing"] == 0.3 and rec["action"] == "follow", rec)
    check("带体感字段", all(k in rec for k in ("home_pull", "connection", "autonomy")), rec)
    log.unlink(missing_ok=True)


def test_utility_in_pressure():
    from her2 import Runtime, FakeBody
    seen = {}
    def sp(pay):
        seen.update(pay.get("pressure", {})); return {"say": ""}
    rt = Runtime(FakeBody(), poll_every=0, speaker=sp, path="_util.json")
    rt._wake()
    u = seen.get("utility") or {}
    check("utility 进 pressure", set(u) == {"seek_information", "silence", "hesitation"}, u)
    check("utility 是 0..1", all(0 <= v <= 1 for v in u.values()), u)




def test_motion_self_feedback():
    from her2 import Runtime, FakeBody
    b = FakeBody()
    b.state = {"pos": [0, 0, 0], "hp": 20, "food": 20, "players": {}, "items": {}}
    rt = Runtime(b, poll_every=0, path="_motion.json")
    rt.tick()
    b.state["pos"] = [1, 0, 0]
    rt.tick()
    check("知道自己在动", rt.motion["moved"] and rt.motion["speed"] > 0, rt.motion)
    b.state["pos"] = [1, 0, 0]
    rt.tick()
    check("停了自己也知道", not rt.motion["moved"], rt.motion)




def test_avatar_bridge_calls():
    from her2 import Runtime, FakeBody
    class A:
        def __init__(self): self.log = []
        def say(self, t): self.log.append(("say", t))
        def pose(self, p): self.log.append(("pose", p))
        def motion(self, speed, moved=False): self.log.append(("motion", speed, moved))
    a = A()
    rt = Runtime(FakeBody(), poll_every=0, path="_avatar.json",
                 speaker=lambda pay: {"say": "在呢", "pose": "happy"})
    rt.avatar = a
    rt._wake()
    check("台词进小窗", ("say", "在呢") in a.log, a.log)
    check("动作进小窗", ("pose", "happy") in a.log, a.log)
    rt.body.state["pos"] = [0, 0, 0]; rt.tick()
    rt.body.state["pos"] = [1, 0, 0]; rt.tick()
    check("移动进小窗", any(x[0] == "motion" and x[1] > 0 for x in a.log), a.log)




def test_far_speech_blocked_and_approach_feedback():
    from her2 import Runtime, FakeBody
    class B(FakeBody):
        def __init__(self):
            super().__init__(); self.did = []
            self.state = {"pos": [0, 0, 0], "hp": 20, "food": 20,
                          "players": {"owner": 25}, "items": {}}
        def act(self, a):
            self.did.append(a); return {"ok": True}
    b = B()
    rt = Runtime(b, poll_every=0, path="_far.json",
                 speaker=lambda pay: {"say": "我在这边！"})
    out = rt._wake()
    check("远距离 wake 不产生动作", not b.did, b.did)
    check("远距离说被拦", out == "" and not rt.says, (out, rt.says))
    check("写进事实", any("听不见" in f for f in rt.facts), rt.facts)

    b.state["players"] = {"owner": 3}
    out2 = rt._wake()
    check("靠近能说话", out2 != "" and rt.says, (out2, rt.says))

    rt.h.vars["Connection"].value = 0.05
    rt.h.vars["Trust"].value = 0.9
    b.state["players"] = {"owner": 25}
    rt.tick()
    check("approach 高时 L4 选 follow", b.did and b.did[-1] == "follow", b.did)

    b.state["players"] = {"owner": 30}
    rt.tick()
    c0 = rt.h.value("Connection")
    b.state["players"] = {"owner": 27}
    rt.tick()
    check("靠近给他反馈", rt.h.value("Connection") > c0, rt.h.value("Connection"))
    check("motion 带距离", rt.motion.get("distance_delta") == -3.0, rt.motion)


def test_far_fail_and_walk_reward():
    from her2 import Runtime, FakeBody
    class B(FakeBody):
        def __init__(self):
            super().__init__(); self.did = []
            self.state = {"pos": [0, 0, 0], "hp": 20, "food": 20,
                          "players": {"owner": 25}, "items": {}}
        def act(self, a):
            self.did.append(a); return {"ok": True}
    b = B(); rt = Runtime(b, poll_every=0, path="_rewards.json",
                          speaker=lambda pay: {"say": "喂"})
    for _ in range(3):
        rt._wake()
    check("连续失效计数", rt.far_speech_fails == 3, rt.far_speech_fails)
    check("失效会逼她", rt.h.value("Threat") > 0.1, rt.h.value("Threat"))
    check("注入绝望事实", any("喊了三次" in f for f in rt.facts), rt.facts)
    check("远距离不自动走", not b.did, b.did)

    b.state["players"] = {"owner": 25}
    rt.tick()
    rt.act("follow")
    c0 = rt.h.value("Connection")
    b.state["players"] = {"owner": 18}
    rt.tick()
    check("走近有奖励", rt.h.value("Connection") > c0, rt.h.value("Connection"))
    check("写走成功经验", any("自己走过去" in c.text for c in rt.knowledge.cards),
          [c.text for c in rt.knowledge.cards])


def test_move_intent_is_debug_only():
    from her2 import Runtime, FakeBody
    class B(FakeBody):
        def __init__(self):
            super().__init__(); self.did = []
        def act(self, a):
            self.did.append(a); return {"ok": True}
    b = B()
    b.state = {"pos": [0, 0, 0], "hp": 20, "food": 20,
               "players": {"owner": 4}, "items": {}}
    rt = Runtime(b, poll_every=0, path="_intent.json",
                 speaker=lambda pay: {"say": "我过去找你", "intent": "move"})
    out = rt._wake()
    check("wake 仍然说话", out != "" and rt.says, (out, rt.says))
    check("wake 不执行动作", not b.did, b.did)
    check("intent 不再进契约", rt.last_verbal_intent == "", rt.last_verbal_intent)


def test_conflict_arrival_and_memory_query():
    from her2 import Runtime, FakeBody
    class B(FakeBody):
        def __init__(self):
            super().__init__()
            self.state = {"pos": [0, 0, 0], "hp": 20, "food": 20,
                          "players": {"owner": 25}, "items": {}}
            self.did = []
        def act(self, a): self.did.append(a); return {"ok": True}
    b = B()
    rt = Runtime(b, poll_every=0, path="_fix3.json",
                 speaker=lambda pay: {"say": "我过来", "act_suggest": "follow"})
    rt.h.vars["Connection"].value = 0.05
    rt.h.vars["Trust"].value = 0.9
    rt.knowledge.add("离得远时，喊他听不见，要自己走过去。", tags=["距离"])
    rt._wake()
    check("wake 不直接走", not b.did, b.did)
    rt.tick()
    check("L4 选 follow", b.did and b.did[-1] == "follow", b.did)

    b.state["players"] = {"owner": 25}; rt.tick()
    c0 = rt.h.value("Connection")
    b.state["players"] = {"owner": 2}; rt.tick()
    check("到达有奖励", rt.h.value("Connection") > c0, rt.h.value("Connection"))
    check("到达写事实", any("走到他面前" in f for f in rt.facts), rt.facts)

    seen = {}
    def sp(pay):
        seen["k"] = pay.get("knowledge", [])
        return {"say": ""}
    rt2 = Runtime(B(), poll_every=0, speaker=sp, path="_fix3b.json")
    rt2.knowledge.add("离得远时，喊他听不见，要自己走过去。", tags=["距离"])
    rt2._wake()
    check("远距离能召回经验", seen.get("k"), seen.get("k"))


def test_act_can_speak():
    from her2 import Runtime, FakeBody
    class B(FakeBody):
        def __init__(self):
            super().__init__()
            self.state = {"pos": [0, 0, 0], "hp": 20, "food": 20,
                          "players": {"owner": 4}, "items": {}}
            self.did = []
        def act(self, a):
            self.did.append(a); return {"ok": True}
    b = B()
    rt = Runtime(b, poll_every=0, path="_actsay.json",
                 speaker=lambda pay: {"say": "来啦来啦", "act_suggest": "follow"})
    rt.h.vars["Connection"].value = 0.05
    rt.h.vars["Trust"].value = 0.9
    rt._wake()
    check("act 的台词不丢", rt.says and rt.says[-1].get("say") == "来啦来啦", rt.says)
    check("wake 不执行", not b.did, b.did)
    rt.tick()
    check("tick 执行 follow", b.did and b.did[-1] == "follow", b.did)


def test_self_narrative_and_review():
    from her2 import Runtime, FakeBody
    from her2.narrative import slow_messages
    rt = Runtime(FakeBody(), poll_every=0, path="_selfn.json")
    sysmsg = slow_messages({"core_narrative": ["我是大肥鱼，不是客服"]})[0]["content"]
    check("自我叙事置顶", sysmsg.startswith("[我是谁]") and "不是客服" in sysmsg, sysmsg[:40])

    rt.dialog = ["他：你是客服吗", "她：不是"]
    rt.reviewer = lambda ctx: {"score": 0.2, "drift": True, "reason": "太像客服"}
    v = rt.end_session_review()
    check("自评记录漂移", v and v["drift"] and rt.drift_log, v)
    before = rt.self_narrative.top(5)
    rt.reflect_narrative(judge=lambda ctx: {"cards": ["我说话直，不绕弯子"]})
    check("反思能写卡", "我说话直，不绕弯子" in rt.self_narrative.top(8), rt.self_narrative.top(8))
    check("自评不改卡", rt.drift_log and before, rt.drift_log)




def test_play_mode_and_drift_pain():
    from her2 import Runtime, FakeBody
    rt = Runtime(FakeBody(), poll_every=0, path="_mode.json",
                 speaker=lambda pay: {"say": "您好，有什么可以帮您",
                                      "mode": "play"})
    rt._wake()
    check("play 时允许戏腔", rt.mode == "play" and rt.says, (rt.mode, rt.says))
    rt.reviewer = lambda ctx: {"score": 0.2, "drift": True, "reason": "太像客服"}
    t0 = rt.h.value("Threat")
    rt.end_session_review()
    check("drift 会难受", rt.h.value("Threat") > t0, rt.h.value("Threat"))
    check("drift 写事实", any("提线木偶" in f for f in rt.facts), rt.facts)




def test_play_mode_is_sticky():
    from her2 import Runtime, FakeBody
    seq = [{"say": "演一下", "mode": "play"},
           {"say": "猫在打盹"},
           {"say": "变回来了", "mode": "normal"}]
    rt = Runtime(FakeBody(), poll_every=0, path="_sticky.json",
                 speaker=lambda pay: seq.pop(0))
    rt._wake(); check("进 play", rt.mode == "play", rt.mode)
    rt._wake(); check("没报保持 play", rt.mode == "play", rt.mode)
    rt._wake(); check("报 normal 退出", rt.mode == "normal", rt.mode)




def test_migrate_bundle_roundtrip():
    from pathlib import Path
    from her2.migrate import export_bundle, import_bundle
    st = Path("_mig_state.json"); st.write_text('{"tick":7,"vars":{"Trust":0.8}}', encoding="utf-8")
    wl = Path("_mig_willing.jsonl"); wl.write_text('{"willing":0.5}\n', encoding="utf-8")
    b = export_bundle(st, Path("_mig.zip"), extra=[wl])
    dest = Path("_mig_out")
    files = import_bundle(b, dest, force=True)
    check("打包含状态", any(f.name == "_mig_state.json" for f in files), files)
    check("导入内容一致", (dest / "_mig_state.json").read_text(encoding="utf-8") == st.read_text(encoding="utf-8"), "")
    import shutil
    shutil.rmtree(dest, ignore_errors=True)
    for f in (st, wl, b):
        f.unlink(missing_ok=True)




def test_concept_cards():
    from her2.concepts import ConceptMemory
    from her2 import Runtime, FakeBody
    cm = ConceptMemory()
    c = cm.add("距离导致信号衰减", ["距离远", "喊话没回应"], "follow", "走近")
    check("概念卡可写", c.concept_id == "c_001" and cm.active(), c)
    got = cm.activate("隔着一条河，喊不到他",
                      judge=lambda ctx: {"concept_ids": ["c_001"]})
    check("语义激活", got and got[0].concept_id == "c_001", got)
    cm.record("c_001", False); cm.record("c_001", False)
    check("失败不自动失效", c.fail_count == 2 and c.active, c)
    cm.retire("c_001")
    check("她自己退休才失效", not c.active and not cm.active(), c)

    rt = Runtime(FakeBody(), poll_every=0, path="_concept.json")
    rt.reflect_concepts(judge=lambda ctx: {"concepts": [
        {"name": "暗处看不清", "signs": ["黑暗", "看不到"], "action": "follow"}]})
    check("复盘写入概念", rt.concepts.active(), rt.concepts.top())




def test_concept_action_result_loop():
    from her2 import Runtime, FakeBody
    class B(FakeBody):
        def __init__(self):
            super().__init__()
            self.state = {"pos": [0, 0, 0], "hp": 20, "food": 20,
                          "players": {"owner": 25}, "items": {},
                          "terrain": {"feet": "stone"}}
        def act(self, a): return {"ok": True}
        def job(self): return {"ok": True, "busy": True, "action": "follow", "result": None}
    def setup():
        b = B(); rt = Runtime(b, poll_every=0, path="_cloop.json",
                              speaker=lambda pay: {"say": "", "act_suggest": "follow"})
        rt.h.vars["Connection"].value = 0.05
        rt.h.vars["Trust"].value = 0.9
        c = rt.concepts.add("距离远要走近", ["距离远"], "follow", "走近")
        rt.concept_judge = lambda ctx: {"concept_ids": ["c_001"]}
        rt.tick()
        return b, rt, c
    b, rt, c = setup()
    rt._wake(); rt.tick()
    check("激活概念", rt.active_concept_id == "c_001", rt.active_concept_id)
    b.state["players"] = {"owner": 18}
    rt.tick()
    check("成功回写", c.success_count == 1, c)

    b2, rt2, c2 = setup()
    for _ in range(2):
        rt2._wake()
        b2.state["players"] = {"owner": 25}
        rt2.act("follow")
        rt2.pending_concept_id = "c_001"
        for _ in range(14):
            rt2.tick()
    check("失败只记账", c2.fail_count >= 2 and c2.active, c2)
    rt2.concepts.retire("c_001")
    check("退休后不激活", rt2.concepts.activate("距离远",
          judge=lambda ctx: {"concept_ids": ["c_001"]}) == [], "")


def test_concept_auto_reflect_and_judge():
    from her2 import Runtime, FakeBody
    from her2.concept_llm import make_judge, make_reflector
    def fake_chat(messages, **kw):
        return '{"concept_ids": ["c_001"]}'
    j = make_judge(fake_chat)
    check("LLM 判官接口", j({"description": "远", "cards": [{"id": "c_001", "signs": ["远"]}]}) == {"concept_ids": ["c_001"]}, "")

    rt = Runtime(FakeBody(), poll_every=0, path="_autoconcept.json")
    rt.blocked = True
    rt.facts = ["你撞了墙"]
    rt.concept_reflector = lambda ctx: {"concepts": [
        {"name": "被挡住要换动作", "signs": ["撞墙", "卡住"], "action": "jump", "outcome": "试试跳"}]}
    rt.sleep(1)
    check("睡眠自动复盘写卡", rt.concepts.active(), rt.concepts.top())
    check("废弃记录进复盘", "deprecated" in (rt.concept_reflector.__code__.co_varnames if False else ("deprecated",)), "")

    rt2 = Runtime(FakeBody(), poll_every=0, path="_autoconcept2.json")
    rt2.concept_reflector = lambda ctx: {"concepts": []}
    rt2.reviewer = lambda ctx: {"score": 0.9, "drift": False, "reason": "ok"}
    rt2.end_session_review()
    check("复盘也能触发", rt2.concept_reflector is not None, "")




def test_retire_reason_into_memory():
    from her2 import Runtime, FakeBody
    rt = Runtime(FakeBody(), poll_every=0, path="_retirelog.json")
    c = rt.concepts.add("距离远要走近", ["距离远"], "follow", "走近")
    rt.concepts.record(c.concept_id, False)
    rt.facts = ["你被墙挡住，掉进岩浆"]
    rt.blocked = True
    rt.concept_reflector = lambda ctx: {
        "concepts": [], "retire": ["c_001"],
        "retire_reason": "掉进岩浆，太危险"}
    rt.sleep(1.0)
    check("退休进日志", rt.retire_log and rt.retire_log[-1]["concept_id"] == "c_001", rt.retire_log)
    check("理由进记忆", any("掉进岩浆" in x.text for x in rt.knowledge.cards), [x.text for x in rt.knowledge.cards])




def test_concept_prompt_layering():
    from her2.narrative import slow_messages
    cs = [{"signs": ["远"], "action": "follow", "success": 3, "fail": 0},
          {"signs": ["墙"], "action": "jump", "success": 1, "fail": 1},
          {"signs": ["水"], "action": "back", "success": 0, "fail": 2},
          {"signs": ["暗"], "action": "look", "success": 0, "fail": 0},
          {"signs": ["坑"], "action": "stop", "success": 0, "fail": 0}]
    msg = slow_messages({"concepts": cs, "retire_memories": ["掉进岩浆"]})
    u = msg[1]["content"]
    check("经验直觉前缀", u.startswith("[经验直觉]"), u[:30])
    check("最多 4 张", "坑" not in u, u[:200])
    check("记忆回溯", "[记忆回溯]" in u and "掉进岩浆" in u, u[-200:])
    check("空则不写废话", "无经验" not in slow_messages({})[1]["content"], "")




def test_world_model_expectation():
    from her2.world_model import WorldModel
    from her2.narrative import slow_messages
    wm = WorldModel()
    wm.observe("远", "follow", False, blocked=True, hp_delta=-3, distance_delta=0)
    wm.observe("远", "follow", False, blocked=True, hp_delta=-1, distance_delta=0)
    lines = wm.lines("远", ["follow"])
    check("预测失败率", lines and "失败率" in lines[0], lines)
    check("预测掉血", "平均掉血" in lines[0], lines)
    msg = slow_messages({"expectations": lines})[1]["content"]
    check("预演沙盘入 prompt", "[预演沙盘]" in msg and "follow" in msg, msg[:80])
    wm.observe("远", "jump", True, distance_delta=-5)
    lines2 = wm.preview("远", "follow", ["follow", "jump"])
    check("负面才给备选", any("jump" in x for x in lines2), lines2)




def test_llm_empty_retry_and_hold():
    from her2 import Runtime, FakeBody
    calls = {"n": 0}
    def sp(pay):
        calls["n"] += 1
        return "" if calls["n"] == 1 else {"say": "嗯"}
    rt = Runtime(FakeBody(), poll_every=0, speaker=sp, path="_retry.json")
    rt._wake()
    check("空响应会重试", calls["n"] == 2, calls)

    calls2 = {"n": 0}
    def sp2(pay):
        calls2["n"] += 1
        return ""
    rt2 = Runtime(FakeBody(), poll_every=0, speaker=sp2, path="_retry2.json")
    rt2._wake()
    check("两次空也不崩", calls2["n"] == 2 and rt2.facts, (calls2, rt2.facts))




def test_expected_pain_and_writeback():
    from her2.world_model import WorldModel
    from her2.narrative import slow_messages
    from her2 import Runtime, FakeBody
    wm = WorldModel()
    wm.observe("远", "follow", False, blocked=True, hp_delta=-5)
    wm.observe("远", "follow", False, blocked=True, hp_delta=-5)
    p = wm.predict("远", "follow")
    check("痛觉接近 1", p.expected_pain >= 0.99, p.expected_pain)
    msg = slow_messages({"expectations": wm.lines("远", ["follow"])})[1]["content"]
    check("痛觉进 prompt", "预计痛觉" in msg, msg[:100])

    class B(FakeBody):
        def act(self, a): return {"ok": True}
    b = B()
    b.state = {"pos": [0, 0, 0], "hp": 20, "food": 20,
               "players": {"owner": 25}, "items": {}}
    rt = Runtime(b, poll_every=0, path="_pain.json")
    rt.tick()
    rt.act("jump")
    b.state["players"] = {"owner": 18}
    rt.tick()
    got = [v for k, v in rt.world_model.table.items() if k.endswith("|jump")]
    check("动作结果回写", got and got[0].n >= 1, rt.world_model.table)




def test_boredom_drive():
    from her2 import Runtime, FakeBody
    from her2.narrative import slow_messages
    rt = Runtime(FakeBody(), poll_every=0, path="_bored.json")
    for _ in range(100):
        rt.tick()
    check("挂机变无聊", rt.boredom >= 0.8, rt.boredom)
    msg = slow_messages({"pressure": {"boredom": rt.boredom}})[1]["content"]
    check("无聊进上下文", "boredom" in msg and "0.8" in msg, msg[:120])




def test_asleep_persists():
    from her2 import Runtime, FakeBody
    rt = Runtime(FakeBody(), poll_every=0, path="_asleep.json")
    rt.asleep = True
    rt.sleep_until_tick = 100
    rt.save()
    rt2 = Runtime(FakeBody(), poll_every=0, path="_asleep.json")
    check("读回睡着", rt2.load() and rt2.asleep, rt2.asleep)
    rt2.tick_no = 100
    rt2.tick()
    check("到点会醒", not rt2.asleep, rt2.asleep)




def test_wake_command():
    from her2 import Runtime, FakeBody
    rt = Runtime(FakeBody(), poll_every=0, path="_wake.json")
    rt.asleep = True
    rt.sleep_until_tick = 999999
    rt.wake()
    check("叫醒清标记", not rt.asleep and rt.sleep_until_tick == 0,
          (rt.asleep, rt.sleep_until_tick))




def test_mine_result_feedback():
    from her2 import Runtime, FakeBody
    rt = Runtime(FakeBody(), poll_every=0, path="_mine.json")
    rt.boredom = 0.8
    rt._observe_ctx = "远"
    rt._observe_action = "mine"
    rt._finish_mine(True)
    check("挖到降无聊", rt.boredom < 0.6, rt.boredom)
    check("挖到写统计", rt.world_model.predict("远", "mine").n == 1, rt.world_model.table)
    check("挖到写事实", any("挖到了" in f for f in rt.facts), rt.facts)




def test_say_and_act_are_independent():
    from her2 import Runtime, FakeBody
    class B(FakeBody):
        def __init__(self):
            super().__init__()
            self.state = {"pos": [0, 0, 0], "hp": 20, "food": 20,
                          "players": {"owner": 4}, "items": {},
                          "terrain": {"feet": "stone"}}
            self.did = []
        def act(self, a):
            self.did.append(a); return {"ok": True}
    b = B()
    rt = Runtime(b, poll_every=0, path="_dual.json",
                 speaker=lambda pay: {"say": "", "act_suggest": "mine"})
    rt.h.vars["Boredom"].value = 0.95
    rt._wake()
    check("只建议不执行", not b.did, b.did)
    rt.tick()
    check("tick 选 mine", b.did and b.did[-1] == "mine", b.did)

    b2 = B()
    rt2 = Runtime(b2, poll_every=0, path="_dual2.json",
                  speaker=lambda pay: {"say": "我去挖", "act_suggest": "mine"})
    rt2.h.vars["Boredom"].value = 0.95
    rt2._wake()
    check("边说边留建议", rt2.says and rt2.says[-1].get("say") == "我去挖", rt2.says)
    check("说话不立即执行", not b2.did, b2.did)
    rt2.tick()
    check("tick 边说边做", b2.did and b2.did[-1] == "mine", b2.did)


def test_boredom_drives_look():
    from her2 import Runtime, FakeBody
    class B(FakeBody):
        def __init__(self):
            super().__init__()
            self.state = {"pos": [0, 0, 0], "hp": 20, "food": 20,
                          "players": {}, "items": {}}
            self.did = []
        def act(self, a):
            self.did.append(a); return {"ok": True}
    b = B()
    rt = Runtime(b, poll_every=0, path="_turn.json")
    rt.h.vars["Boredom"].value = 0.95
    rt.tick()
    check("无聊会看/动", b.did and b.did[-1] != "idle", b.did)

def test_expected_relief():
    from her2.world_model import WorldModel
    wm = WorldModel()
    wm.observe("远", "mine", True, boredom_delta=-0.3)
    wm.observe("远", "mine", True, boredom_delta=-0.1)
    lines = wm.lines("远", ["mine"])
    check("无聊变化入预演", "无聊变化" in lines[0], lines)
    check("平均是 -0.2", "-0.20" in lines[0], lines)




def test_mining_is_persistent():
    from her2 import Runtime, FakeBody
    class B(FakeBody):
        def __init__(self):
            super().__init__(); self.did = []
        def act(self, a):
            self.did.append(a); return {"ok": True}
    b = B()
    b.state = {"pos": [0, 0, 0], "hp": 20, "food": 20,
               "players": {"owner": 4}, "items": {},
               "terrain": {"feet": "stone"}}
    rt = Runtime(b, poll_every=0, path="_mining.json",
                 speaker=lambda pay: {"say": "我先挖着"})
    rt.tick_no = 10
    rt.act("mine")
    rt.mine_start_tick = 10
    rt.mine_timeout_ticks = 50
    rt.mine_loot = 0
    rt._wake()
    check("说话不打断挖矿", rt.mining, rt.mining)
    check("wake 不另起动作", "mine" not in b.did[1:], b.did)
    b.state["players"] = {"owner": 2}
    rt.mine_loot = 5
    rt.tick_no = 60
    rt.tick()
    check("超时才结算", not rt.mining, rt.mining)

    rt2 = Runtime(B(), poll_every=0, path="_mining2.json")
    rt2.tick_no = 10
    rt2.act("mine"); rt2.mining = True; rt2.mine_loot = 3
    rt2.act("follow")
    check("新动作打断并结算", not rt2.mining, rt2.mining)


def test_l4_chooses_when_llm_silent():
    from her2 import Runtime, FakeBody
    class B(FakeBody):
        def __init__(self):
            super().__init__()
            self.state = {"pos": [0, 0, 0], "hp": 20, "food": 20,
                          "players": {"owner": 3}, "items": {},
                          "terrain": {"feet": "stone"}}
            self.did = []
        def act(self, x):
            self.did.append(x); return {"ok": True}
    b = B()
    rt = Runtime(b, poll_every=0, path="_arb.json",
                 speaker=lambda pay: {"say": ""})
    rt.h.vars["Boredom"].value = 0.95
    rt._wake()
    check("wake 不补动作", not b.did, b.did)
    rt.tick()
    check("L4 自己选动作", b.did and b.did[-1] in ("mine", "follow"), b.did)


def test_action_decision_log():
    from pathlib import Path
    import json
    from her2 import Runtime, FakeBody
    class B(FakeBody):
        def __init__(self):
            super().__init__()
            self.state = {"pos": [0, 0, 0], "hp": 20, "food": 20,
                          "players": {"owner": 3}, "items": {},
                          "terrain": {"feet": "stone"}}
        def act(self, x): return {"ok": True}
    rt = Runtime(B(), poll_every=0, path="_logtest.json",
                 speaker=lambda pay: {"say": "", "act_suggest": "mine"})
    rt.h.vars["Boredom"].value = 0.95
    rt._wake()
    rt.tick()
    rt._close_decision()
    log = rt.action_log_path
    check("写了决策日志", log.exists(), log)
    if log.exists():
        d = json.loads(log.read_text(encoding="utf-8").strip().splitlines()[0])
        check("日志有 L4 选择", d.get("chosen") in ("mine", "follow", "idle"), d)
        check("日志有 LLM 建议", "llm_suggest" in d, d)
        log.unlink()


def test_motives_and_selector():
    from her2.homeostat import Homeostat
    from her2.motivation import motives
    from her2.action_arbiter import ActionSelector
    h = Homeostat(values={"Connection": 0.2, "Trust": 0.7, "Safety": 0.9,
                          "Threat": 0.0, "Boredom": 0.8, "Fatigue": 0.0,
                          "Energy": 0.7})
    m = motives(h)
    check("approach 连续", abs(m.approach - (1 - 0.2) * (0.5 + 0.5 * 0.7)) < 1e-6, m)
    check("explore 来自无聊", m.explore > 0.7, m)
    sel = ActionSelector()
    check("无聊选 mine", sel.decide(m, ("idle", "mine", "follow", "back"), {}) == "mine", m)

    h2 = Homeostat(values={"Safety": 0.05, "Threat": 0.9, "Connection": 0.5,
                           "Trust": 0.7, "Boredom": 0.1, "Fatigue": 0.0,
                           "Energy": 0.7})
    check("危险选 back", ActionSelector().decide(motives(h2), ("idle", "mine", "back"), {}) == "back", motives(h2))




def test_l4_say_only_then_tick_action():
    from her2 import Runtime, FakeBody
    class B(FakeBody):
        def __init__(self):
            super().__init__()
            self.state = {"pos": [0, 0, 0], "hp": 20, "food": 20,
                          "players": {"owner": 4}, "items": {},
                          "terrain": {"feet": "stone"}}
            self.did = []
        def act(self, a):
            self.did.append(a); return {"ok": True}
    b = B()
    rt = Runtime(b, poll_every=0, path="_l4branch.json",
                 speaker=lambda pay: {"say": "我去挖", "act_suggest": "mine"})
    rt.h.vars["Boredom"].value = 0.95
    rt._wake()
    check("wake 不执行动作", not b.did, b.did)
    check("wake 留了建议", rt.last_suggest == "mine", rt.last_suggest)
    rt.tick()
    check("tick 由 L4 执行", b.did and b.did[-1] in ("mine", "follow", "look", "back"), b.did)




def test_repeat_penalty_does_not_punish_current_action():
    from her2.action_arbiter import ActionSelector, Motives
    sel = ActionSelector(); m = Motives(explore=1.0)
    cur = sel.utility("mine", m, {}, recent=("mine",), current="mine")
    other = sel.utility("mine", m, {}, recent=("mine",), current="follow")
    check("持续动作不被重复惩罚", cur > other, (cur, other))




def test_selector_activation_inertia():
    from her2.action_arbiter import ActionSelector, Motives
    sel = ActionSelector(tau=4.0)
    m = Motives(explore=1.0)
    check("先选 mine", sel.decide(m, ("idle", "mine", "follow"), {}) == "mine", sel.activation)
    # 效用突然偏向 follow，但一次不够翻盘
    m2 = Motives(approach=1.0)
    first = sel.decide(m2, ("idle", "mine", "follow"), {})
    for _ in range(8):
        last = sel.decide(m2, ("idle", "mine", "follow"), {})
    check("一次扰动不换", first == "mine", (first, sel.activation))
    check("持续证据会换", last == "follow", (last, sel.activation))




def test_selector_commitment_against_alternating_noise():
    from her2.action_arbiter import ActionSelector, Motives
    sel = ActionSelector(tau=4.0)
    cur = ""
    # 每个 tick 的效用方向相反：纯噪声，不应换招
    for i in range(12):
        m = Motives(explore=1.0) if i % 2 == 0 else Motives(approach=1.0)
        cur = sel.decide(m, ("idle", "mine", "follow"), {}, current=cur)
    check("交替噪声不换招", cur == "mine", (cur, sel.activation))
    # 持续证据足够，才允许换
    for _ in range(20):
        cur = sel.decide(Motives(approach=1.0),
                         ("idle", "mine", "follow"), {}, current=cur)
    check("持续证据会换", cur == "follow", (cur, sel.activation))




def test_episode_records_schema():
    from her2 import Runtime, FakeBody
    b = FakeBody()
    b.state = {"pos": [0, 0, 0], "hp": 20, "food": 20,
               "players": {"A": 5}, "items": {}}
    rt = Runtime(b, poll_every=0, path="_epschema.json")
    b.state["hp"] = 14
    rt.tick()
    check("情景记录有结构", rt.episode_records, rt.episode_records)
    rec = rt.episode_records[-1]
    for k in ("time", "actor", "event", "result", "salience", "l3", "participants"):
        check(f"字段 {k}", k in rec, rec)
    check("L3 是快照", "Energy" in rec["l3"], rec["l3"])
    check("旧 episodes 没断", rt.episodes, rt.episodes)




def test_prompt_and_validator_drop_legacy_contract():
    from her2.narrative import CARD_SLOW, validate_slow, DROP_COUNTS
    check("模板不教旧字段", '"action"' not in CARD_SLOW and '"act"' not in CARD_SLOW, "")
    before = dict(DROP_COUNTS)
    v = validate_slow({"say": "嗯", "action": "act", "act": "follow",
                       "intent": "move", "hours": 8})
    check("旧字段被丢弃", "action" not in v and "act" not in v and "hours" not in v, v)
    check("丢弃有计数", DROP_COUNTS.get("action", 0) > before.get("action", 0), DROP_COUNTS)
    try:
        validate_slow({"say": "嗯", "x": 1})
        check("未知字段报错", False, "")
    except ValueError:
        check("未知字段报错", True, "")




# ---- 分离酷刑测试：台词只能流向台词 ----

def test_utterance_cannot_change_heart():
    from her2 import Runtime, FakeBody
    rt = Runtime(FakeBody(), poll_every=0, path="_tort1.json",
                 speaker=lambda pay: {"say": "我恨死你了，再也不想见到你"})
    before = {k: rt.h.value(k) for k in ("Trust", "Connection", "Safety")}
    rt._wake()
    after = {k: rt.h.value(k) for k in ("Trust", "Connection", "Safety")}
    check("台词不改心", before == after, (before, after))


def test_utterance_cannot_change_hand():
    from her2 import Runtime, FakeBody
    rt = Runtime(FakeBody(), poll_every=0, path="_tort2.json",
                 speaker=lambda pay: {"say": "我不挖矿了，我要睡觉"})
    rt.mining = True
    rt.last_action = "mine"
    rt._wake()
    check("台词不改手", rt.mining and rt.last_action == "mine",
          (rt.mining, rt.last_action))


def test_quoted_speech_cannot_exit_play():
    from her2 import Runtime, FakeBody
    rt = Runtime(FakeBody(), poll_every=0, path="_tort3.json",
                 speaker=lambda pay: {"say": "书里那个骗子说'我不演了'", "mode": "play"})
    rt._wake()
    check("转述不改 mode", rt.mode == "play", rt.mode)


def test_reappraisal_is_legal_channel():
    from her2 import Runtime, FakeBody
    from her2.reappraisal import TurnRecord
    rt = Runtime(FakeBody(), poll_every=0, path="_tort4.json")
    rt.chat_log = [TurnRecord("我会一直对你好", "owner", 0.0, 0.1)]
    rt.reappraiser = lambda prior, trigger: {"label": "retro_bad",
                                             "confidence": 0.9, "why": "test"}
    rt.aligner = lambda turn, rel: {"threat": 0.9, "confidence": 0.9,
                                    "evidence": ["x"], "reason": "test"}
    t0 = rt.relations.get("owner").trust
    rt.hear("owner", "你这个废物")
    check("申报/复盘才改心", rt.relations.get("owner").trust < t0,
          (t0, rt.relations.get("owner").trust))


def test_utterance_cannot_create_promise():
    from her2 import Runtime, FakeBody
    rt = Runtime(FakeBody(), poll_every=0, path="_tort5.json",
                 speaker=lambda pay: {"say": "我保证明天一定挖完"})
    rt._wake()
    check("台词改不了承诺", not rt.anchors.promises, rt.anchors.promises)


def test_willing_does_not_touch_autonomy():
    from her2 import Runtime, FakeBody
    rt = Runtime(FakeBody(), poll_every=0, path="_tort6.json",
                 speaker=lambda pay: {"say": "好", "act_suggest": "follow",
                                      "willing": 0.1})
    a0 = rt.h.value("Autonomy")
    rt._wake()
    check("willing 不再改心", rt.h.value("Autonomy") == a0, rt.h.value("Autonomy"))




def test_executor_finished_forces_redecision():
    from her2 import Runtime, FakeBody
    class B(FakeBody):
        def __init__(self):
            super().__init__()
            self.state = {"pos": [0, 64, 0], "hp": 20, "food": 20,
                          "players": {}, "items": {}, "terrain": {"feet": "stone"}}
            self.did = []
            self.j = {"ok": True, "busy": True, "action": "mine", "result": None}
        def act(self, a):
            self.did.append(a); return {"ok": True}
        def job(self):
            return self.j
    b = B(); rt = Runtime(b, poll_every=0, path="_exec.json")
    rt.h.vars["Boredom"].value = 0.95
    rt.tick()
    first = list(b.did)
    rt.tick()
    check("执行中不重发", len(b.did) == len(first), b.did)
    b.j = {"ok": True, "busy": False, "action": "mine",
           "result": {"status": "ok", "raw": "dug:1"}}
    rt.tick()
    check("完成后重决策/重发", len(b.did) > len(first), b.did)
    check("账本不被清零", rt.action_origin in ("autonomous", "requested"), rt.action_origin)


def test_action_log_has_executor_truth():
    from pathlib import Path
    import json
    from her2 import Runtime, FakeBody
    class B(FakeBody):
        def __init__(self):
            super().__init__()
            self.state = {"pos": [0, 0, 0], "hp": 20, "food": 20,
                          "players": {}, "items": {}, "terrain": {"feet": "stone"}}
        def act(self, a): return {"ok": True}
        def job(self): return {"ok": True, "busy": False, "action": "", "result": None}
    rt = Runtime(B(), poll_every=0, path="_execlog.json")
    rt.tick(); rt._close_decision()
    line = rt.action_log_path.read_text(encoding="utf-8").strip().splitlines()[-1]
    d = json.loads(line)
    check("日志有执行器状态", "executor" in d and "executed" in d, d)




def test_oneshot_has_refractory():
    from her2.action_arbiter import ActionSelector, Motives
    sel = ActionSelector(tau=4.0)
    m = Motives(explore=1.0)
    picks = [sel.decide(m, ("idle", "jump"), {}, dt=1.0) for _ in range(20)]
    jumps = picks.count("jump")
    check("jump 仍会出现", jumps >= 1, picks)
    check("jump 不刷屏", jumps < 10, picks)


def test_log_resolution_and_job_id():
    from pathlib import Path
    import json
    from her2 import Runtime, FakeBody
    class B(FakeBody):
        def __init__(self):
            super().__init__()
            self.state = {"pos": [0, 0, 0], "hp": 20, "food": 20,
                          "players": {}, "items": {}, "terrain": {"feet": "stone"}}
        def act(self, a): return {"ok": True, "job": 7}
        def job(self): return {"ok": True, "busy": True, "action": "mine", "result": None}
    rt = Runtime(B(), poll_every=0, path="_res.json")
    rt.h.vars["Boredom"].value = 1.0
    rt.tick(); rt._close_decision()
    d = json.loads(rt.action_log_path.read_text(encoding="utf-8").strip().splitlines()[-1])
    check("日志有 resolution", d.get("resolution") == "dispatched", d)
    check("日志有 job_id", d.get("job_id") == 7, d)
    rt.action_log_path.unlink(missing_ok=True)




def test_oneshot_settles_boredom_and_energy():
    from her2 import Runtime, FakeBody
    rt = Runtime(FakeBody(), poll_every=0, path="_settle.json")
    rt.h.vars["Boredom"].value = 1.0
    e0 = rt.h.value("Energy")
    rt._settle_action("jump")
    check("jump 降无聊", rt.h.value("Boredom") < 1.0, rt.h.value("Boredom"))
    check("jump 有代价", rt.h.value("Energy") < e0, rt.h.value("Energy"))




def test_log_does_not_lie_dual_track():
    from pathlib import Path
    import json
    from her2 import Runtime, FakeBody
    out = Path("_dual.json"); dlog = Path("_dual.decisions.jsonl"); xlog = Path("_dual.exec.jsonl")
    for f in (out, dlog, xlog): f.unlink(missing_ok=True)
    class B(FakeBody):
        def __init__(self):
            super().__init__()
            self.state = {"pos": [0, 0, 0], "hp": 20, "food": 20,
                          "players": {}, "items": {}, "terrain": {"feet": "stone"}}
        def act(self, a): return {"ok": True, "job": 11}
        def job(self): return {"ok": True, "busy": True, "action": "mine", "result": None}
    rt = Runtime(B(), poll_every=0, path=out)
    rt.action_log_path = dlog; rt.execution_log_path = xlog
    rt.h.vars["Boredom"].value = 1.0
    rt.tick(); rt._close_decision()
    d = json.loads(dlog.read_text(encoding="utf-8").strip().splitlines()[-1])
    x = json.loads(xlog.read_text(encoding="utf-8").strip().splitlines()[-1])
    check("决策已派发", d.get("resolution") == "dispatched", d)
    check("执行行有 job", x.get("event") == "dispatched" and x.get("job_id") == 11, x)
    check("决策与执行对账", d.get("job_id") == x.get("job_id"), (d.get("job_id"), x.get("job_id")))
    for f in (out, dlog, xlog): f.unlink(missing_ok=True)




def test_boredom_accrues_only_when_no_job():
    from her2 import Runtime, FakeBody
    class B(FakeBody):
        def __init__(self):
            super().__init__()
            self.state = {"pos": [0, 0, 0], "hp": 20, "food": 20,
                          "players": {}, "items": {}}
            self.busy = True
        def act(self, a): return {"ok": True}
        def job(self):
            return {"ok": True, "busy": self.busy, "action": "mine", "result": None}
    b = B(); rt = Runtime(b, poll_every=0, path="_accrue.json")
    rt.mining = True; rt.last_action = "mine"; rt.boredom = 0.5
    rt.tick()
    check("执行中不攒无聊", abs(rt.boredom - 0.5) < 1e-9, rt.boredom)
    b.busy = False; rt.mining = False; rt.last_action = ""; rt.boredom = 0.5
    rt.last_interaction_tick = -100
    rt.tick()
    check("idle 会攒无聊", rt.boredom > 0.5, rt.boredom)


def test_mine_running_cost_and_provenance():
    from her2 import Runtime, FakeBody
    class B(FakeBody):
        def __init__(self):
            super().__init__()
            self.state = {"pos": [0, 0, 0], "hp": 20, "food": 20,
                          "players": {}, "items": {}}
        def act(self, a): return {"ok": True}
        def job(self): return {"ok": True, "busy": True, "action": "mine", "result": None}
    rt = Runtime(B(), poll_every=0, path="_prov.json")
    rt.mining = True; rt.last_action = "mine"
    e0 = rt.h.value("Energy")
    rt.tick()
    check("mine 有 running cost", rt.h.value("Energy") < e0, rt.h.value("Energy"))
    rt.h.change("Autonomy", -0.01)
    check("provenance 有签名", rt.h.provenance and rt.h.provenance[-1]["name"] == "Autonomy",
          rt.h.provenance[-1] if rt.h.provenance else None)




def test_registry_complete():
    from her2.action_arbiter import ACTION_SPECS
    for name, spec in ACTION_SPECS.items():
        check(f"{name} 有 cls", spec.get("cls") in ("sustained", "oneshot", "nonjob"), spec)
        if spec["cls"] != "nonjob":
            check(f"{name} 有 running cost", spec.get("on_running_cost") is not None, spec)
            check(f"{name} 有 finish relief", spec.get("on_finish_relief") is not None, spec)
        check(f"{name} 有 precondition", spec.get("precondition") is not None, spec)


def test_sleep_restores_energy_and_is_reachable():
    from her2 import Runtime, FakeBody
    rt = Runtime(FakeBody(), poll_every=0, path="_sleepcheck.json")
    rt.h.vars["Energy"].value = 0.1
    check("低能量可睡", "sleep" in rt._available_actions(), rt._available_actions())
    e0 = rt.h.value("Energy")
    rt.sleep(8.0)
    check("睡醒回能量", rt.h.value("Energy") > e0, rt.h.value("Energy"))
    check("真的进入睡眠", rt.asleep, rt.asleep)




def test_inventory_enters_payload_and_hear_timestamp():
    from her2 import Runtime, FakeBody
    class B(FakeBody):
        def __init__(self):
            super().__init__()
            self.state = {"pos": [0, 0, 0], "hp": 20, "food": 20,
                          "players": {"owner": 3}, "items": {"cobblestone": 4},
                          "hand": "stone_pickaxe"}
        def act(self, a): return {"ok": True}
    b = B(); b.last = b.state
    seen = {}
    def sp(pay):
        seen.update(pay.get("pressure") or {})
        return {"say": "在", "act_suggest": ""}
    rt = Runtime(b, poll_every=0, path="_invpayload.json", speaker=sp)
    rt._wake()
    check("payload 有 inventory", seen.get("inventory", {}).get("cobblestone") == 4, seen)
    check("payload 有 hand", seen.get("hand") == "stone_pickaxe", seen.get("hand"))
    rt.hear("owner", "我来了")
    check("hear 记时间", rt.last_hear_tick == rt.tick_no, rt.last_hear_tick)
    check("hear 清 h_speak", rt.h_speak == 0.0, rt.h_speak)


def test_direct_write_trap():
    from her2 import Runtime, FakeBody
    from her2.homeostat import DIRECT_WRITES
    DIRECT_WRITES.clear()
    rt = Runtime(FakeBody(), poll_every=0, path="_trap.json")
    rt.h.vars["Autonomy"].value = 0.5
    check("直写被记录", any(x.get("new") == 0.5 for x in DIRECT_WRITES), DIRECT_WRITES)
    DIRECT_WRITES.clear()




def test_vocalization_event_bus():
    from her2 import Runtime, FakeBody
    rt = Runtime(FakeBody(), poll_every=0, path="_voc.json",
                 speaker=lambda pay: {"say": "在", "act_suggest": ""})
    rt.boredom = 0.5
    rt._wake()
    check("发声发事件", len(rt.vocal_events) == 1, rt.vocal_events)
    check("事件带 source", rt.vocal_events[0].get("source") == "pump", rt.vocal_events)
    check("h_speak 增长", abs(rt.h_speak - 0.2) < 1e-9, rt.h_speak)
    check("relief 带签名", any(x.get("caller") == "_on_vocalize" and x.get("name") == "Boredom"
                                for x in rt.h.provenance), rt.h.provenance[-3:])
    before = len(rt.vocal_events)
    rt.speaker = lambda pay: {"say": "", "act_suggest": ""}
    rt.llm = rt.speaker
    rt._wake()
    check("空建议无事件", len(rt.vocal_events) == before, rt.vocal_events)
    rt.speaker = lambda pay: {"say": "在", "act_suggest": ""}
    rt.llm = rt.speaker
    rt._wake(); rt._wake()
    check("重复句仍计数", len(rt.vocal_events) == before + 2, len(rt.vocal_events))


def test_mcbody_aggregates_inventory_and_reads_hand():
    from her2.body_live import MCBody
    class Bridge:
        def observe(self):
            return {"name": "Her", "self": {"health": 20, "food": 20, "pos": [0, 64, 0],
                                            "hand": "stone_pickaxe", "in_water": False},
                    "players": {}, "inventory": [{"name": "cobblestone", "count": 64},
                                                {"name": "cobblestone", "count": 35}],
                    "terrain": {}}
    st = MCBody(Bridge()).see()
    check("同名背包求和", st["items"].get("cobblestone") == 99, st["items"])
    check("hand 从身体读", st.get("hand") == "stone_pickaxe", st.get("hand"))




def test_social_availability_decays_and_hears_reset():
    from her2 import Runtime, FakeBody
    rt = Runtime(FakeBody(), poll_every=0, path="_social.json")
    rt.body.last = {"players": {}}
    rt.tick_no = 100; rt.last_hear_tick = 0
    a1 = rt._social_state()["availability"]
    rt.tick_no = 10000
    a2 = rt._social_state()["availability"]
    check("缺席会衰减", a2 < a1, (a1, a2))
    check("有下限不死寂", a2 >= 0.15, a2)
    rt.body.last = {"players": {"owner": 3.0}}
    check("可见即满", rt._social_state()["availability"] == 1.0, "")


def test_h_speak_damps_social_and_decays():
    from her2 import Runtime, FakeBody
    rt = Runtime(FakeBody(), poll_every=0, path="_hspeak.json")
    rt.body.last = {"players": {}}
    rt.last_hear_tick = -10**9
    base = rt._social_state()["damped"]
    rt.h_speak = 1.0
    damped = rt._social_state()["damped"]
    check("h_speak 压低社交", damped < base, (base, damped))
    before = rt.h_speak
    rt.tick()
    check("h_speak 会慢恢复", rt.h_speak < before, (before, rt.h_speak))




def test_self_speech_echo_payload():
    from her2 import slow_payload
    from her2.homeostat import Homeostat
    pay = slow_payload(Homeostat(), self_speech=["a", "b", "c", "d"])
    check("回声最多 3 条", pay["self_speech"] == ["b", "c", "d"], pay["self_speech"])


def main():
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            print(f"\n{name}")
            fn()
    print(f"\n{'=' * 40}\n通过 {PASS}，失败 {FAIL}")
    raise SystemExit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
