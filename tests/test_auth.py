import pytest
from fastapi.testclient import TestClient

def test_health_check(test_client: TestClient):
    """Tests the public /health endpoint."""
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "uptime" in data

def test_login_url(test_client: TestClient, mocker):
    """Tests the /auth/login_url endpoint."""
    # Mock the external call to kite.login_url
    mock_login_url = "https://kite.zerodha.com/connect/login?api_key=test_kite_api_key"
    mocker.patch("kite_live_data.main.kite.login_url", return_value=mock_login_url)

    response = test_client.get("/auth/login_url")
    assert response.status_code == 200
    assert response.json() == {"login_url": mock_login_url}

def test_auth_callback_success(test_client: TestClient, mocker):
    """Tests the /auth/callback endpoint with a successful token exchange."""
    # Mock the external call to kite.generate_session
    mock_session_data = {
        "access_token": "a_real_access_token",
        "user_id": "AB1234"
    }
    mocker.patch("kite_live_data.main.kite.generate_session", return_value=mock_session_data)

    response = test_client.get("/auth/callback?request_token=a_fake_request_token")
    assert response.status_code == 200
    assert "Authentication Successful!" in response.text

def test_auth_callback_failure(test_client: TestClient, mocker):
    """Tests the /auth/callback endpoint with a failed token exchange."""
    # Mock the external call to raise an exception
    mocker.patch("kite_live_data.main.kite.generate_session", side_effect=Exception("Invalid token"))

    response = test_client.get("/auth/callback?request_token=an_invalid_request_token")
    assert response.status_code == 200 # The endpoint itself returns a 200 with HTML
    assert "Authentication Failed" in response.text
    assert "Invalid token" in response.text

def test_auth_status_unauthenticated(test_client: TestClient, test_api_key: str, reset_session):
    """Tests the /auth/status endpoint when not authenticated."""
    headers = {"x-api-key": test_api_key}
    response = test_client.get("/auth/status", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is False
    assert data["expires_at"] is None

def test_api_key_security(test_client: TestClient):
    """Tests that protected endpoints require a valid x-api-key."""
    # No API key
    response = test_client.get("/auth/status")
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"

    # Incorrect API key
    headers = {"x-api-key": "wrong_key"}
    response = test_client.get("/auth/status", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API Key"
