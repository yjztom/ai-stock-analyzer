# -*- coding: utf-8 -*-
"""项目主入口：跑完整分析并按需推送通知。

用法：
    python main.py            # 分析 + 落盘 + 推送（若配了 Secrets）
    python main.py --no-notify # 只分析落盘，不推送

本地想测推送：把 config/secrets.example.json 复制成 config/secrets.local.json
并填入真实值即可（该文件已被 .gitignore 忽略，不会入库）。
"""
import os
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import analyze_stocks
import notify_discord
import notify_telegram


def _load_local_secrets():
    """若存在 config/secrets.local.json，把其中的键注入环境变量（方便本地调试）。"""
    path = os.path.join(HERE, "config", "secrets.local.json")
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k, v in data.items():
            if k.startswith("_"):
                continue
            os.environ.setdefault(k, str(v))
        print("已加载本地 secrets.local.json")
    except Exception as e:
        print("读取 secrets.local.json 失败（忽略）:", e)


def main():
    no_notify = "--no-notify" in sys.argv
    _load_local_secrets()

    print("开始分析 ...")
    result = analyze_stocks.analyze_all(save=True)
    s = result["summary"]
    print(f"分析完成：{s['total']} 只 | 真实行情 {s['live_count']} | "
          f"买入 {s['buy_count']} / 卖出 {s['sell_count']} / 观望 {s['hold_count']}")

    if no_notify:
        print("已跳过推送（--no-notify）")
        return

    sent = []
    if notify_discord.notify(result):
        sent.append("Discord")
    if notify_telegram.notify(result):
        sent.append("Telegram")
    if not sent:
        print("==> 未配置推送渠道（DISCORD_WEBHOOK_URL / TELEGRAM_*），跳过通知。")


if __name__ == "__main__":
    main()
