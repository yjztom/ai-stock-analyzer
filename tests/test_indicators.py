# -*- coding: utf-8 -*-
"""指标算法单元测试（纯标准库 unittest，零依赖，沙箱可直接跑）。

运行：  python -m unittest discover -s tests -v
或：    python tests/test_indicators.py
"""
import os
import sys
import unittest

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import indicators as ind


class TestIndicators(unittest.TestCase):
    def setUp(self):
        # 一段可预测的价格序列
        self.up = [float(x) for x in range(1, 51)]          # 单调上涨 1..50
        self.flat = [10.0] * 40

    def test_sma_basic(self):
        out = ind.sma([1, 2, 3, 4, 5], 3)
        self.assertEqual(out[:2], [None, None])             # 前两位不足
        self.assertAlmostEqual(out[2], 2.0)                 # (1+2+3)/3
        self.assertAlmostEqual(out[4], 4.0)                 # (3+4+5)/3

    def test_ema_length_and_seed(self):
        out = ind.ema([1, 2, 3, 4, 5], 3)
        self.assertEqual(len(out), 5)
        self.assertIsNone(out[1])
        self.assertAlmostEqual(out[2], 2.0)                 # 种子=SMA3=(1+2+3)/3

    def test_rsi_all_up_is_100(self):
        out = ind.rsi(self.up, 14)
        self.assertIsNotNone(out[-1])
        self.assertAlmostEqual(out[-1], 100.0, places=6)    # 全涨→RSI=100

    def test_rsi_flat_is_50(self):
        out = ind.rsi(self.flat, 14)
        self.assertAlmostEqual(out[-1], 50.0, places=6)     # 无波动→50

    def test_macd_shapes(self):
        macd_line, sig, hist = ind.macd(self.up)
        self.assertEqual(len(macd_line), len(self.up))
        self.assertEqual(len(sig), len(self.up))
        self.assertEqual(len(hist), len(self.up))
        self.assertIsNotNone(hist[-1])

    def test_bollinger_order(self):
        upper, mid, lower = ind.bollinger(self.up, 20, 2.0)
        self.assertTrue(lower[-1] < mid[-1] < upper[-1])    # 下<中<上

    def test_kdj_range_and_j(self):
        highs = [x + 1 for x in self.up]
        lows = [x - 1 for x in self.up]
        K, D, J = ind.kdj(self.up, highs, lows, 9, 3, 3)
        self.assertIsNotNone(K[-1])
        self.assertTrue(0 <= K[-1] <= 100)                  # K 在 0~100
        self.assertAlmostEqual(J[-1], 3 * K[-1] - 2 * D[-1], places=6)  # J=3K-2D

    def test_kdj_flat_is_50(self):
        K, D, J = ind.kdj(self.flat, self.flat, self.flat, 9, 3, 3)
        self.assertAlmostEqual(K[-1], 50.0, places=6)       # 无波动 RSV=50 → K=50


if __name__ == "__main__":
    unittest.main(verbosity=2)
