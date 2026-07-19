# -*- coding: utf-8 -*-
"""Discord 推送：把当日 Top 信号以 Embed 富文本卡片发到 Webhook。

- 仅在环境变量 DISCORD_WEBHOOK_URL 存在时才推送，缺失则静默跳过；
- 按信号方向着色（红涨绿跌，符合国内习惯）；
- 推送失败不抛异常、不中断主流程。
"""
import os
import json
import urllib.request

# 颜色用十进制（Discord embed 要求）：红=偏多，绿=偏空
COLOR_BULL = 0xE23B3B     # 红
COLOR_BEAR = 0x18A058     # 绿
COLOR_FLAT = 0x8A8F99     # 灰


def _post_json(url, payload, timeout=10):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status


def build_embed(result):
    """把汇总结果拼成一个 Discord Embed 卡片。"""
    s = result["summary"]
    color = COLOR_BULL if len(s["top_bull"]) >= len(s["top_bear"]) else COLOR_BEAR
    fields = []
    if s["top_bull"]:
        fields.append({
            "name": "🔴 偏多 Top",
            "value": "\n".join(f"{x['name']}（{x['rec']} {x['score']:+d}）" for x in s["top_bull"]),
            "inline": True,
        })
    if s["top_bear"]:
        fields.append({
            "name": "🟢 偏空 Top",
            "value": "\n".join(f"{x['name']}（{x['rec']} {x['score']:+d}）" for x in s["top_bear"]),
            "inline": True,
        })
    return {
        "embeds": [{
            "title": "📈 AI 股票分析日报",
            "description": (f"{s['date']} · 共 {s['total']} 只 · 真实行情 {s['live_count']} 只\n"
                            f"买入 {s['buy_count']} / 卖出 {s['sell_count']} / 观望 {s['hold_count']}"),
            "color": color,
            "fields": fields,
            "footer": {"text": "⚠️ 仅供学习，不构成投资建议 · " + s["generated_at"]},
        }]
    }


def notify(result):
    """存在 DISCORD_WEBHOOK_URL 时推送，返回是否成功。"""
    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not url:
        return False
    try:
        _post_json(url, build_embed(result))
        print("==> Discord 已推送")
        return True
    except Exception as e:
        print("Discord 推送失败:", e)
        return False
