"""
XAUUSD Gold Scalper — Webhook Server
=====================================
FastAPI server that receives trading signals from TradingView alerts
(or Antigravity agents) and places orders on TradingView Paper Trading
via its internal REST API using session cookies.

Endpoints:
    GET  /         — Health check
    POST /webhook  — Receive and execute trade signals
    GET  /trades   — Return all logged trades

Deploy on Railway with environment variables from .env.example.
"""

import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
load_dotenv()

TV_SESSION = os.getenv("TV_SESSION", "")
TV_SESSION2 = os.getenv("TV_SESSION2", "")
TV_ACCOUNT_ID = os.getenv("TV_ACCOUNT_ID", "")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "mysecret123")
TRADE_SIZE = float(os.getenv("TRADE_SIZE", "0.05"))
PORT = int(os.getenv("PORT", "8000"))

# TradingView internal Paper Trading API base
TV_API_BASE = "https://paper-trading.tradingview.com/trading"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("gold-scalper")

# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="XAUUSD Gold Scalper Bot",
    description="Webhook server for automated XAUUSD paper trading",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory trade log
# ---------------------------------------------------------------------------
trade_log: list[dict] = []

# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class WebhookPayload(BaseModel):
    secret: str
    action: str  # BUY or SELL
    price: float
    sl: Optional[float] = None
    tp: Optional[float] = None
    lots: Optional[float] = None


class TradeRecord(BaseModel):
    id: str
    timestamp: str
    action: str
    price: float
    sl: Optional[float] = None
    tp: Optional[float] = None
    lots: float
    status: str
    tv_response: Optional[dict] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# TradingView Paper Trading API Helper
# ---------------------------------------------------------------------------

def build_tv_cookies() -> dict:
    """Build the cookie dict required for TradingView API auth."""
    return {
        "sessionid": TV_SESSION,
        "sessionid_sign": TV_SESSION2,
    }


def place_tv_order(action: str, price: float, lots: float,
                   sl: Optional[float] = None,
                   tp: Optional[float] = None) -> dict:
    """
    Place an order on TradingView Paper Trading via its internal API.

    Uses the /trading/{account_id}/orders endpoint with session cookies
    for authentication. This is TradingView's undocumented internal API.

    Args:
        action: "BUY" or "SELL"
        price:  current price of XAUUSD
        lots:   position size in lots (e.g. 0.05)
        sl:     stop-loss price (optional)
        tp:     take-profit price (optional)

    Returns:
        dict with the API response or error details
    """
    if not all([TV_SESSION, TV_SESSION2, TV_ACCOUNT_ID]):
        logger.warning("TradingView credentials not set — logging trade only")
        return {
            "status": "simulated",
            "message": "TV credentials not configured; trade logged but not placed",
        }

    # Map action to TradingView side
    side = "buy" if action.upper() == "BUY" else "sell"

    # Build the order payload for TradingView Paper Trading
    order_payload = {
        "symbol": "OANDA:XAUUSD",
        "brokerSymbol": "OANDA:XAUUSD",
        "side": side,
        "type": "market",
        "qty": lots,
        "requestId": str(uuid.uuid4()),
        "currentAsk": price + 0.50 if side == "buy" else price,
        "currentBid": price if side == "buy" else price - 0.50,
    }

    # Add stop-loss if provided
    if sl is not None:
        order_payload["stopLoss"] = sl

    # Add take-profit if provided
    if tp is not None:
        order_payload["takeProfit"] = tp

    url = f"{TV_API_BASE}/{TV_ACCOUNT_ID}/orders"
    cookies = build_tv_cookies()
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://www.tradingview.com",
        "Referer": "https://www.tradingview.com/",
    }

    try:
        resp = requests.post(url, data=order_payload, cookies=cookies,
                             headers=headers, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        logger.info(f"TV order placed: {action} {lots} lots @ {price} — {result}")
        return {"status": "ok", "tv_response": result}
    except requests.exceptions.HTTPError as e:
        logger.error(f"TV API HTTP error: {e} — Response: {e.response.text}")
        return {"status": "error", "error": str(e), "body": e.response.text}
    except requests.exceptions.RequestException as e:
        logger.error(f"TV API request failed: {e}")
        return {"status": "error", "error": str(e)}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
async def health_check():
    """Health check — Railway and monitoring agents poll this."""
    return {"status": "running"}


@app.post("/webhook")
async def receive_webhook(payload: WebhookPayload):
    """
    Receive a trading signal and place a paper trade.

    Validates the webhook secret, places an order via TradingView Paper
    Trading API, and logs the trade.
    """
    # 1. Validate secret
    if payload.secret != WEBHOOK_SECRET:
        logger.warning(f"Invalid secret received: {payload.secret[:4]}***")
        raise HTTPException(status_code=403, detail="Invalid webhook secret")

    # 2. Validate action
    action = payload.action.upper()
    if action not in ("BUY", "SELL"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action '{payload.action}'. Must be BUY or SELL.",
        )

    # 3. Use provided lots or default from env
    lots = payload.lots if payload.lots is not None else TRADE_SIZE

    # 4. Place the order on TradingView Paper Trading
    tv_result = place_tv_order(
        action=action,
        price=payload.price,
        lots=lots,
        sl=payload.sl,
        tp=payload.tp,
    )

    # 5. Log the trade
    trade = {
        "id": str(uuid.uuid4())[:8],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "price": payload.price,
        "sl": payload.sl,
        "tp": payload.tp,
        "lots": lots,
        "status": tv_result.get("status", "unknown"),
        "tv_response": tv_result.get("tv_response"),
        "error": tv_result.get("error"),
    }
    trade_log.append(trade)
    logger.info(
        f"Trade logged: {trade['id']} — {action} {lots} lots @ {payload.price}"
    )

    return {"status": "ok", "trade": trade}


@app.get("/trades")
async def get_trades():
    """Return all logged trades. Polled by the Monitor Agent every 60s."""
    return {
        "total": len(trade_log),
        "trades": trade_log,
    }


# ---------------------------------------------------------------------------
# Entry point (for local dev — Railway uses Dockerfile CMD)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=PORT, reload=True)
