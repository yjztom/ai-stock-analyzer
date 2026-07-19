# -*- coding: utf-8 -*-
"""买卖点信号：把 7 大技术指标「翻译」成中文理由 + 一个多空评分。

设计原则（面向新手、严守合规）：
- 每条信号都给一句中文理由，方便学习；绝不预测涨跌；
- 多空评分 score 越大越偏多；所有结论都是对「当前技术形态」的客观描述，
  不是买卖操作指令；
- 指标参数从 config/indicators_config.json 传入（cfg），改配置即可调参。
"""
import indicators as ind


def _golden_cross(a, b):
    """快线 a 上穿慢线 b（金叉）。需要最近两天都不为 None。"""
    if None in (a[-1], b[-1], a[-2], b[-2]):
        return False
    return a[-1] > b[-1] and a[-2] <= b[-2]


def _death_cross(a, b):
    """快线 a 下穿慢线 b（死叉）。"""
    if None in (a[-1], b[-1], a[-2], b[-2]):
        return False
    return a[-1] < b[-1] and a[-2] >= b[-2]


def evaluate(closes, highs, lows, volumes, cfg=None):
    """输入 OHLCV（从旧到新），返回该标的的信号字典。

    cfg 为 indicators_config.json 解析后的 dict；为 None 时用内置默认值。
    """
    cfg = cfg or {}
    c_ma = cfg.get("ma", {})
    c_macd = cfg.get("macd", {})
    c_rsi = cfg.get("rsi", {})
    c_boll = cfg.get("boll", {})
    c_kdj = cfg.get("kdj", {})
    c_vol = cfg.get("volume", {})

    ma_short = c_ma.get("short", 5)
    ma_mid = c_ma.get("mid", 20)
    ma_long = c_ma.get("long", 60)
    rsi_ob = c_rsi.get("overbought", 70)
    rsi_os = c_rsi.get("oversold", 30)
    kdj_ob = c_kdj.get("overbought", 80)
    kdj_os = c_kdj.get("oversold", 20)
    vol_spike = c_vol.get("spike_ratio", 1.5)

    # ---- 计算全部指标 ----
    macd_line, signal_line, hist = ind.macd(
        closes, c_macd.get("fast", 12), c_macd.get("slow", 26), c_macd.get("signal", 9))
    rsi_vals = ind.rsi(closes, c_rsi.get("period", 14))
    upper, mid, lower = ind.bollinger(
        closes, c_boll.get("period", 20), c_boll.get("std_k", 2.0))
    K, D, J = ind.kdj(
        closes, highs, lows, c_kdj.get("period", 9),
        c_kdj.get("k_smooth", 3), c_kdj.get("d_smooth", 3))
    ma5 = ind.sma(closes, ma_short)
    ma20 = ind.sma(closes, ma_mid)
    ma60 = ind.sma(closes, ma_long)
    vol_ma = ind.sma(volumes, c_vol.get("ma_period", 20))

    score = 0
    reasons = []                       # 每条: {"text": 理由, "side": "bull"/"bear"}
    price = closes[-1]
    prev_price = closes[-2] if len(closes) > 1 else price

    # 1) MACD 金叉 / 死叉（权重最大 ±2）
    if _golden_cross(macd_line, signal_line):
        score += 2
        reasons.append({"text": "MACD 金叉（快线上穿慢线），短期动能转强", "side": "bull"})
    elif _death_cross(macd_line, signal_line):
        score -= 2
        reasons.append({"text": "MACD 死叉（快线下穿慢线），短期动能转弱", "side": "bear"})

    # 2) RSI 超买 / 超卖（±1）
    r = rsi_vals[-1]
    if r is not None:
        if r < rsi_os:
            score += 1
            reasons.append({"text": f"RSI={r:.0f} 进入超卖区(<{rsi_os})，可能有反弹机会", "side": "bull"})
        elif r > rsi_ob:
            score -= 1
            reasons.append({"text": f"RSI={r:.0f} 进入超买区(>{rsi_ob})，注意回落风险", "side": "bear"})

    # 3) 布林带触碰（±1）
    if (lower[-1] is not None and lower[-2] is not None
            and prev_price >= lower[-2] and price < lower[-1]):
        score += 1
        reasons.append({"text": "价格跌破布林下轨，短期或超跌", "side": "bull"})
    elif (upper[-1] is not None and upper[-2] is not None
            and prev_price <= upper[-2] and price > upper[-1]):
        score -= 1
        reasons.append({"text": "价格突破布林上轨，短期或超买", "side": "bear"})

    # 4) 均线多头/空头排列（±1）—— MA5>MA20>MA60 为多头
    if None not in (ma5[-1], ma20[-1], ma60[-1]):
        if ma5[-1] > ma20[-1] > ma60[-1]:
            score += 1
            reasons.append({"text": "均线多头排列（MA5>MA20>MA60），中期趋势偏多", "side": "bull"})
        elif ma5[-1] < ma20[-1] < ma60[-1]:
            score -= 1
            reasons.append({"text": "均线空头排列（MA5<MA20<MA60），中期趋势偏空", "side": "bear"})

    # 5) MA20 / MA60 金叉死叉（±1）
    if _golden_cross(ma20, ma60):
        score += 1
        reasons.append({"text": "MA20 上穿 MA60（均线金叉）", "side": "bull"})
    elif _death_cross(ma20, ma60):
        score -= 1
        reasons.append({"text": "MA20 下穿 MA60（均线死叉）", "side": "bear"})

    # 6) KDJ（±1）—— 低位金叉/J<0 偏多；高位死叉/J>100 偏空
    if None not in (K[-1], D[-1], K[-2], D[-2]):
        low_zone = K[-1] < kdj_ob and D[-1] < kdj_ob
        high_zone = K[-1] > kdj_ob and D[-1] > kdj_ob
        if _golden_cross(K, D) and (K[-1] < 50 or low_zone):
            score += 1
            reasons.append({"text": "KDJ 低位金叉（K 上穿 D），短线或转强", "side": "bull"})
        elif _death_cross(K, D) and high_zone:
            score -= 1
            reasons.append({"text": "KDJ 高位死叉（K 下穿 D），短线或转弱", "side": "bear"})
        elif J[-1] is not None and J[-1] < 0:
            score += 1
            reasons.append({"text": f"KDJ 的 J={J[-1]:.0f}<0，极度超卖", "side": "bull"})
        elif J[-1] is not None and J[-1] > 100:
            score -= 1
            reasons.append({"text": f"KDJ 的 J={J[-1]:.0f}>100，极度超买", "side": "bear"})

    # 7) 成交量确认（±1）—— 放量上涨偏多，放量下跌偏空
    if vol_ma[-1] is not None and volumes[-1] > vol_spike * vol_ma[-1]:
        if price >= prev_price:
            score += 1
            reasons.append({"text": "放量上涨，资金参与度提升", "side": "bull"})
        else:
            score -= 1
            reasons.append({"text": "放量下跌，抛压加重", "side": "bear"})

    rec = _recommend(score)
    return {
        "score": score,
        "recommendation": rec["label"],
        "recommendation_level": rec["level"],
        "rsi": None if r is None else round(r, 1),
        "macd_hist": None if hist[-1] is None else round(hist[-1], 4),
        "k": None if K[-1] is None else round(K[-1], 1),
        "d": None if D[-1] is None else round(D[-1], 1),
        "j": None if J[-1] is None else round(J[-1], 1),
        "ma5": None if ma5[-1] is None else round(ma5[-1], 2),
        "ma20": None if ma20[-1] is None else round(ma20[-1], 2),
        "ma60": None if ma60[-1] is None else round(ma60[-1], 2),
        "upper": None if upper[-1] is None else round(upper[-1], 2),
        "lower": None if lower[-1] is None else round(lower[-1], 2),
        "reasons": reasons,
        "bull_count": sum(1 for x in reasons if x["side"] == "bull"),
        "bear_count": sum(1 for x in reasons if x["side"] == "bear"),
    }


def _recommend(score):
    """把评分映射成 7 档「形态描述」（不是操作指令）。

    强烈买入 → 买入 → 谨慎买入 → 观望 → 谨慎卖出 → 卖出 → 强烈卖出
    """
    if score >= 5:
        return {"label": "强烈买入", "level": "strong_buy"}
    if score >= 3:
        return {"label": "买入", "level": "buy"}
    if score >= 1:
        return {"label": "谨慎买入", "level": "weak_buy"}
    if score <= -5:
        return {"label": "强烈卖出", "level": "strong_sell"}
    if score <= -3:
        return {"label": "卖出", "level": "sell"}
    if score <= -1:
        return {"label": "谨慎卖出", "level": "weak_sell"}
    return {"label": "观望", "level": "hold"}
