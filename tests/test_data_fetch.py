# -*- coding: utf-8 -*-
"""数据获取测试：验证抓取/兜底返回结构完整且各序列等长。

沙箱无外网时，fetch_ohlcv 会自动回退仿真数据（live=False），
本测试对「真实/仿真」两种情况都成立（只校验结构，不校验数值）。

运行：  python tests/test_data_fetch.py
"""
import os
import sys
import unittest

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import data_fetcher as df


class TestDataFetch(unittest.TestCase):
    KEYS = ["live", "symbol", "currency", "dates", "opens", "highs", "lows", "closes", "volumes"]

    def _check_shape(self, d):
        for k in self.KEYS:
            self.assertIn(k, d, "缺少字段: " + k)
        n = len(d["closes"])
        self.assertGreater(n, 20, "数据点太少")
        for k in ["dates", "opens", "highs", "lows", "volumes"]:
            self.assertEqual(len(d[k]), n, k + " 长度与 closes 不一致")

    def test_us_symbol(self):
        self._check_shape(df.fetch_ohlcv("AAPL"))

    def test_hk_symbol(self):
        self._check_shape(df.fetch_ohlcv("0700.HK"))

    def test_a_share_symbol(self):
        self._check_shape(df.fetch_ohlcv("600519.SS"))

    def test_synthetic_is_deterministic(self):
        # 仿真数据对同一 symbol 必须可复现（种子固定）
        a = df._synthetic("TEST.SS", 60)
        b = df._synthetic("TEST.SS", 60)
        self.assertEqual(a["closes"], b["closes"])
        self.assertFalse(a["live"])

    def test_ohlc_consistency(self):
        d = df._synthetic("ZZZZ", 40)
        for i in range(len(d["closes"])):
            self.assertLessEqual(d["lows"][i], d["highs"][i])       # low<=high
            self.assertLessEqual(d["lows"][i], d["opens"][i])
            self.assertGreaterEqual(d["highs"][i], d["closes"][i])


if __name__ == "__main__":
    unittest.main(verbosity=2)
