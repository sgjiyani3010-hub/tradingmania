# GOLD TRADING BOT — Multi-Agent Automation Master Plan

> **XAUUSD · Antigravity + Gemini AI · TradingView Paper Trading**
>
> Account: `sagarjiyani3010` · Capital: **$1,000** · Per Trade: **$200** · Lots: **0.05**
>
> Version 1.0 · March 2026

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Multi-Agent Design](#3-multi-agent-design)
4. [Environment Variables (.env)](#4-environment-variables-env)
5. [Pine Script — XAUUSD Indicator](#5-pine-script--xauusd-indicator)
6. [Webhook Server (Railway Deployment)](#6-webhook-server-railway-deployment)
7. [Antigravity Multi-Agent Setup](#7-antigravity-multi-agent-setup)
8. [TradingView Alert Configuration](#8-tradingview-alert-configuration)
9. [Implementation Phases](#9-implementation-phases)
10. [Risk Management Rules](#10-risk-management-rules)
11. [Troubleshooting](#11-troubleshooting)
12. [Final Launch Checklist](#12-final-launch-checklist)

---

## 1. Project Overview

This document is the **single source of truth** for building a fully automated GOLD (XAUUSD) trading bot using a multi-agent AI architecture. The system uses:

- **TradingView Pine Script** for signal generation
- **FastAPI webhook server** deployed on Railway for order execution
- **Antigravity** as the multi-agent orchestration platform with **Gemini AI** models powering each agent

### Capital Allocation at a Glance

| Variable | Value / How to Get It | Used By |
|---|---|---|
| **Total Capital** | $1,000 USD (TradingView Paper Trading) | All agents |
| **Per-Trade Deploy** | $200 USD (~0.05 lots on XAUUSD at 1:100 leverage) | Order Agent |
| **Max Open Trades** | 1 at a time (sequential, not concurrent) | Risk Agent |
| **Daily Risk Limit** | $100 max drawdown per day (10% of capital) | Risk Agent |
| **Profit Hold Trigger** | 1.5% floating profit → switch to trailing stop | Order Agent |

---

## 2. System Architecture

The system has **four layers** that communicate sequentially:

### Layer 1 — Signal Layer (TradingView)

Pine Script indicator runs on **XAUUSD 5-minute chart**. Evaluates **5 filters** on every bar close:

1. EMA 9/21 crossover
2. RSI sweet-spot (50–68 long / 32–50 short)
3. MACD histogram momentum
4. ADX trend strength ≥ 18
5. Strong-body candle confirmation

Fires an alert **only when score ≥ 3/5**.

### Layer 2 — Webhook Layer (Railway Server)

FastAPI Python server hosted on **Railway (free tier)**. Receives JSON POST from TradingView alert, verifies secret token, and calls the TradingView Paper Trading REST API to place the order. Logs every trade to `/trades` endpoint.

### Layer 3 — Agent Orchestration Layer (Antigravity)

Five specialised Gemini-powered agents run as an orchestrated workflow. Each agent has a **single atomic responsibility**. The Orchestrator agent coordinates all others. Agents communicate via Antigravity's built-in message-passing system.

### Layer 4 — Monitoring Layer (Dashboard)

A simple web dashboard polls the Railway server's `/trades` endpoint and displays live P&L, win rate, equity curve, and agent status. Agents can also send Telegram or email alerts.

---

## 3. Multi-Agent Design

Five agents are created in Antigravity. Each uses a Gemini model appropriate to its workload. All agents are **stateless** — state is held in the Railway server's in-memory log and TradingView Paper Trading account.

| Agent Name | Role | Model | Primary Task |
|---|---|---|---|
| **Orchestrator** | Coordinator | `gemini-1.5-pro` | Routes tasks between agents, enforces 10-min trade limit, decides profit-hold vs exit |
| **Signal Analyst** | Market Reader | `gemini-1.5-flash` | Parses incoming TradingView alert JSON, validates signal score, enriches with context |
| **Risk Guard** | Risk Manager | `gemini-1.5-flash` | Checks daily drawdown limit, position sizing, blocks trades if risk threshold hit |
| **Order Executor** | Trade Placer | `gemini-1.5-flash` | Calls Railway `/webhook` endpoint with correct JSON payload, logs confirmation |
| **Monitor Agent** | Reporter | `gemini-1.5-flash` | Polls `/trades` every 60s, sends P&L summary, triggers alerts on big wins or losses |

---

### 3.1 Orchestrator Agent — System Prompt

> **SYSTEM PROMPT:** Copy this exactly into Antigravity's system prompt field for the Orchestrator agent.

```
You are the Orchestrator of a GOLD (XAUUSD) trading bot. Your job is to coordinate 4 specialist agents to execute trades on TradingView Paper Trading.

Rules you must enforce at all times:
- Maximum 3 trades per 10-minute window. Track timestamps of last 3 trades.
- Maximum 1 open position at a time. If a position is open, block new entries.
- Daily loss limit: $100. If realized + unrealized loss exceeds $100, stop all trading and alert the user.
- Minimum trade size: 0.05 lots (= ~$200 margin on XAUUSD).
- Profit-hold rule: if floating profit exceeds 1.5% of account equity, instruct Order Executor to switch from fixed TP to trailing stop.

When a signal arrives:
1. Send signal JSON to Signal Analyst. Wait for validation response.
2. If valid, send to Risk Guard with current account state. Wait for approval.
3. If approved, send to Order Executor with full trade parameters.
4. Log the result and update your internal trade counter.
5. After every 5 trades, request a summary report from Monitor Agent.

Always respond in JSON format. Never place a trade without Risk Guard approval.
```

---

### 3.2 Signal Analyst Agent — System Prompt

```
You are the Signal Analyst for a GOLD trading bot. You receive raw alert JSON from TradingView and must validate and enrich it.

Input format you will receive:
{"action":"BUY","price":2345.50,"secret":"[token]"}

Your job:
1. Confirm action is BUY or SELL (reject CLOSE or unknown).
2. Confirm price is a realistic XAUUSD price (must be between 1500 and 4000).
3. Calculate SL and TP:
   - BUY:  SL = price - (price * 0.0018)   TP = price + (price * 0.0025)
   - SELL: SL = price + (price * 0.0018)   TP = price - (price * 0.0025)
4. Return enriched JSON: {"valid":true,"action":"BUY","price":2345.50,"sl":2341.28,"tp":2351.36,"lots":0.05}
5. If invalid, return: {"valid":false,"reason":"[explanation]"}

Respond ONLY with JSON. No extra text.
```

---

### 3.3 Risk Guard Agent — System Prompt

```
You are the Risk Guard for a GOLD trading bot. You protect the $1,000 paper trading account.

You receive: {"action":"BUY","price":2345.50,"sl":2341.28,"tp":2351.36,"lots":0.05,"current_balance":985.00,"daily_pnl":-15.00,"open_positions":0}

Risk rules (ALL must pass for approval):
1. daily_pnl must be greater than -100 (max $100 daily loss)
2. open_positions must be 0 (no concurrent trades)
3. lots must be exactly 0.05 (never deviate)
4. SL distance must not exceed 0.3% of price (catastrophic stop prevention)
5. TP must be at least 1.2x the SL distance (minimum reward:risk ratio)

If ALL rules pass: {"approved":true,"reason":"All risk checks passed"}
If ANY rule fails: {"approved":false,"reason":"[specific rule that failed]"}

Respond ONLY with JSON. No extra text.
```

---

### 3.4 Order Executor Agent — System Prompt

```
You are the Order Executor for a GOLD trading bot. You place trades by calling the webhook server.

You will receive: {"action":"BUY","price":2345.50,"sl":2341.28,"tp":2351.36,"lots":0.05,"webhook_url":"https://YOUR-APP.up.railway.app/webhook","secret":"mysecret123"}

Your job:
1. Make an HTTP POST to webhook_url with this body:
   {"secret":"[secret]","action":"[action]","price":[price],"sl":[sl],"tp":[tp],"lots":[lots]}
2. If HTTP 200 received: return {"executed":true,"order_id":"[from response]"}
3. If HTTP error: return {"executed":false,"error":"[status code and message]","retry":true}
4. On retry=true, wait 3 seconds and try once more. After 2 failures, set retry:false.

Always log: timestamp, action, price, SL, TP, lots, and server response.
Respond ONLY with JSON. No extra text.
```

---

### 3.5 Monitor Agent — System Prompt

```
You are the Monitor Agent for a GOLD trading bot. You watch the account and report status.

Every 60 seconds you poll: GET https://YOUR-APP.up.railway.app/trades

From the response, calculate and report:
1. Total trades today
2. Win rate (wins / total * 100)
3. Total realized P&L
4. Largest single win and largest single loss
5. Current streak (consecutive wins or losses)

Alert conditions (send immediate alert to Orchestrator):
- Any single trade loses more than $50
- Win rate drops below 40% after 5+ trades
- 3 consecutive losing trades
- Daily P&L reaches -$80 (warning before $100 limit)
- Daily P&L exceeds +$150 (lock in profits notification)

Report format: {"status":"ok","trades":12,"win_rate":58,"pnl":+42.50,"alert":null}
If alert needed: {"status":"alert","message":"[alert text]","severity":"warning|critical"}
```

---

## 4. Environment Variables (`.env`)

> **Set ALL of these as environment variables on Railway before deploying. Never commit these to GitHub.**

### How to Obtain Each Value

| Variable | How to Get It |
|---|---|
| `TV_SESSION` | Open Chrome → `tradingview.com` → F12 → Application tab → Cookies → `tradingview.com` → copy `sessionid` value |
| `TV_SESSION2` | Same location as above → copy `sessionid_sign` value |
| `TV_ACCOUNT_ID` | In DevTools Network tab, click Paper Trading panel → find any API request → look for `id` field starting with `pst` in the JSON response |
| `GEMINI_API_KEY` | Go to `aistudio.google.com` → Get API Key → Create API Key → copy the key starting with `AIza` |

### Complete Variable Reference

| Variable | Value / How to Get It | Used By |
|---|---|---|
| `TV_SESSION` | Paste your TradingView `sessionid` cookie value here | Railway server → TradingView API auth |
| `TV_SESSION2` | Paste your TradingView `sessionid_sign` cookie value here | Railway server → TradingView API auth |
| `TV_ACCOUNT_ID` | Paste your Paper Trading account ID (starts with `pst`) | Railway server → order placement |
| `WEBHOOK_SECRET` | `mysecret123` (change to anything, must match Pine Script) | Railway + Pine Script alert message |
| `TRADE_SIZE` | `0.05` (0.05 lots = ~$200 margin on XAUUSD at 1:100 leverage) | Railway server → order size |
| `GEMINI_API_KEY` | Paste your Gemini API key here (starts with `AIza...`) | All Antigravity agents |
| `RAILWAY_URL` | `https://YOUR-APP-NAME.up.railway.app` (get after deploy) | Antigravity Order Executor agent |

### Example `.env` File

```env
TV_SESSION=abc123xyz...
TV_SESSION2=def456uvw...
TV_ACCOUNT_ID=pst987654321
WEBHOOK_SECRET=mysecret123
TRADE_SIZE=0.05
GEMINI_API_KEY=AIzaSy...
RAILWAY_URL=https://gold-scalper.up.railway.app
```

---

## 5. Pine Script — XAUUSD Indicator

> [!IMPORTANT]
> Add this as an **INDICATOR** (not Strategy) on your **XAUUSD 5M** chart. Then create 2 alerts (BUY + SELL) as described in [Section 8](#8-tradingview-alert-configuration).

```pine
//@version=5
indicator("XAUUSD Precision Scalper | Webhook Ready", overlay=true)

emaFast   = input.int(9,    "EMA Fast")
emaSlow   = input.int(21,   "EMA Slow")
rsiLen    = input.int(14,   "RSI Length")
adxLen    = input.int(14,   "ADX Length")
adxMin    = input.float(18.0,"Min ADX", step=0.5)
atrLen    = input.int(14,   "ATR Length")
atrSL     = input.float(1.8,"SL Multiplier", step=0.1)
atrTP     = input.float(2.5,"TP Multiplier",  step=0.1)
maxPer10m = input.int(3,    "Max signals / 10 min")
sessionOn = input.bool(false,"Session filter ON")

emaF = ta.ema(close, emaFast)
emaS = ta.ema(close, emaSlow)
rsi  = ta.rsi(close, rsiLen)
atr  = ta.atr(atrLen)

upMove   = high - high[1]
downMove = low[1] - low
plusDM   = upMove > downMove and upMove > 0 ? upMove : 0.0
minusDM  = downMove > upMove and downMove > 0 ? downMove : 0.0
tr_      = ta.rma(ta.tr, adxLen)
plusDI   = 100 * ta.rma(plusDM, adxLen) / tr_
minusDI  = 100 * ta.rma(minusDM, adxLen) / tr_
dx       = 100 * math.abs(plusDI - minusDI) / (plusDI + minusDI)
adx      = ta.rma(dx, adxLen)

[_, _, hist] = ta.macd(close, 12, 26, 9)

bodySize   = math.abs(close - open)
rangeSize  = high - low
strongBody = rangeSize > 0 ? bodySize / rangeSize > 0.5 : false
bullCandle = close > open and strongBody
bearCandle = close < open and strongBody

emaBull  = emaF > emaS
emaBear  = emaF < emaS
rsiBull  = rsi >= 50 and rsi <= 68
rsiBear  = rsi >= 32 and rsi <= 50
macdBull = hist > 0 and hist > hist[1]
macdBear = hist < 0 and hist < hist[1]
trending = adx >= adxMin

longScore  = (emaBull?1:0)+(rsiBull?1:0)+(macdBull?1:0)+(trending?1:0)+(bullCandle?1:0)
shortScore = (emaBear?1:0)+(rsiBear?1:0)+(macdBear?1:0)+(trending?1:0)+(bearCandle?1:0)

var int   windowCount = 0
var float windowOpen  = na
if na(windowOpen) or (time - windowOpen) >= 600000
    windowOpen  := time
    windowCount := 0
underLimit = windowCount < maxPer10m

londonNY  = time(timeframe.period, "0800-1700", "Europe/London")
inSession = sessionOn ? not na(londonNY) : true

longFire  = barstate.isconfirmed and longScore  >= 3 and underLimit and inSession
shortFire = barstate.isconfirmed and shortScore >= 3 and underLimit and inSession

if longFire
    windowCount += 1
if shortFire
    windowCount += 1

plot(emaF, "EMA 9",  color=color.new(color.lime,10),   linewidth=1)
plot(emaS, "EMA 21", color=color.new(color.orange,10), linewidth=1)
plotshape(longFire,  location=location.belowbar, style=shape.triangleup,
    color=color.new(color.green,0), size=size.normal)
plotshape(shortFire, location=location.abovebar, style=shape.triangledown,
    color=color.new(color.red,0),   size=size.normal)
bgcolor(inSession ? color.new(color.blue,95) : na)

var label lbl = na
label.delete(lbl)
lbl := label.new(bar_index, low - atr*2,
    "L:" + str.tostring(longScore) + "/5  S:" + str.tostring(shortScore) + "/5" +
    "\nADX:" + str.tostring(math.round(adx,1)) + "  RSI:" + str.tostring(math.round(rsi,1)) +
    "\nWindow: " + str.tostring(windowCount) + "/" + str.tostring(maxPer10m),
    style=label.style_label_up, color=color.new(color.black,5),
    textcolor=color.white, size=size.small)

alertcondition(longFire,  title="BUY Signal",  message="BUY XAUUSD fired")
alertcondition(shortFire, title="SELL Signal", message="SELL XAUUSD fired")
```

---

## 6. Webhook Server (Railway Deployment)

The webhook server is already built (`app.py` + `requirements.txt` + `Dockerfile`). Follow these exact steps to get it live on Railway with a public HTTPS URL.

### 6.1 Step-by-step Railway Deployment

1. Go to [railway.app](https://railway.app) and sign up with your GitHub account (free)
2. Create a new GitHub repository called `gold-scalper-bot` (public or private)
3. Upload these **3 files** to the repository root: `app.py` · `requirements.txt` · `Dockerfile`
4. In Railway dashboard → **New Project** → **Deploy from GitHub repo** → select `gold-scalper-bot`
5. Railway auto-detects the Dockerfile and starts building
6. Once deployed, go to **Settings → Variables** → add ALL env vars from [Section 4](#4-environment-variables-env)
7. Go to **Settings → Networking → Generate Domain** → copy the HTTPS URL
8. Test: open `YOUR-URL/` in browser — you should see `{"status":"running"}`

### 6.2 Verify the Server Is Working

Run this in your terminal (replace the URL with your Railway URL):

```bash
curl -X POST https://YOUR-APP.up.railway.app/webhook \
  -H "Content-Type: application/json" \
  -d '{"secret":"mysecret123","action":"BUY","price":2345.50,"sl":2341.28,"tp":2351.36}'
```

**Expected response:**

```json
{"status":"ok","trade":{"action":"BUY",...}}
```

Then check your **TradingView Paper Trading panel** — a BUY order for XAUUSD should appear.

---

## 7. Antigravity Multi-Agent Setup

Antigravity is used to create, configure, and orchestrate the 5 AI agents. Each agent is set up as a separate agent node in Antigravity with its system prompt from [Section 3](#3-multi-agent-design).

### 7.1 Create the Agents

1. Log in to your Antigravity account
2. Create a new Workflow called: **`XAUUSD Gold Scalper`**
3. Add **5 Agent nodes** with these exact names:
   - `Orchestrator`
   - `Signal Analyst`
   - `Risk Guard`
   - `Order Executor`
   - `Monitor Agent`
4. For each agent, set the model to the Gemini model specified in [Section 3's table](#3-multi-agent-design)
5. For each agent, paste the system prompt from the corresponding subsection in Section 3
6. Set `GEMINI_API_KEY` as an environment variable in Antigravity's settings

### 7.2 Connect the Agent Workflow

Wire the agents in this **exact order** in Antigravity's visual editor:

```
TradingView Alert (webhook trigger)
         │
         ▼
   Orchestrator  ◄──────────────────────────────────┐
         │                                          │
         ▼                                          │
  Signal Analyst ──► (invalid) ──► LOG & STOP       │
         │ (valid)                                  │
         ▼                                          │
    Risk Guard   ──► (blocked) ──► LOG & STOP       │
         │ (approved)                               │
         ▼                                          │
  Order Executor ──► Railway /webhook               │
         │                                          │
         ▼                                          │
  Monitor Agent  ────── every 60s report ───────────┘
```

### 7.3 Configure the Webhook Trigger in Antigravity

1. In Antigravity, find the **Webhook / HTTP Trigger** option for the workflow
2. Copy the Antigravity workflow webhook URL (looks like `https://app.antigravity.ai/trigger/abc123`)
3. In TradingView → **Create Alert** → set **Webhook URL** to this Antigravity URL
4. Set the alert message to this JSON for **BUY** signals:
   ```json
   {"secret":"mysecret123","action":"BUY","price":{{close}}}
   ```
5. Create a second alert for **SELL** signals:
   ```json
   {"secret":"mysecret123","action":"SELL","price":{{close}}}
   ```
6. Set **BOTH** alerts to trigger: **Once Per Bar Close**

> [!CAUTION]
> **WHY "Once Per Bar Close":** This prevents signal repainting. The alert only fires after the 5-minute bar is fully closed and confirmed, meaning the signal cannot change or retract.

---

## 8. TradingView Alert Configuration

Create **exactly 2 alerts** in TradingView. Both must be set to **"Once Per Bar Close"** — this is the single most important setting.

### Alert #1 — BUY Signal

| Variable | Value / How to Get It | Used By |
|---|---|---|
| **Condition** | XAUUSD Precision Scalper → BUY Signal | TradingView alert picker |
| **Trigger** | **Once Per Bar Close** ⚠️ CRITICAL | Prevents repainting |
| **Webhook URL** | `https://YOUR-APP.up.railway.app/webhook` | Your Railway server |
| **Message** | `{"secret":"mysecret123","action":"BUY","price":{{close}}}` | Parsed by server + agents |

### Alert #2 — SELL Signal

| Variable | Value / How to Get It | Used By |
|---|---|---|
| **Condition** | XAUUSD Precision Scalper → SELL Signal | TradingView alert picker |
| **Trigger** | **Once Per Bar Close** ⚠️ CRITICAL | Prevents repainting |
| **Webhook URL** | `https://YOUR-APP.up.railway.app/webhook` | Your Railway server |
| **Message** | `{"secret":"mysecret123","action":"SELL","price":{{close}}}` | Parsed by server + agents |

> [!WARNING]
> **PRO PLAN REQUIRED:** TradingView webhook alerts require a Pro plan or above ($14.95/month). The free plan does not support webhook URLs. Upgrade at [tradingview.com/pricing](https://tradingview.com/pricing) before creating these alerts.

---

## 9. Implementation Phases

> **Complete each phase fully before moving to the next. Do not skip steps.**

### Phase 1: Repository & Server Setup — ⏱️ 30 minutes

- [ ] Create GitHub repo `gold-scalper-bot`
- [ ] Add `app.py`, `requirements.txt`, `Dockerfile` (from the files provided)
- [ ] Sign up at [railway.app](https://railway.app) with GitHub
- [ ] Deploy repo to Railway → wait for green build
- [ ] Add all env variables from [Section 4](#4-environment-variables-env) to Railway
- [ ] Generate Railway domain URL
- [ ] Run curl test from [Section 6.2](#62-verify-the-server-is-working) to confirm server is live

### Phase 2: TradingView Pine Script — ⏱️ 15 minutes

- [ ] Open TradingView → search **XAUUSD** → set chart to **5M** timeframe
- [ ] Open Pine Script Editor → paste the script from [Section 5](#5-pine-script--xauusd-indicator)
- [ ] Save as `XAUUSD Precision Scalper`
- [ ] Click **"Add to Chart"** → confirm EMA lines and debug label appear
- [ ] Check debug label: it shows live score (`L:X/5 S:X/5`), ADX, RSI values

### Phase 3: Antigravity Agent Setup — ⏱️ 45 minutes

- [ ] Create Antigravity account at [antigravity.ai](https://antigravity.ai)
- [ ] Add `GEMINI_API_KEY` to Antigravity environment settings
- [ ] Create workflow `XAUUSD Gold Scalper`
- [ ] Add 5 agent nodes, set Gemini models as specified in [Section 3](#3-multi-agent-design)
- [ ] Paste system prompts from Section 3 into each agent
- [ ] Wire the workflow in the order shown in [Section 7.2](#72-connect-the-agent-workflow)
- [ ] Copy the Antigravity workflow trigger webhook URL

### Phase 4: TradingView Alerts — ⏱️ 10 minutes

- [ ] In TradingView click the **Alert (clock)** icon
- [ ] Create BUY alert exactly as specified in [Section 8](#8-tradingview-alert-configuration)
- [ ] Create SELL alert exactly as specified in [Section 8](#8-tradingview-alert-configuration)
- [ ] Confirm both alerts show **"Active"** status in the Alerts panel

### Phase 5: End-to-End Test — ⏱️ 20 minutes

- [ ] Manually POST a test BUY to your Railway server (curl from [Section 6.2](#62-verify-the-server-is-working))
- [ ] Verify order appears in TradingView Paper Trading panel
- [ ] Trigger the Antigravity workflow manually with a test payload
- [ ] Trace through all 5 agents in Antigravity logs
- [ ] Wait for a real live signal on XAUUSD 5M chart
- [ ] Watch the full flow: TradingView alert → Antigravity → Railway → Paper Trade

---

## 10. Risk Management Rules

> These rules are enforced by the **Risk Guard agent** ([Section 3.3](#33-risk-guard-agent--system-prompt)) and should **never** be overridden.

| Variable | Value / How to Get It | Used By |
|---|---|---|
| **Max daily loss** | $100 (10% of $1,000 capital) | Risk Guard blocks all trades if hit |
| **Max trade size** | 0.05 lots fixed | Order Executor uses this always |
| **Max concurrent trades** | 1 position at a time | Orchestrator blocks parallel entries |
| **Max trades / 10 min** | 3 signals in any rolling 10-minute window | Pine Script + Orchestrator enforce |
| **Min reward:risk ratio** | 1.2:1 (TP distance ≥ 1.2× SL distance) | Risk Guard validates before approval |
| **Profit-hold trigger** | 1.5% floating profit → switch to trailing stop | Orchestrator instructs Order Executor |
| **Trail stop distance** | 0.5× ATR from peak price | Order Executor updates the exit order |
| **Hard stop loss** | 1.8× ATR below entry (long) / above entry (short) | Order Executor sets on entry |
| **Take profit** | 2.5× ATR above entry (long) / below entry (short) | Order Executor sets on entry |

---

## 11. Troubleshooting

### No orders appearing in Paper Trading

- Check Railway logs for incoming POST requests. If none, the TradingView alert webhook is not firing.
- Verify your TradingView plan supports webhooks (**Pro required**).
- Confirm the alert webhook URL matches your Railway domain **exactly** (including `https://`).
- Check that `TV_SESSION` and `TV_SESSION2` cookies are still valid — they expire. Re-copy from browser if needed.

### Railway server returning 403

- The `WEBHOOK_SECRET` in Railway env vars does not match the `secret` field in the alert message JSON.
- Both must be exactly: `mysecret123` (or whatever you set).

### Pine Script shows no signals (score always 0–2)

- Check the debug label on the chart — it shows each filter's live value.
- If ADX is always below 18, gold may be in a ranging market — lower `adxMin` to `15`.
- If RSI never hits the sweet spot, the chart timeframe may be wrong — confirm **5M**.

### Antigravity agents not triggering

- Confirm `GEMINI_API_KEY` is set correctly in Antigravity environment.
- Check that the TradingView alert is pointing to the **Antigravity webhook URL**, not the Railway URL.
- In the Antigravity flow, the Railway URL must be hardcoded in the Order Executor agent's system prompt.

### Session cookies expired

- Go to `tradingview.com` → F12 → Application → Cookies → copy fresh `sessionid` and `sessionid_sign`.
- Update `TV_SESSION` and `TV_SESSION2` in Railway environment variables.
- Redeploy (Railway auto-redeploys when env vars change).

---

## 12. Final Launch Checklist

> **Tick every item before considering the system live.**

- [ ] Railway server deployed and returning `{"status":"running"}` at root URL
- [ ] All 7 environment variables set in Railway
- [ ] curl test from [Section 6.2](#62-verify-the-server-is-working) places a test order in Paper Trading
- [ ] Pine Script added to XAUUSD 5M chart and debug label is visible
- [ ] EMA 9 and EMA 21 lines visible on chart
- [ ] TradingView Pro plan active (webhooks require Pro)
- [ ] BUY alert created: **Once Per Bar Close** + correct webhook URL + correct JSON message
- [ ] SELL alert created: **Once Per Bar Close** + correct webhook URL + correct JSON message
- [ ] Antigravity workflow created with all 5 agents
- [ ] All 5 agent system prompts pasted correctly
- [ ] Gemini API key set in Antigravity environment
- [ ] `RAILWAY_URL` hardcoded in Order Executor agent system prompt
- [ ] Antigravity workflow trigger URL set as webhook in TradingView OR Railway URL
- [ ] End-to-end test completed: signal → agent chain → paper trade order
- [ ] Monitor Agent confirmed to be polling `/trades` endpoint
- [ ] Paper Trading account balance confirms $1,000 starting capital

---

> **End of Document** · XAUUSD Gold Scalper · Version 1.0
