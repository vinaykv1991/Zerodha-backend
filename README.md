# Kite Trading API Service

This project provides a comprehensive, FastAPI-based backend service to interact with the Zerodha Kite Connect API. It is designed to serve as a robust backend for trading applications, offering a clean, modern API for complex operations like authentication, data fetching, risk calculation, and full order management.

The application is built for easy local setup and is pre-configured for one-click deployment on the Render platform.

## Features

- **Full Authentication Flow:** Securely exchange a `request_token` for a session `access_token` and check session status.
- **Advanced Market Data:**
  - Get real-time quotes for any instrument.
  - Fetch historical OHLC candle data.
  - Search for a specific instrument to get its token and details.
- **Risk & Target Calculation:**
  - A `/target/calc` endpoint that uses ATR (Average True Range) to calculate realistic stop-loss and target levels for a trade, with configurable multipliers.
  - A `/risk/check` endpoint to calculate cash risk for a potential trade.
- **Complete Order Management:**
  - Place, modify, and cancel orders using a consistent JSON-based request structure.
  - Support for MIS and Bracket Orders (BO).
  - View a list of all recent orders and current open positions.
- **Webhook Subscriptions:** Subscribe a URL to receive real-time updates on order status changes.
- **Deployment Ready:** Includes a `render.yaml` for seamless deployment and uses environment variables for secure management of API keys.
- **Health Check:** A `/health` endpoint for monitoring service uptime and readiness.

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

Set the following environment variables with your Kite API credentials:

**On macOS/Linux:**
```bash
export KITE_API_KEY='your_api_key'
export KITE_API_SECRET='your_api_secret'
```

### 4. Running the Application

```bash
uvicorn kite_live_data.main:app --host 0.0.0.0 --port 8000
```
The API and its interactive documentation will be available at `http://localhost:8000/docs`.

---

## Authentication Flow

1.  **Get Login URL:** Call `GET /auth/login_url`. This will return the URL for the Kite Connect login page.
2.  **Log In:** Open the URL in a browser and log in with your Zerodha credentials.
3.  **Handle Callback:** After logging in, Kite will redirect you to the callback URL you configured in your Kite App settings. **You must set this URL to point to this API's `/auth/callback` endpoint.** For local testing, this would be `http://localhost:8000/auth/callback`.
4.  **Session Created:** The `/auth/callback` endpoint automatically exchanges the received `request_token` for an `access_token` and creates a session. Your browser will show a "success" message. You can now use the other API endpoints.

## API Documentation

All endpoints are documented via the automatically generated Swagger UI. Once the server is running, visit `http://localhost:8000/docs` to see a full interactive API specification and to test the endpoints.

### Key Endpoints

- **Auth:** `GET /auth/login_url`, `GET /auth/callback`, `GET /auth/status`
- **Market Data:** `GET /quote`, `GET /historical`, `GET /instruments`
- **Risk/Target:** `POST /target/calc`, `POST /risk/check`
- **Orders:** `POST /place_order`, `POST /modify_order`, `POST /cancel_order`
- **Positions:** `GET /orders`, `GET /positions`
- **Webhooks:** `POST /webhook/subscribe`
- **Monitoring:** `GET /health`

---

## Deployment on Render

This repository is ready for deployment on Render.

1.  **Push to Git:** Ensure your code is in a GitHub or GitLab repository.
2.  **Create Blueprint Service:** On the Render dashboard, create a new "Blueprint" service and connect your repository. Render will use the `render.yaml` file automatically.
3.  **Add Environment Variables:** In your service's "Environment" tab on Render, add your `KITE_API_KEY` and `KITE_API_SECRET`.
4.  **Deploy.** Render will build and deploy the service. Your API will be available at the URL provided by Render.
