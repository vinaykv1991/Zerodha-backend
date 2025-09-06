from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Security
from fastapi.security import APIKeyHeader
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, HttpUrl
import logging
import os
import datetime
import uuid
import requests
from kiteconnect import KiteConnect
from typing import List, Dict, Any
import pandas as pd
import pandas_ta as ta

# --- Setup ---
logging.basicConfig(level=logging.DEBUG)
app = FastAPI(
    title="Kite Trading API",
    description="A FastAPI service to interact with the Zerodha Kite Connect API.",
    version="1.0.0"
)

# --- API Keys & Secrets ---
KITE_API_KEY = os.environ.get("KITE_API_KEY")
KITE_API_SECRET = os.environ.get("KITE_API_SECRET")
INTERNAL_API_KEY = os.environ.get("INTERNAL_API_KEY")

if not KITE_API_KEY or not KITE_API_SECRET: raise RuntimeError("KITE_API_KEY and KITE_API_SECRET must be set.")
if not INTERNAL_API_KEY: raise RuntimeError("INTERNAL_API_KEY for API security must be set.")

kite = KiteConnect(api_key=KITE_API_KEY)
api_key_header = APIKeyHeader(name="x-api-key", auto_error=True)

# --- In-memory storage ---
session = {"access_token": None, "expires_at": None, "user_id": None}
instrument_cache = {"instruments": [], "last_updated": None}
webhook_subscriptions: Dict[str, HttpUrl] = {}
start_time = datetime.datetime.now()

# --- Pydantic Models ---
class HealthResponse(BaseModel): ok: bool; uptime: str
class AuthStatusResponse(BaseModel): connected: bool; expires_at: datetime.datetime | None = None
class QuoteResponse(BaseModel): symbol: str; last_price: float; volume: int; timestamp: datetime.datetime
class Candle(BaseModel): time: datetime.datetime; open: float; high: float; low: float; close: float; volume: int
class InstrumentResponse(BaseModel): tradingsymbol: str; token: int; lot_size: int; exchange: str
class TargetCalcRequest(BaseModel):
    symbol: str; entry_price: float; sl_atr_multiplier: float = 1.5; target_atr_multiplier: float = 3.0
class TargetCalcResponse(BaseModel): entry: float; stop_loss: float; target1: float; target2: float; rr_ratio: float
class OrderLeg(BaseModel): type: str; value: float
class PlaceOrderRequest(BaseModel):
    symbol: str; transaction_type: str; quantity: int; order_type: str
    product: str; price: float | None = None; trigger_price: float | None = None
    sl: OrderLeg | None = None; target: OrderLeg | None = None
class ModifyOrderRequest(BaseModel):
    order_id: str; quantity: int | None = None; price: float | None = None;
    trigger_price: float | None = None; order_type: str | None = None
class CancelOrderRequest(BaseModel): order_id: str
class OrderResponse(BaseModel): order_id: str; status: str
class WebhookRequest(BaseModel): url: HttpUrl
class WebhookResponse(BaseModel): ok: bool; webhook_id: str
class Position(BaseModel): symbol: str; qty: int; avg_price: float; pnl: float
class RiskCheckRequest(BaseModel): entry: float; stop_loss: float; quantity: int
class RiskCheckResponse(BaseModel): cash_risk: float; margin_required: float; rr_ratio: float | None = None

# --- Security & Dependencies ---
async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")

def check_kite_auth():
    is_connected = session.get("access_token") and session.get("expires_at") and session["expires_at"] > datetime.datetime.now()
    if not is_connected: raise HTTPException(status_code=401, detail="Kite session not authenticated.")
    kite.set_access_token(session["access_token"])

# --- Helper Functions ---
def get_token_expiry_time() -> datetime.datetime:
    now = datetime.datetime.now()
    return (now + datetime.timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)

def send_webhook_update(payload: dict):
    for url in webhook_subscriptions.values():
        try: requests.post(str(url), json=payload, timeout=5)
        except requests.RequestException as e: logging.error(f"Failed to send webhook to {url}: {e}")

def update_instrument_cache_if_needed():
    if not instrument_cache.get("last_updated") or (datetime.datetime.now() - instrument_cache["last_updated"]).days >= 1:
        try:
            instrument_cache["instruments"] = kite.instruments()
            instrument_cache["last_updated"] = datetime.datetime.now()
        except Exception as e: logging.error(f"Could not update instrument cache: {e}")

def get_instrument_token(symbol: str) -> int | None:
    update_instrument_cache_if_needed()
    try:
        exchange, tradingsymbol = symbol.split(':')
        for inst in instrument_cache["instruments"]:
            if inst['tradingsymbol'] == tradingsymbol and inst['exchange'] == exchange:
                return inst['instrument_token']
    except ValueError: pass
    return None

