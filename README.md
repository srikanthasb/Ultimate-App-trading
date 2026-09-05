# AI Investment App V3

A real-time trading guidance platform built around a Python/FastAPI market and analysis backend and a browser-native React/TypeScript trading interface.

## V3 design goals

- No Streamlit rerun in the live trading path.
- Persistent browser chart; live ticks update the existing chart.
- Browser WebSocket connection with automatic reconnect.
- Upstox LTPC feed with backend reconnect support.
- Exact instrument-key propagation from search through history, candles and live ticks.
- 1m, 3m, 5m, 10m, 15m, 30m and 1h candles.
- Zoom, pan and trader-controlled chart framing.
- Deterministic technical confluence before AI interpretation.
- Weak/conflicting setups are rejected as HOLD.
- Valid setups receive entry, stop, targets, quantity and trailing-stop guidance when risk conditions permit.
- HOLD still exposes support, resistance and monitoring conditions.

## Architecture

```text
Upstox WebSocket
      |
      v
FastAPI / LiveMarketService
      |
      +--> CandleEngine / LiveCandleStore
      +--> Indicators / Strategy Engine
      +--> AI Analyst / Decision Engine
      +--> Risk Engine / Trade Plan Engine
      |
      v
FastAPI WebSocket /ws/market
      |
      v
React + TypeScript + Lightweight Charts
      |
      +--> persistent candlestick chart
      +--> live price/candle updates
      +--> BUY / SELL / HOLD guidance
      +--> visible risk plan
```

## Local development

### 1. Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create `.env` from `.env.example` and add your own credentials locally. Never commit `.env`.

Start the backend:

```powershell
python -m uvicorn src.api.api:app --host 127.0.0.1 --port 8000
```

### 2. Frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, normally `http://127.0.0.1:5173`.

The frontend talks to FastAPI at `http://127.0.0.1:8000` and receives live market events over `/ws/market`.

### 3. Legacy Streamlit reference

The old `app.py` is retained as a reference/fallback. V3's live trading UI is the React frontend and does not depend on Streamlit reruns.

## Production container

The Dockerfile builds the React frontend and serves the resulting static application from the FastAPI container on port 8000.

## Safety philosophy

The application is decision-support software, not a profit guarantee. It deliberately prefers HOLD when evidence is weak, conflicting, structurally poor, or unable to support a defensible risk/reward plan.
