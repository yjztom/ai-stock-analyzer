# -*- coding: utf-8 -*-
"""主分析编排：加载配置 -> 多市场取数 -> 算 7 指标/信号 -> 落盘 -> 汇总。

数据落盘分层（对应 data/ 目录）：
- data/raw/<symbol>.json        : 原始 OHLCV
- data/processed/<symbol>.json  : 带信号与关键指标值的处理结果
- data/signals/YYYY-MM-DD.json  : 当日全部信号摘要（按日归档）
展示用产物：
- docs/data.json                : 前端 SPA 读取的最新结果
- docs/reports/YYYY-MM-DD.json  : 按日归档，便于历史追溯

被 main.py 调用；也可直接 `python scripts/analyze_stocks.py` 运行。
"""
import os
import sys
import json
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from data_fetcher import fetch_ohlcv
from signals import evaluate

CONFIG_DIR = os.path.join(ROOT, "config")
DATA_DIR = os.path.join(ROOT, "data")
DOCS_DIR = os.path.join(ROOT, "docs")

MARKET_LABEL = {"US": "美股", "HK": "港股", "SH": "A股(沪)", "SZ": "A股(深)"}


def _load_json(path, default=None):
    """安全读 JSON；文件不存在或损坏时返回 default。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _load_config():
    """读取股票清单与指标参数两份配置。"""
    stocks_cfg = _load_json(os.path.join(CONFIG_DIR, "stocks_config.json"), {})
    ind_cfg = _load_json(os.path.join(CONFIG_DIR, "indicators_config.json"), {})
    stocks = stocks_cfg.get("stocks", [])
    return stocks, ind_cfg


def _write_json(path, obj):
    """确保父目录存在后写 JSON（UTF-8，保留中文）。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def analyze_all(save=True):
    """对清单里每只股票做完整分析，返回 {summary, rows}；save=True 时落盘。"""
    stocks, ind_cfg = _load_config()
    fetch_cfg = ind_cfg.get("fetch", {})
    rng = fetch_cfg.get("range", "6mo")
    interval = fetch_cfg.get("interval", "1d")
    timeout = fetch_cfg.get("timeout_sec", 12)

    today = datetime.date.today().isoformat()
    rows = []

    for item in stocks:
        sym = item["symbol"]
        data = fetch_ohlcv(sym, rng=rng, interval=interval, timeout=timeout)
        closes = data["closes"]
        sig = evaluate(closes, data["highs"], data["lows"], data["volumes"], ind_cfg)

        prev = closes[-2] if len(closes) > 1 else closes[-1]
        change_pct = round((closes[-1] / prev - 1) * 100, 2) if len(closes) > 1 else 0.0
        mkt = item.get("market", "")

        row = {
            "symbol": sym,
            "name": item.get("name", sym),
            "market": mkt,
            "market_label": MARKET_LABEL.get(mkt, mkt),
            "note": item.get("note", ""),
            "live": data["live"],
            "currency": data.get("currency", ""),
            "price": round(closes[-1], 2),
            "prev_close": round(prev, 2),
            "change_pct": change_pct,
            # 只给前端最近 60 个点画迷你走势，减小体积
            "dates": data["dates"][-60:],
            "closes": [round(x, 2) for x in closes[-60:]],
            "volumes": data["volumes"][-60:],
            "signal": sig,
        }
        rows.append(row)

        if save:                                    # data/raw + data/processed 分层落盘
            _write_json(os.path.join(DATA_DIR, "raw", f"{sym}.json"), {
                "symbol": sym, "live": data["live"], "dates": data["dates"],
                "opens": data["opens"], "highs": data["highs"], "lows": data["lows"],
                "closes": data["closes"], "volumes": data["volumes"],
            })
            _write_json(os.path.join(DATA_DIR, "processed", f"{sym}.json"), {
                "symbol": sym, "name": row["name"], "market": mkt,
                "price": row["price"], "change_pct": change_pct, "signal": sig,
            })

    # ---- 汇总：按信号强度排出偏多/偏空 TOP ----
    buy_levels = ("strong_buy", "buy", "weak_buy")
    sell_levels = ("strong_sell", "sell", "weak_sell")
    bull = [r for r in rows if r["signal"]["recommendation_level"] in buy_levels]
    bear = [r for r in rows if r["signal"]["recommendation_level"] in sell_levels]
    bull.sort(key=lambda r: r["signal"]["score"], reverse=True)
    bear.sort(key=lambda r: r["signal"]["score"])

    summary = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "date": today,
        "total": len(rows),
        "live_count": sum(1 for r in rows if r["live"]),
        "buy_count": len(bull),
        "sell_count": len(bear),
        "hold_count": sum(1 for r in rows if r["signal"]["recommendation_level"] == "hold"),
        "top_bull": [
            {"name": r["name"], "symbol": r["symbol"], "score": r["signal"]["score"],
             "rec": r["signal"]["recommendation"]} for r in bull[:5]
        ],
        "top_bear": [
            {"name": r["name"], "symbol": r["symbol"], "score": r["signal"]["score"],
             "rec": r["signal"]["recommendation"]} for r in bear[:5]
        ],
    }
    result = {"summary": summary, "rows": rows}

    if save:
        # 前端读取的最新结果
        _write_json(os.path.join(DOCS_DIR, "data.json"), result)
        # 按日归档（signals 摘要 + docs/reports 全量）
        _write_json(os.path.join(DATA_DIR, "signals", f"{today}.json"), summary)
        _write_json(os.path.join(DOCS_DIR, "reports", f"{today}.json"), result)

    return result


if __name__ == "__main__":
    res = analyze_all(save=True)
    s = res["summary"]
    print(f"分析完成：{s['total']} 只 | 真实行情 {s['live_count']} | "
          f"买入 {s['buy_count']} / 卖出 {s['sell_count']} / 观望 {s['hold_count']}")
