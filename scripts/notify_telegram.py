# -*- coding: utf-8 -*-
"""Telegram 推送：通过 Bot 向指定 chat_id 发 Markdown 消息。

- 需要环境变量 TELEGRAM_BOT_TOKEN 与 TELEGRAM_CHAT_ID，缺任一则静默跳过；
- 推送失败不抛异常、不中断主流程。
"""
import os
import json
import urllib.request

API = "https://api.telegram.org/bot{token}/sendMessage"


def _post_json(url, payload, timeout=10):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status


def build_text(result):
    """拼成 Telegram Markdown 文本。"""
    s = result["summary"]
    lines = [f"*📈 AI 股票分析日报*  `{s['date']}`",
             f"共 {s['total']} 只 · 真实行情 {s['live_count']} 只",
             f"买入 {s['buy_count']} / 卖出 {s['sell_count']} / 观望 {s['hold_count']}"]
    if s["top_bull"]:
        lines.append("\n🔴 *偏多 Top*")
        lines += [f"• {x['name']}（{x['rec']} {x['score']:+d}）" for x in s["top_bull"]]
    if s["top_bear"]:
        lines.append("\n🟢 *偏空 Top*")
        lines += [f"• {x['name']}（{x['rec']} {x['score']:+d}）" for x in s["top_bear"]]
    lines.append("\n⚠️ _仅供学习，不构成投资建议_")
    return "\n".join(lines)


def notify(result):
    """存在 token+chat_id 时推送，返回是否成功。"""
    tok = os.environ.get("TELEGRAM_BOT_TOKEN")
    cid = os.environ.get("TELEGRAM_CHAT_ID")
    if not (tok and cid):
        return False
    try:
        _post_json(API.format(token=tok), {
            "chat_id": cid,
            "text": build_text(result),
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        })
        print("==> Telegram 已推送")
        return True
    except Exception as e:
        print("Telegram 推送失败:", e)
        return False
