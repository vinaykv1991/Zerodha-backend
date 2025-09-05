from fastapi import FastAPI, HTTPException
from kiteconnect import KiteConnect
from pydantic import BaseModel
import logging
from typing import List
import datetime
import os

# Setup logging
logging.basicConfig(level=logging.DEBUG)

app = FastAPI()

# Get API key and secret from environment variables
api_key = os.environ.get("KITE_API_KEY")
api_secret = os.environ.get("KITE_API_SECRET")

if not api_key or not api_secret:
    raise RuntimeError("KITE_API_KEY and KITE_API_SECRET environment variables must be set.")

kite = KiteConnect(api_key=api_key)
access_token = None

class Instruments(BaseModel):
    instrument_tokens: List[str]

@app.get("/")
def read_root():
    return {"message": "Kite Live Data API"}

@app.get("/login")
def login():
    login_url = kite.login_url()
    return {"login_url": login_url}

@app.get("/callback")
def callback(request_token: str):
    global access_token
    try:
        data = kite.generate_session(request_token, api_secret=api_secret)
        access_token = data["access_token"]
        kite.set_access_token(access_token)
        return {"status": "success", "user_id": data["user_id"]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error generating session: {e}")

def check_access_token():
    if not access_token:
        raise HTTPException(status_code=401, detail="Access token not found. Please login first.")

@app.get("/profile")
def get_profile():
    check_access_token()
    try:
        profile = kite.profile()
        return profile
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching profile: {e}")

@app.get("/instruments/{exchange}")
def get_instruments(exchange: str):
    check_access_token()
    try:
        instruments = kite.instruments(exchange)
        return instruments
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching instruments: {e}")

@app.post("/ltp")
def get_ltp(instruments: Instruments):
    check_access_token()
    try:
        ltp = kite.ltp(instruments.instrument_tokens)
        return ltp
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching LTP: {e}")

@app.post("/ohlc")
def get_ohlc(instruments: Instruments):
    check_access_token()
    try:
        ohlc = kite.ohlc(instruments.instrument_tokens)
        return ohlc
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching OHLC: {e}")

@app.post("/quote")
def get_quote(instruments: Instruments):
    check_access_token()
    try:
        quote = kite.quote(instruments.instrument_tokens)
        return quote
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching quote: {e}")

@app.get("/historical-data/{instrument_token}")
def get_historical_data(instrument_token: int, from_date: str, to_date: str, interval: str):
    check_access_token()
    try:
        # Convert date strings to datetime objects
        from_date_obj = datetime.datetime.strptime(from_date, "%Y-%m-%d")
        to_date_obj = datetime.datetime.strptime(to_date, "%Y-%m-%d")

        historical_data = kite.historical_data(instrument_token, from_date_obj, to_date_obj, interval)
        return historical_data
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching historical data: {e}")