# --- API Endpoints ---
@app.get("/")
def read_root(): return {"message": "Welcome to the Kite Trading API"}

@app.get("/health", response_model=HealthResponse)
def health_check():
    uptime_delta = datetime.datetime.now() - start_time
    return {"ok": True, "uptime": str(uptime_delta)}

# Simplified Authentication Flow
@app.get("/auth/login_url")
def get_login_url():
    """Generates the Kite Connect login URL."""
    return {"login_url": kite.login_url()}

@app.get("/auth/callback", response_class=HTMLResponse)
def auth_callback(request_token: str):
    """
    Handles the callback from Kite, exchanges the token, and sets the session.
    You must set your Kite App's Redirect URL to this endpoint.
    """
    try:
        data = kite.generate_session(request_token, api_secret=api_secret)
        session.update(access_token=data["access_token"], user_id=data["user_id"], expires_at=get_token_expiry_time())
        kite.set_access_token(session["access_token"])
        return """<html><body><h1>Authentication Successful!</h1><p>You can now close this window and use the API.</p></body></html>"""
    except Exception as e:
        return f"""<html><body><h1>Authentication Failed</h1><p>Error: {e}</p></body></html>"""

@app.get("/auth/status", response_model=AuthStatusResponse, dependencies=[Depends(verify_api_key)])
def get_auth_status():
    is_connected = session.get("access_token") and session.get("expires_at") and session["expires_at"] > datetime.datetime.now()
    return {"connected": is_connected, "expires_at": session.get("expires_at")}

@app.post("/webhook/subscribe", response_model=WebhookResponse, dependencies=[Depends(verify_api_key)])
def subscribe_webhook(request: WebhookRequest, auth: None = Depends(check_kite_auth)):
    webhook_id = str(uuid.uuid4())
    webhook_subscriptions[webhook_id] = request.url
    return {"ok": True, "webhook_id": webhook_id}

@app.get("/quote", response_model=QuoteResponse, dependencies=[Depends(verify_api_key)])
def get_quote(symbol: str, auth: None = Depends(check_kite_auth)):
    """
    Gets a quote for a given symbol. If exchange is not specified, defaults to NSE.
    """
    formatted_symbol = symbol
    if ":" not in symbol:
        # If no exchange is specified, default to NSE.
        # A more robust implementation might search for the instrument first.
        formatted_symbol = f"NSE:{symbol.upper()}"

    try:
        quote_data = kite.quote(formatted_symbol)
        instrument_quote = quote_data.get(formatted_symbol)
        if not instrument_quote:
            raise HTTPException(status_code=404, detail=f"Quote not found for symbol: {formatted_symbol}")

        # The quote response from kite has 'tradingsymbol' which we can use
        return QuoteResponse(symbol=instrument_quote['tradingsymbol'], **instrument_quote)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/historical", response_model=List[Candle], dependencies=[Depends(verify_api_key)])
def get_historical_data(symbol: str, interval: str, from_date: str, to_date: str, auth: None = Depends(check_kite_auth)):
    """
    Gets historical candle data.
    'symbol' can be an instrument token (e.g., "12345") or a symbol string (e.g., "NSE:INFY").
    'interval' can use shorthands like '5m', '1h', '1d'.
    """
    # Handle interval shorthands
    interval_map = {
        "5m": "5minute", "15m": "15minute", "1h": "60minute", "1d": "day"
    }
    final_interval = interval_map.get(interval, interval)

    # Determine if symbol is a token or a string
    if symbol.isdigit():
        instrument_token = int(symbol)
    else:
        instrument_token = get_instrument_token(symbol)

    if not instrument_token:
        raise HTTPException(status_code=404, detail=f"Instrument not found for symbol/token: {symbol}")

    try:
        records = kite.historical_data(instrument_token, from_date, to_date, final_interval)
        return [Candle(time=r['date'], **r) for r in records]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/instruments", response_model=InstrumentResponse, dependencies=[Depends(verify_api_key)])
def search_instruments(query: str, auth: None = Depends(check_kite_auth)):
    update_instrument_cache_if_needed()
    query = query.upper()
    for inst in instrument_cache["instruments"]:
        if query == inst['tradingsymbol'].upper():
            return InstrumentResponse(tradingsymbol=inst['tradingsymbol'], token=inst['instrument_token'], lot_size=inst['lot_size'], exchange=inst['exchange'])
    raise HTTPException(status_code=404, detail=f"Instrument '{query}' not found.")

