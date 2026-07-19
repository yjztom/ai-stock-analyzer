# -*- coding: utf-8 -*-
"""通知构造测试：不真正发网络请求，只校验消息体构造正确、缺密钥时安全跳过。

运行：  python tests/test_notifications.py
"""
import os
import sys
import unittest

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import notify_discord as nd
import notify_telegram as nt

SAMPLE = {
    "summary": {
        "generated_at": "2026-07-19 04:00 UTC",
        "date": "2026-07-19", "total": 3, "live_count": 2,
        "buy_count": 1, "sell_count": 1, "hold_count": 1,
        "top_bull": [{"name": "苹果", "symbol": "AAPL", "score": 4, "rec": "买入"}],
        "top_bear": [{"name": "特斯拉", "symbol": "TSLA", "score": -3, "rec": "卖出"}],
    }
}


class TestNotifications(unittest.TestCase):
    def test_discord_embed_structure(self):
        payload = nd.build_embed(SAMPLE)
        self.assertIn("embeds", payload)
        emb = payload["embeds"][0]
        self.assertEqual(emb["title"], "📈 AI 股票分析日报")
        self.assertTrue(any("偏多" in f["name"] for f in emb["fields"]))
        self.assertIn("不构成投资建议", emb["footer"]["text"])

    def test_telegram_text_content(self):
        text = nt.build_text(SAMPLE)
        self.assertIn("苹果", text)
        self.assertIn("特斯拉", text)
        self.assertIn("不构成投资建议", text)

    def test_discord_skips_without_env(self):
        os.environ.pop("DISCORD_WEBHOOK_URL", None)     # 确保未配置
        self.assertFalse(nd.notify(SAMPLE))             # 应安全跳过返回 False

    def test_telegram_skips_without_env(self):
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        os.environ.pop("TELEGRAM_CHAT_ID", None)
        self.assertFalse(nt.notify(SAMPLE))


if __name__ == "__main__":
    unittest.main(verbosity=2)
