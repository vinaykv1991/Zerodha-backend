# Kite Live Data API

This project provides a FastAPI-based backend service to interact with the Zerodha Kite Connect API. It allows users to authenticate, fetch various types of real-time market data, and retrieve historical data for financial instruments.

The application is designed for easy local setup and is pre-configured for deployment on the Render platform.

## Features

- **Authentication:** A simple two-step authentication flow to get an access token from Kite Connect.
- **Market Data:** Endpoints to fetch live snapshot data, including:
  - Last Traded Price (LTP)
  - Open, High, Low, Close (OHLC)
  - Full quote details (volume, depth, etc.)
- **Historical Data:** An endpoint to retrieve historical candle data for any instrument with a specified time frame and date range.
- **Instrument Discovery:** An endpoint to fetch the list of all tradable instruments for a given exchange.
- **Deployment Ready:** Includes a `render.yaml` file for seamless deployment to the Render cloud platform.
- **Secure Configuration:** Uses environment variables to manage sensitive API keys and secrets, following security best practices.

---

## Local Setup and Usage

Follow these steps to run the application on your local machine.

### 1. Prerequisites

- Python 3.8+
- A Zerodha Kite Developer account with an `api_key` and `api_secret`.
- Your application's redirect URL configured in your Kite Developer app settings.

### 2. Installation

Clone the repository and install the required dependencies:

```bash
git clone <repository_url>
cd <repository_name>
pip install -r requirements.txt
```

### 3. Environment Variables

The application requires your Kite API credentials to be set as environment variables.

**On macOS/Linux:**
```bash
export KITE_API_KEY='your_api_key'
export KITE_API_SECRET='your_api_secret'
```

**On Windows (Command Prompt):**
```bash
set KITE_API_KEY=your_api_key
set KITE_API_SECRET=your_api_secret
```

### 4. Running the Application

Once the environment variables are set, you can start the application using `uvicorn`:

```bash
uvicorn kite_live_data.main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.

---

## API Endpoints

### Authentication

1.  **Login (`GET /login`)**
    -   Open `http://localhost:8000/login` in your browser.
    -   This will redirect you to the official Zerodha login page.
    -   After you log in, you will be redirected to your configured redirect URL with a `request_token`.

2.  **Generate Session (`GET /callback`)**
    -   Copy the `request_token` from the redirect URL.
    -   Make a request to the callback endpoint to generate a session:
        `http://localhost:8000/callback?request_token=YOUR_REQUEST_TOKEN`
    -   This will create an `access_token` that the server will use for subsequent requests.

### Market Data

*   **Get Profile (`GET /profile`)**
    -   Returns the user profile to confirm authentication.

*   **Get Instruments (`GET /instruments/{exchange}`)**
    -   Example: `http://localhost:8000/instruments/NSE`

*   **Get LTP/OHLC/Quote (`POST /ltp`, `/ohlc`, `/quote`)**
    -   Requires a JSON body with a list of instrument tokens.
    -   Example with `curl`:
        ```bash
        curl -X POST "http://localhost:8000/ltp" \
             -H "Content-Type: application/json" \
             -d '{"instrument_tokens": ["256265"]}'
        ```

*   **Get Historical Data (`GET /historical-data/{instrument_token}`)**
    -   Requires `from_date`, `to_date`, and `interval` as query parameters.
    -   Example with `curl`:
        ```bash
        curl "http://localhost:8000/historical-data/256265?from_date=2024-01-01&to_date=2024-01-31&interval=day"
        ```

---

## Deployment on Render

This repository is ready for deployment on Render using the included `render.yaml` file.

### Steps:

1.  **Push to a Git Repository:** Make sure your code is pushed to a GitHub or GitLab repository.

2.  **Create a New Blueprint Service on Render:**
    -   On the Render dashboard, click "New +" and select "Blueprint".
    -   Connect your Git repository.
    -   Render will automatically detect and use the `render.yaml` file.

3.  **Add Environment Variables:**
    -   In the service settings on Render, go to the "Environment" tab.
    -   Add the following environment variables with your actual Kite credentials:
        -   `KITE_API_KEY`: `your_api_key`
        -   `KITE_API_SECRET`: `your_api_secret`

4.  **Deploy:**
    -   Click "Create New Service". Render will build and deploy the application.
    -   Your API will be available at the URL provided by Render.
