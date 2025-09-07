import pytest
from fastapi.testclient import TestClient
from datetime import datetime

# --- /quote endpoint tests ---

def test_get_quote_success(authenticated_client: TestClient, test_api_key: str, mocker):
    """Tests a successful quote fetch."""
    symbol = "NSE:INFY"
    mock_depth = {"buy": [{"quantity": 10, "price": 1499.0, "orders": 1}], "sell": []}
    mock_quote = {
        symbol: {
            "instrument_token": 123, "last_price": 1500.0, "volume": 100000,
            "timestamp": datetime.now().isoformat(), "tradingsymbol": "INFY", "depth": mock_depth
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

def test_get_quote_smart_symbol(authenticated_client: TestClient, test_api_key: str, mocker):
    """Tests the smart symbol handling (no exchange prefix)."""
    input_symbol = "infy"
    expected_formatted_symbol = "NSE:INFY"
    mock_depth = {"buy": [], "sell": []}
    mock_quote = {
        expected_formatted_symbol: {
            "instrument_token": 123, "last_price": 1500.0, "volume": 100000,
            "timestamp": datetime.now().isoformat(), "tradingsymbol": "INFY", "depth": mock_depth
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
