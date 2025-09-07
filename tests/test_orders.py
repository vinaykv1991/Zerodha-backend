import pytest
from fastapi.testclient import TestClient
from datetime import datetime

# --- /target/calc endpoint tests ---

def test_calculate_target_success(authenticated_client: TestClient, test_api_key: str, mocker):
    """Tests a successful target calculation."""
    mocker.patch("kite_live_data.main.get_instrument_token", return_value=12345)
    mock_historical = [{"date": datetime.now().isoformat(), "open": 100, "high": 110, "low": 90, "close": c} for c in range(100, 115)]
    mocker.patch("kite_live_data.main.kite.historical_data", return_value=mock_historical)
    request_data = {"symbol": "NSE:RELIANCE", "entry_price": 110.0}
    headers = {"x-api-key": test_api_key}
    response = authenticated_client.post("/target/calc", headers=headers, json=request_data)
    assert response.status_code == 200
    assert "stop_loss" in response.json()

# --- /risk/check endpoint tests ---

def test_risk_check_success(authenticated_client: TestClient, test_api_key: str):
    """Tests a successful risk check calculation."""
    request_data = {"entry": 100.0, "stop_loss": 98.0, "quantity": 50}
    headers = {"x-api-key": test_api_key}
    response = authenticated_client.post("/risk/check", headers=headers, json=request_data)
    assert response.status_code == 200
    assert response.json()["cash_risk"] == 100.0

# --- Order Management endpoint tests ---

def test_place_order_success(authenticated_client: TestClient, test_api_key: str, mocker):
    """Tests successful order placement."""
    mock_order_id = "240101000000001"
    mocker.patch("kite_live_data.main.kite.place_order", return_value=mock_order_id)
    request_data = {
        "symbol": "NSE:INFY", "transaction_type": "BUY", "quantity": 1,
        "order_type": "MARKET", "product": "MIS", "sl": None, "target": None
    }
    headers = {"x-api-key": test_api_key}
    response = authenticated_client.post("/place_order", headers=headers, json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert data["order_id"] == mock_order_id

def test_place_bracket_order_success(authenticated_client: TestClient, test_api_key: str, mocker):
    """Tests successful bracket order placement."""
    mock_place_order = mocker.patch("kite_live_data.main.kite.place_order", return_value="240101000000002")

    request_data = {
        "symbol": "NSE:SBIN",
        "transaction_type": "BUY",
        "quantity": 1,
        "order_type": "LIMIT",
        "product": "BO",
        "price": 500.0,
        "sl": {"type": "absolute", "value": 495.0},
        "target": {"type": "absolute", "value": 510.0}
    }
    headers = {"x-api-key": test_api_key}
    response = authenticated_client.post("/place_order", headers=headers, json=request_data)

    assert response.status_code == 200
    mock_place_order.assert_called_once()
    call_args = mock_place_order.call_args[1]
    assert call_args["product"] == "BO"
    assert call_args["stoploss"] == 495.0
    assert call_args["squareoff"] == 510.0

def test_get_orders_success(authenticated_client: TestClient, test_api_key: str, mocker):
    """Tests fetching the order book."""
    mock_orders = [{"order_id": "123", "status": "COMPLETE"}]
    mocker.patch("kite_live_data.main.kite.orders", return_value=mock_orders)
    headers = {"x-api-key": test_api_key}
    response = authenticated_client.get("/orders", headers=headers)
    assert response.status_code == 200
    assert response.json() == mock_orders

def test_get_positions_success(authenticated_client: TestClient, test_api_key: str, mocker):
    """Tests fetching current positions."""
    mock_positions = {"net": [{"tradingsymbol": "INFY", "quantity": 10, "average_price": 1500, "pnl": 100, "product": "MIS"}]}
    mocker.patch("kite_live_data.main.kite.positions", return_value=mock_positions)
    headers = {"x-api-key": test_api_key}
    response = authenticated_client.get("/positions", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["symbol"] == "INFY"
