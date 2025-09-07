import pytest
from fastapi.testclient import TestClient
import os
import sys

# Add the project root to the Python path to allow for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set dummy environment variables for testing
os.environ["KITE_API_KEY"] = "test_kite_api_key"
os.environ["KITE_API_SECRET"] = "test_kite_api_secret"
os.environ["INTERNAL_API_KEY"] = "test_internal_api_key"

# This needs to be imported AFTER setting the env vars
from kite_live_data.main import app

@pytest.fixture(scope="module")
def test_client():
    """
    Creates a FastAPI TestClient that can be used in tests.
    """
    with TestClient(app) as client:
        yield client

@pytest.fixture(scope="module")
def test_api_key():
    """
    Provides the test API key for use in test requests.
    """
    return os.environ["INTERNAL_API_KEY"]

@pytest.fixture(scope="function")
def authenticated_client(test_client: TestClient, mocker):
    """
    Provides a TestClient that is already authenticated with a mock Kite session.
    This avoids repeating the auth flow in every test.
    Also handles session teardown.
    """
    # Mock a successful session generation
    mock_session_data = {
        "access_token": "a_real_access_token",
        "user_id": "AB1234",
        "public_token": "a_public_token"
    }
    mocker.patch("kite_live_data.main.kite.generate_session", return_value=mock_session_data)

    # Perform the callback to set the session state on the server
    test_client.get("/auth/callback?request_token=a_fake_request_token")

    yield test_client

    # Teardown: reset the session after the test runs
    from kite_live_data.main import session
    session.update({"access_token": None, "expires_at": None, "user_id": None})

@pytest.fixture(scope="function")
def reset_session():
    """
    Fixture to reset the session state before a test.
    """
    from kite_live_data.main import session
    session.update({"access_token": None, "expires_at": None, "user_id": None})
