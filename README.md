# Kite Trading API Service

This project provides a comprehensive, FastAPI-based backend service to interact with the Zerodha Kite Connect API. It is designed to serve as a robust backend for trading applications, offering a clean, modern API for complex operations like authentication, data fetching, risk calculation, and full order management.

The application is built for easy local setup and is pre-configured for deployment on the Render platform.

## Features

- **Dual-Layer Authentication:**
    - **Service-Level:** All protected endpoints are secured by a static `x-api-key` header.
    - **User-Level:** A simple flow to get a Kite Connect session `access_token`.
- **Smarter Market Data Endpoints:**
  - Get real-time quotes for any instrument. **Now supports symbols with or without an exchange prefix (e.g., `INFY` or `NSE:INFY`).**
  - Fetch historical OHLC candle data. **Now supports instrument tokens or symbol strings, plus interval shorthands (e.g., `5m`, `1h`).**
  - Search for a specific instrument to get its token and details.
- **Risk & Target Calculation:**
  - A `/target/calc` endpoint that uses ATR to calculate realistic stop-loss and target levels.
  - A `/risk/check` endpoint to calculate cash risk for a potential trade.
- **Complete Order Management:**
  - Place, modify, and cancel orders using a consistent JSON-based request structure.
- **Webhook Subscriptions:** Subscribe a URL to receive real-time updates on order status changes.
- **Deployment Ready:** Includes a `render.yaml` and uses environment variables for all secrets.
- **Health Check:** A `/health` endpoint for monitoring service uptime.

---

## Local Setup

### 1. Prerequisites
- Python 3.8+
- A Zerodha Kite Developer account with an `api_key` and `api_secret`.

### 2. Installation
```bash
git clone <repository_url>
cd <repository_name>
pip install -r requirements.txt
```

### 3. Environment Variables
Set the following environment variables.

**On macOS/Linux:**
```bash
export KITE_API_KEY='your_kite_api_key'
export KITE_API_SECRET='your_kite_api_secret'
export INTERNAL_API_KEY='a_strong_secret_key_of_your_choice'
```

### 4. Running the Application
```bash
uvicorn kite_live_data.main:app --host 0.0.0.0 --port 8000
```
The API and its interactive documentation will be available at `http://localhost:8000/docs`.

---

## API Usage

### API Security
All endpoints (except for the public `/health` and `/auth/...` routes) are protected. You must include your `INTERNAL_API_KEY` in the `x-api-key` header with every request.

Example with `curl`:
```bash
curl -X GET "http://localhost:8000/quote?symbol=NSE:INFY" -H "x-api-key: your_strong_secret_key_of_your_choice"
```

### Authentication Flow
1.  **Get Login URL:** Call `GET /auth/login_url`.
2.  **Log In:** Open the URL in a browser and log in.
3.  **Handle Callback:** Kite will redirect you to this API's `/auth/callback` endpoint. You must have this URL (`http://<your_server>/auth/callback`) configured in your Kite App settings.
4.  **Session Created:** The API will handle the token exchange. You can now use the authenticated endpoints.

### API Documentation
Visit `http://localhost:8000/docs` for a full interactive API specification. The "Authorize" button in the Swagger UI can be used to set the `x-api-key` for all test requests.

---

## Deployment on Render

1.  **Push to Git:** Ensure your code is in a GitHub or GitLab repository.
2.  **Create Blueprint Service:** On the Render dashboard, create a new "Blueprint" service and connect your repository. Render will use `render.yaml` automatically.
3.  **Add Environment Variables:** In your service's "Environment" tab on Render, add your secrets:
    -   `KITE_API_KEY`
    -   `KITE_API_SECRET`
    -   `INTERNAL_API_KEY` (Choose a strong, random string for this)
4.  **Deploy.** Your API will be available at the URL provided by Render.
