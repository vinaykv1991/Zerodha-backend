import pytest
from fastapi.testclient import TestClient
from datetime import datetime

# --- /quote endpoint tests ---

def test_get_quote_success(authenticated_client: TestClient, test_api_key: str, mocker):
    """Tests a successful quote fetch."""
    symbol = "NSE:INFY"
    mock_depth = {"buy": [{"quantity": 10, "price": 1499.0, "orders": 1}], "sell": []}
    mock_ohlc = {"open": 1490.0, "high": 1510.0, "low": 1485.0, "close": 1495.0}
    mock_quote = {
        symbol: {
            "instrument_token": 123, "last_price": 1500.0, "volume": 100000,
            "timestamp": datetime.now().isoformat(), "tradingsymbol": "INFY", "depth": mock_depth,
            "buy_quantity": 100, "sell_quantity": 200, "last_quantity": 10, "average_price": 1499.5,
            "last_trade_time": datetime.now().isoformat(), "oi": 1000, "oi_day_high": 1200, "oi_day_low": 800,
            "net_change": 5.0, "lower_circuit_limit": 1300.0, "upper_circuit_limit": 1700.0, "ohlc": mock_ohlc
        }
    }
    mocker.patch("kite_live_data.main.kite.quote", return_value=mock_quote)
    headers = {"x-api-key": test_api_key}
    response = authenticated_client.get(f"/quote?symbol={symbol}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "NSE:INFY"
    assert data["last_price"] == 1500.0
    assert "depth" in data
    assert data["depth"]["buy"][0]["price"] == 1499.0
    assert data["buy_quantity"] == 100
    assert data["instrument_token"] == 123
    assert data["net_change"] == 5.0
    assert data["ohlc"]["high"] == 1510.0

def test_get_quote_smart_symbol(authenticated_client: TestClient, test_api_key: str, mocker):
    """Tests the smart symbol handling (no exchange prefix)."""
    input_symbol = "infy"
    expected_formatted_symbol = "NSE:INFY"
    mock_depth = {"buy": [], "sell": []}
    mock_ohlc = {"open": 0, "high": 0, "low": 0, "close": 0}
    mock_quote = {
        expected_formatted_symbol: {
            "instrument_token": 123, "last_price": 1500.0, "volume": 100000,
            "timestamp": datetime.now().isoformat(), "tradingsymbol": "INFY", "depth": mock_depth,
            "buy_quantity": 0, "sell_quantity": 0, "last_quantity": 0, "average_price": 0,
            "last_trade_time": None, "oi": 0, "oi_day_high": 0, "oi_day_low": 0,
            "net_change": 0, "lower_circuit_limit": 0, "upper_circuit_limit": 0, "ohlc": mock_ohlc
        }
    }
    mocker.patch("kite_live_data.main.kite.quote", return_value=mock_quote)
    headers = {"x-api-key": test_api_key}
    response = authenticated_client.get(f"/quote?symbol={input_symbol}", headers=headers)
    assert response.status_code == 200
    assert response.json()["symbol"] == expected_formatted_symbol

def test_get_quote_not_found(authenticated_client: TestClient, test_api_key: str, mocker):
    """Tests the case where the quote is not found."""
    symbol = "NSE:NONEXISTENT"
    mocker.patch("kite_live_data.main.kite.quote", return_value={})
    headers = {"x-api-key": test_api_key}
    response = authenticated_client.get(f"/quote?symbol={symbol}", headers=headers)
    assert response.status_code == 404
    assert "Quote not found" in response.json()["detail"]

def test_get_quote_for_index(authenticated_client: TestClient, test_api_key: str, mocker):
    """Tests fetching a quote for a major index, which has fewer data points."""
    input_symbol = "nifty 50"
    expected_formatted_symbol = "INDICES:NIFTY 50"
    mock_ohlc = {"open": 17900, "high": 18100, "low": 17850, "close": 17950}
    mock_quote = {
        expected_formatted_symbol: {
            "instrument_token": 256265,
            "timestamp": datetime.now().isoformat(),
            "last_price": 18000.50,
            "net_change": 50.25,
            "ohlc": mock_ohlc,
        }
    }
    mocker.patch("kite_live_data.main.kite.quote", return_value=mock_quote)
    headers = {"x-api-key": test_api_key}
    response = authenticated_client.get(f"/quote?symbol={input_symbol}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == expected_formatted_symbol
    assert data["last_price"] == 18000.50
    assert data["volume"] is None
    assert data["depth"] is None
    assert data["oi"] is None
    assert data["ohlc"]["open"] == 17900

# --- /historical endpoint tests ---
def test_get_historical_success(authenticated_client: TestClient, test_api_key: str, mocker):
    mock_historical = [{"date": datetime.now().isoformat(), "open": 100, "high": 110, "low": 90, "close": 105, "volume": 1000}]
    mocker.patch("kite_live_data.main.kite.historical_data", return_value=mock_historical)
    mocker.patch("kite_live_data.main.get_instrument_token", return_value=12345)
    headers = {"x-api-key": test_api_key}
    url = "/historical?symbol=NSE:RELIANCE&interval=5m&from_date=2024-01-01&to_date=2024-01-02"
    response = authenticated_client.get(url, headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1

# --- /instruments endpoint tests ---
def test_search_instruments_success(authenticated_client: TestClient, test_api_key: str, mocker):
    mock_instruments = [{"tradingsymbol": "RELIANCE", "instrument_token": 123, "lot_size": 1, "exchange": "NSE"}]
    mocker.patch("kite_live_data.main.kite.instruments", return_value=mock_instruments)
    mocker.patch("kite_live_data.main.instrument_cache", {"instruments": [], "last_updated": None})
    headers = {"x-api-key": test_api_key}
    response = authenticated_client.get("/instruments?query=RELIANCE", headers=headers)
    assert response.status_code == 200
    assert response.json()["tradingsymbol"] == "RELIANCE"
