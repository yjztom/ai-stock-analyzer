# -*- coding: utf-8 -*-
"""技术指标计算（纯 Python，零依赖，面向初学者，注释详尽）。

约定：
- 所有函数接收「从旧到新排列」的价格/量列表；
- 返回与输入等长的列表，数据不足的早期位置用 None 填充，方便对齐；
- 不依赖 numpy/pandas，GitHub Actions 上免安装即可运行。

包含 7 大指标族：
  SMA、EMA、MACD、RSI、Bollinger（布林带）、KDJ、成交量均线。
"""


def sma(values, period):
    """简单移动平均线（算术平均）。前 period-1 个位置为 None。"""
    n = len(values)
    out = [None] * n
    if n < period:
        return out
    for i in range(period - 1, n):
        window = values[i - period + 1: i + 1]      # 取最近 period 个值
        out[i] = sum(window) / period
    return out


def ema(values, period):
    """指数移动平均线（越近权重越大）。种子取前 period 个值的 SMA。"""
    n = len(values)
    out = [None] * n
    if n < period:
        return out
    k = 2.0 / (period + 1)
    seed = sum(values[:period]) / period
    out[period - 1] = seed
    prev = seed
    for i in range(period, n):
        prev = values[i] * k + prev * (1 - k)
        out[i] = prev
    return out


def _ema_skip_none(values, period):
    """对「含 None」的序列算 EMA：从第一个非 None 处开始做种子。

    MACD 线前面有一长串 None（EMA_slow 还没算出），不能直接用普通 ema。
    """
    n = len(values)
    out = [None] * n
    start = next((i for i, v in enumerate(values) if v is not None), None)
    if start is None or n - start < period:
        return out
    k = 2.0 / (period + 1)
    seed = sum(values[start:start + period]) / period
    out[start + period - 1] = seed
    prev = seed
    for i in range(start + period, n):
        prev = values[i] * k + prev * (1 - k)
        out[i] = prev
    return out


def _rsi_value(avg_gain, avg_loss):
    """由平均涨幅/跌幅算单个 RSI（0~100）。"""
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def rsi(values, period=14):
    """相对强弱指标 RSI（Wilder 平滑法）。>70 常视为超买，<30 视为超卖。"""
    n = len(values)
    out = [None] * n
    if n <= period:
        return out
    gains, losses = [], []
    for i in range(1, n):
        d = values[i] - values[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    avg_gain = sum(gains[:period]) / period         # 首值用简单平均
    avg_loss = sum(losses[:period]) / period
    out[period] = _rsi_value(avg_gain, avg_loss)
    for i in range(period + 1, n):                  # 之后 Wilder 递推
        avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
        out[i] = _rsi_value(avg_gain, avg_loss)
    return out


def macd(values, fast=12, slow=26, signal=9):
    """MACD 指标。返回 (MACD线, 信号线, 柱)。

    MACD线 = EMA_fast - EMA_slow；信号线 = MACD线 的 EMA_signal；柱 = 两者之差。
    快线上穿慢线为「金叉」(偏多)，下穿为「死叉」(偏空)。
    """
    ema_fast = ema(values, fast)
    ema_slow = ema(values, slow)
    n = len(values)
    macd_line = [None] * n
    for i in range(n):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            macd_line[i] = ema_fast[i] - ema_slow[i]
    sig = _ema_skip_none(macd_line, signal)
    hist = [None] * n
    for i in range(n):
        if macd_line[i] is not None and sig[i] is not None:
            hist[i] = macd_line[i] - sig[i]
    return macd_line, sig, hist


def bollinger(values, period=20, k=2.0):
    """布林带。返回 (上轨, 中轨, 下轨)，中轨即 SMA。

    上/下轨 = 中轨 ± k * 标准差。触下轨常看作超跌，触上轨看作超买。
    """
    mid = sma(values, period)
    n = len(values)
    upper = [None] * n
    lower = [None] * n
    for i in range(period - 1, n):
        window = values[i - period + 1: i + 1]
        mean = sum(window) / period
        var = sum((x - mean) ** 2 for x in window) / period
        std = var ** 0.5
        upper[i] = mean + k * std
        lower[i] = mean - k * std
    return upper, mid, lower


def kdj(closes, highs, lows, period=9, k_smooth=3, d_smooth=3):
    """KDJ 随机指标。返回 (K, D, J)，均与输入等长，前 period-1 位为 None。

    计算步骤（经典参数 9,3,3）：
      1) RSV = (收盘 - N日最低) / (N日最高 - N日最低) * 100
      2) K = (1/k_smooth)*RSV + (1-1/k_smooth)*前K   （K、D 初值取 50）
      3) D = (1/d_smooth)*K   + (1-1/d_smooth)*前D
      4) J = 3K - 2D
    低位金叉（K 上穿 D）偏多，高位死叉偏空；J<0 极度超卖，J>100 极度超买。
    """
    n = len(closes)
    K = [None] * n
    D = [None] * n
    J = [None] * n
    if n < period:
        return K, D, J
    ak = 1.0 / k_smooth
    ad = 1.0 / d_smooth
    prev_k, prev_d = 50.0, 50.0                      # 经典初值
    for i in range(period - 1, n):
        hi = max(highs[i - period + 1: i + 1])
        lo = min(lows[i - period + 1: i + 1])
        rsv = 50.0 if hi == lo else (closes[i] - lo) / (hi - lo) * 100.0
        cur_k = ak * rsv + (1 - ak) * prev_k
        cur_d = ad * cur_k + (1 - ad) * prev_d
        K[i] = cur_k
        D[i] = cur_d
        J[i] = 3 * cur_k - 2 * cur_d
        prev_k, prev_d = cur_k, cur_d
    return K, D, J
