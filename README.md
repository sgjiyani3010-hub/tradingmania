# 🥇 XAUUSD Gold Scalper Bot

> Fully automated GOLD (XAUUSD) trading bot using multi-agent AI architecture.
> TradingView Pine Script → Antigravity + Gemini AI Agents → FastAPI Webhook → Paper Trading

**Account:** `sagarjiyani3010` · **Capital:** $1,000 · **Per Trade:** $200 · **Lots:** 0.05

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐     ┌──────────────┐
│   TradingView   │────▶│   Antigravity    │────▶│  Railway Server │────▶│  TV Paper    │
│   Pine Script   │     │   5 AI Agents    │     │  FastAPI (app)  │     │  Trading API │
│   (XAUUSD 5M)  │     │  Gemini-powered  │     │  /webhook       │     │  Orders      │
└─────────────────┘     └──────────────────┘     └─────────────────┘     └──────────────┘
```

| Layer | Component | Purpose |
|-------|-----------|---------|
| **Signal** | Pine Script on XAUUSD 5M | Evaluates 5 filters, fires alert when score ≥ 3/5 |
| **Orchestration** | 5 Antigravity agents | Validate → Risk-check → Execute → Monitor |
| **Execution** | FastAPI on Railway | Receives webhook, places order via TV API |
| **Monitoring** | Monitor Agent | Polls `/trades`, reports P&L, triggers alerts |

## Project Structure

```
tradingmania/
├── app.py                          # FastAPI webhook server
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Railway deployment container
├── .env.example                    # Environment variable template
├── agents/                         # Antigravity agent system prompts
│   ├── orchestrator.md             #   Coordinator (gemini-1.5-pro)
│   ├── signal_analyst.md           #   Market Reader (gemini-1.5-flash)
│   ├── risk_guard.md               #   Risk Manager (gemini-1.5-flash)
│   ├── order_executor.md           #   Trade Placer (gemini-1.5-flash)
│   └── monitor_agent.md            #   Reporter (gemini-1.5-flash)
├── scripts/
│   └── xauusd_precision_scalper.pine  # TradingView Pine Script indicator
└── docs/
    └── gold_trading_bot_plan.md    # Full master plan document
```

## Quick Start

### 1. Clone & Configure

```bash
git clone https://github.com/YOUR-USER/gold-scalper-bot.git
cd gold-scalper-bot
cp .env.example .env
# Edit .env with your TradingView cookies, account ID, and API keys
```

### 2. Run Locally

```bash
pip install -r requirements.txt
python app.py
# Server starts at http://localhost:8000
```

### 3. Test

```bash
# Health check
curl http://localhost:8000/

# Place a test trade
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"secret":"mysecret123","action":"BUY","price":2345.50,"sl":2341.28,"tp":2351.36}'

# View trade log
curl http://localhost:8000/trades
```

### 4. Deploy to Railway

1. Push to GitHub
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Add all env vars from `.env.example` to Railway Settings → Variables
4. Generate domain URL in Settings → Networking

### 5. Set Up TradingView

1. Add Pine Script from `scripts/xauusd_precision_scalper.pine` to XAUUSD 5M chart
2. Create BUY and SELL alerts with webhook URL pointing to your Railway server
3. Set both alerts to **"Once Per Bar Close"**

### 6. Set Up Antigravity Agents

1. Create workflow `XAUUSD Gold Scalper` in Antigravity
2. Add 5 agents using prompts from `agents/` directory
3. Wire the workflow (see `docs/gold_trading_bot_plan.md` §7.2)

## Environment Variables

| Variable | Description |
|----------|-------------|
| `TV_SESSION` | TradingView `sessionid` cookie |
| `TV_SESSION2` | TradingView `sessionid_sign` cookie |
| `TV_ACCOUNT_ID` | Paper Trading account ID (starts with `pst`) |
| `WEBHOOK_SECRET` | Secret token for webhook auth |
| `TRADE_SIZE` | Lot size per trade (default: `0.05`) |
| `GEMINI_API_KEY` | Google Gemini API key for agents |
| `RAILWAY_URL` | Deployed server URL |

## Risk Management

| Rule | Value |
|------|-------|
| Max daily loss | $100 (10% of capital) |
| Max trade size | 0.05 lots |
| Max concurrent trades | 1 |
| Max trades / 10 min | 3 |
| Min reward:risk | 1.2:1 |
| Hard stop loss | 1.8× ATR |
| Take profit | 2.5× ATR |

---

> 📖 **Full documentation:** See [docs/gold_trading_bot_plan.md](docs/gold_trading_bot_plan.md) for the complete master plan.
