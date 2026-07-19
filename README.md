# 零成本 AI 股票分析系统（ai-stock-analyzer）

基于 **GitHub Actions + GitHub Pages** 的全自动股票技术分析系统，**零成本、零服务器、核心链路零第三方依赖**。支持美股 / A股 / 港股多市场，计算 7 大技术指标、生成买卖信号、网页展示并推送 Discord / Telegram。

> ⚠️ 本项目所有输出均为「技术形态的客观描述」，**仅供学习，不构成任何投资建议**。

---

## ✨ 特性一览

| 能力 | 说明 |
|---|---|
| 多市场 | 一个数据源（Yahoo Finance）通吃 美股 `AAPL` / 港股 `0700.HK` / A股 `600519.SS` |
| 7 大指标 | MACD、RSI、布林带、均线系统(MA5/20/60)、**KDJ**、成交量、金叉死叉 |
| 信号分级 | 强烈买入 → 买入 → 谨慎买入 → 观望 → 谨慎卖出 → 卖出 → 强烈卖出（7 档） |
| 零依赖 | 核心仅用 Python 标准库，CI 免 `pip install`，更稳更快 |
| 离线兜底 | 无网/被限流时自动回退仿真数据（页面标红提示），流程不中断 |
| 自动化 | GitHub Actions 双 cron 定时 + 手动触发 + 自动提交报告 |
| 展示 | GitHub Pages 静态 SPA（浅色主题、响应式、红涨绿跌、迷你走势图） |
| 推送 | Discord Embed 卡片 / Telegram Markdown，未配置则静默跳过 |

---

## 📁 目录结构

```
ai-stock-analyzer/
├── .github/workflows/stock-analysis.yml  # 定时任务（双 cron + 手动 + 自动提交）
├── scripts/                              # 分析逻辑核心
│   ├── indicators.py     # 7 大指标计算（纯 Python，含 KDJ）
│   ├── signals.py        # 趋势识别 + 7 档买卖信号评分
│   ├── data_fetcher.py   # 多市场数据获取（Yahoo，离线兜底）
│   ├── analyze_stocks.py # 主编排：取数→算指标→落盘→汇总
│   ├── notify_discord.py # Discord Webhook 推送
│   └── notify_telegram.py# Telegram Bot 推送
├── docs/                                 # GitHub Pages 展示
│   ├── index.html
│   ├── assets/{style.css, app.js}        # 浅色主题 + 动态加载 data.json
│   ├── data.json         # 最新分析结果（运行后生成）
│   └── reports/          # 按日归档报告
├── config/
│   ├── stocks_config.json     # 股票清单（17 只示例）
│   ├── indicators_config.json # 指标参数
│   └── secrets.example.json   # 密钥示例（真实值走 GitHub Secrets）
├── data/{raw, processed, signals}/       # 数据分层存储
├── tests/                                # 单元测试（unittest，零依赖）
├── main.py                               # 主入口
├── requirements.txt                      # 依赖清单（默认零依赖）
└── README.md
```

---

## 🚀 本地运行（先看效果）

```bash
cd ai-stock-analyzer
python main.py              # 分析 + 落盘（配了密钥则推送）
python main.py --no-notify  # 只分析，不推送
```

运行后打开 `docs/index.html` 即可看报告。想在本地看动态页面，用一个静态服务器（避免浏览器对本地 fetch 的限制）：

```bash
cd docs && python -m http.server 8080
# 浏览器访问 http://localhost:8080
```

跑测试：

```bash
python -m unittest discover -s tests -v
```

---

## ☁️ 部署到 GitHub（约 5 分钟）

1. 新建一个 GitHub 仓库，把本目录推上去：
   ```bash
   git init && git add -A && git commit -m "init"
   git branch -M main
   git remote add origin https://github.com/<你的用户名>/<仓库名>.git
   git push -u origin main
   ```
2. **开启 Pages**：Settings → Pages → Source 选 `main` 分支 `/docs` 目录 → Save。
   稍等片刻即可访问 `https://<用户名>.github.io/<仓库名>/`。
3. **启用 Actions**：Actions 页 Enable workflow；想立刻看效果点 **Run workflow**。
4. **（可选）配置推送**：Settings → Secrets and variables → Actions，新增：
   - `DISCORD_WEBHOOK_URL`
   - `TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID`

---

## ⏰ 定时说明（cron 用 UTC）

| cron | 北京时间 | 覆盖场景 |
|---|---|---|
| `0 8 * * 1-5` | 16:00 | A股 / 港股收盘后 |
| `0 21 * * 1-5` | 次日 05:00 | 美股收盘后 |

> GitHub Actions 定时任务在高峰期可能延迟几分钟触发，属正常现象，非严格准时。

---

## 🔧 自定义

- **改股票池**：编辑 `config/stocks_config.json`（`symbol` 用 Yahoo 格式；`market` 填 US/HK/SH/SZ）。
- **调指标参数**：编辑 `config/indicators_config.json`（RSI 周期、布林标准差、KDJ 参数等）。
- **本地测推送**：复制 `config/secrets.example.json` 为 `config/secrets.local.json` 填真实值（已被 gitignore 忽略）。

### 想换数据源？

默认用 Yahoo（在海外 CI 上比 AkShare 稳）。若你想改用 `yfinance` / `AkShare`：
1. 取消 `requirements.txt` 里对应注释；
2. 替换 `scripts/data_fetcher.py` 中 `fetch_ohlcv` 的实现，保持返回结构一致即可，上层无需改动。

---

## ⚠️ 免责声明

本项目为技术学习示例。所有指标、信号、评分均为对历史数据的机械计算与客观描述，**不预测涨跌、不构成投资建议**。据此操作，风险自负。