@app.post("/target/calc", response_model=TargetCalcResponse, dependencies=[Depends(verify_api_key)])
def calculate_target(request: TargetCalcRequest, auth: None = Depends(check_kite_auth)):
    instrument_token = get_instrument_token(request.symbol)
    if not instrument_token: raise HTTPException(status_code=404, detail=f"Instrument not found: {request.symbol}")
    to_date = datetime.date.today(); from_date = to_date - datetime.timedelta(days=45)
    try:
        hist_data = kite.historical_data(instrument_token, from_date.strftime('%Y-%m-%d'), to_date.strftime('%Y-%m-%d'), "day")
        if not hist_data: raise HTTPException(status_code=404, detail="Could not fetch historical data for ATR.")
        df = pd.DataFrame(hist_data); df.set_index('date', inplace=True)
        atr = df.ta.atr(length=14)
        if atr is None or atr.empty: raise HTTPException(status_code=500, detail="Could not calculate ATR.")
        latest_atr = atr.iloc[-1]

        stop_loss_points = request.sl_atr_multiplier * latest_atr
        target_points = request.target_atr_multiplier * latest_atr

        stop_loss = round(request.entry_price - stop_loss_points, 2)
        target1 = round(request.entry_price + target_points, 2)

        risk = request.entry_price - stop_loss
        reward = target1 - request.entry_price
        rr_ratio = round(reward / risk, 2) if risk > 0 else 0

        return TargetCalcResponse(entry=request.entry_price, stop_loss=stop_loss, target1=target1, target2=round(target1 + (target_points / 2), 2), rr_ratio=rr_ratio)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/place_order", response_model=OrderResponse, dependencies=[Depends(verify_api_key)])
def place_order(request: PlaceOrderRequest, background_tasks: BackgroundTasks, auth: None = Depends(check_kite_auth)):
    try:
        exchange, tradingsymbol = request.symbol.split(':')

        params = {
            "variety": kite.VARIETY_REGULAR, "exchange": exchange, "tradingsymbol": tradingsymbol,
            "transaction_type": request.transaction_type, "quantity": request.quantity,
            "product": request.product, "order_type": request.order_type, "price": request.price,
            "trigger_price": request.trigger_price
        }
        if request.product == kite.PRODUCT_BO and request.sl and request.target:
            params['squareoff'] = request.target.value
            params['stoploss'] = request.sl.value
            if request.order_type != kite.ORDER_TYPE_LIMIT:
                raise HTTPException(status_code=400, detail="Bracket Orders must be of LIMIT type.")

        order_id = kite.place_order(**params)
        response = {"order_id": order_id, "status": "PLACED"}
        background_tasks.add_task(send_webhook_update, payload=response)
        return OrderResponse(**response)
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@app.post("/modify_order", response_model=OrderResponse, dependencies=[Depends(verify_api_key)])
def modify_order(request: ModifyOrderRequest, background_tasks: BackgroundTasks, auth: None = Depends(check_kite_auth)):
    try:
        order_id = kite.modify_order(variety=kite.VARIETY_REGULAR, order_id=request.order_id, quantity=request.quantity,
                                     price=request.price, trigger_price=request.trigger_price, order_type=request.order_type)
        response = {"order_id": order_id, "status": "MODIFIED"}
        background_tasks.add_task(send_webhook_update, payload=response)
        return OrderResponse(**response)
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@app.post("/cancel_order", response_model=OrderResponse, dependencies=[Depends(verify_api_key)])
def cancel_order(request: CancelOrderRequest, background_tasks: BackgroundTasks, auth: None = Depends(check_kite_auth)):
    try:
        order_id = kite.cancel_order(variety=kite.VARIETY_REGULAR, order_id=request.order_id)
        response = {"order_id": order_id, "status": "CANCELLED"}
        background_tasks.add_task(send_webhook_update, payload=response)
        return OrderResponse(**response)
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@app.get("/orders", dependencies=[Depends(verify_api_key)])
def get_orders(auth: None = Depends(check_kite_auth)):
    try: return kite.orders()
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/positions", response_model=List[Position], dependencies=[Depends(verify_api_key)])
def get_positions(auth: None = Depends(check_kite_auth)):
    try:
        net_positions = kite.positions().get('net', [])
        return [Position(symbol=p['tradingsymbol'], qty=p['quantity'], avg_price=p['average_price'], pnl=p['pnl'])
                for p in net_positions if p.get('product') == 'MIS' and p.get('quantity') != 0]
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/risk/check", response_model=RiskCheckResponse, dependencies=[Depends(verify_api_key)])
def check_risk(request: RiskCheckRequest, auth: None = Depends(check_kite_auth)):
    cash_risk = (request.entry - request.stop_loss) * request.quantity
    margin_required = request.entry * request.quantity
    return RiskCheckResponse(cash_risk=round(cash_risk, 2), margin_required=round(margin_required, 2), rr_ratio=None)
