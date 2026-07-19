# -*- coding: utf-8 -*-
"""多市场行情获取（零依赖，优先 Yahoo Finance 公开接口，失败回退仿真）。

为什么用 Yahoo 一个源通吃三大市场？
- 无需密钥、覆盖美股/港股/A股，symbol 规则统一（见下）；
- 在 GitHub Actions（海外服务器）上比 AkShare 稳定，且免 pip 安装。
若某些 IP 被限流，会自动回退「仿真数据」并标注 live=False，保证流程不中断。

symbol 规则：
- 美股： AAPL、NVDA
- 港股： 0700.HK、9988.HK
- A股：  600519.SS（沪）、000001.SZ（深）

可选增强：若想改用 yfinance / AkShare，只需替换 fetch_ohlcv 的实现，
上层 analyze_stocks.py 不用改（返回结构保持一致）。
"""
import json
import datetime
import urllib.request
import urllib.error

YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
UA = {"User-Agent": "Mozilla/5.0 (compatible; ai-stock-analyzer/1.0)"}


def fetch_ohlcv(symbol, rng="6mo", interval="1d", timeout=12, days=120):
    """返回 dict: {live, symbol, currency, dates, opens, highs, lows, closes, volumes}。

    live=True 抓到真实行情；live=False 表示网络不可用，返回仿真数据（明显标注）。
    """
    try:
        url = YAHOO.format(symbol=symbol) + f"?range={rng}&interval={interval}&events=div"
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
        res = data["chart"]["result"][0]
        ts = res["timestamp"]
        q = res["indicators"]["quote"][0]
        closes = q["close"]
        opens = q["open"]
        highs = q["high"]
        lows = q["low"]
        volumes = q["volume"]
        dates = [datetime.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d") for t in ts]
        # 去掉 close 为 None 的行（停牌/未收盘），保证四价与量对齐干净
        idx = [i for i, c in enumerate(closes) if c is not None]
        if not idx:
            raise ValueError("empty series")
        keep = [i for i in idx if None not in (opens[i], highs[i], lows[i], volumes[i])]
        if not keep:
            raise ValueError("no complete rows")
        return {
            "live": True,
            "symbol": symbol,
            "currency": res.get("meta", {}).get("currency", ""),
            "dates": [dates[i] for i in keep],
            "opens": [float(opens[i]) for i in keep],
            "highs": [float(highs[i]) for i in keep],
            "lows": [float(lows[i]) for i in keep],
            "closes": [float(closes[i]) for i in keep],
            "volumes": [float(volumes[i]) for i in keep],
        }
    except Exception:
        return _synthetic(symbol, days)


def _synthetic(symbol, days):
    """网络不可用时，用确定性伪随机生成「看起来真实」的日线（live=False）。

    以 symbol 字符算固定种子，保证同一标的每次结果一致（便于对照与测试）。
    """
    seed = sum((i + 1) * ord(ch) for i, ch in enumerate(symbol)) % (2 ** 31)
    a, c, m = 1664525, 1013904223, 2 ** 32
    s = seed

    def rnd():
        nonlocal s
        s = (a * s + c) % m
        return s / m

    price = 50 + rnd() * 150
    opens, highs, lows, closes, volumes = [], [], [], [], []
    dates = []
    d = datetime.date.today()
    while len(dates) < days:                 # 生成最近 days 个交易日（跳过周末）
        if d.weekday() < 5:
            dates.append(d)
        d = d - datetime.timedelta(days=1)
    dates = dates[::-1]

    for _ in range(days):
        op = price * (1 + (rnd() - 0.5) * 0.02)
        cl = op * (1 + (rnd() - 0.5) * 0.04)
        hi = max(op, cl) * (1 + rnd() * 0.02)
        lo = min(op, cl) * (1 - rnd() * 0.02)
        vol = 1e6 * (0.5 + rnd())
        opens.append(round(op, 2)); closes.append(round(cl, 2))
        highs.append(round(hi, 2)); lows.append(round(lo, 2)); volumes.append(round(vol, 0))
        price = cl

    return {
        "live": False,
        "symbol": symbol,
        "currency": "",
        "dates": [x.isoformat() for x in dates],
        "opens": opens, "highs": highs, "lows": lows,
        "closes": closes, "volumes": volumes,
    }
