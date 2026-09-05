import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.services.analysis_service import AnalysisService
from src.services.live_market_service import LiveMarketService


app = FastAPI(
    title="AI Investment API",
    description="Real-time market data, deterministic technical confluence, AI interpretation and risk-controlled trade guidance.",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

live_market_service = LiveMarketService(max_candles=200)


class AnalyzeRequest(BaseModel):
    symbol: str
    period: str = "6mo"
    interval: str = "1d"


class LiveInstrumentRequest(BaseModel):
    instrument: dict
    interval: str = "1m"


class LiveIntervalRequest(BaseModel):
    interval: str


class LiveSearchRequest(BaseModel):
    query: str


def current_snapshot() -> dict[str, Any]:
    return {
        "type": "snapshot",
        "state": live_market_service.get_state(),
        "candles": live_market_service.get_candles(),
        "current_candle": live_market_service.get_current_candle(),
        "analysis": live_market_service.get_analysis(),
    }


FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@app.get("/")
def root():
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "application": "AI Investment API",
        "status": "running",
        "version": "3.0.0",
        "frontend": "not built (use the Vite dev server for local development)",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    try:
        service = AnalysisService(period=request.period, interval=request.interval)
        return service.analyze(request.symbol)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@app.post("/live/search")
def live_search(request: LiveSearchRequest):
    try:
        results = live_market_service.search_instruments(request.query)
        return {"query": request.query, "count": len(results), "instruments": results}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@app.post("/live/start")
def live_start(request: LiveInstrumentRequest):
    try:
        live_market_service.start(request.instrument, request.interval)
        live_market_service.publish_snapshot()
        return {"status": "started", "instrument": request.instrument, "interval": request.interval}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@app.post("/live/stop")
def live_stop():
    try:
        live_market_service.stop()
        live_market_service.publish_snapshot()
        return {"status": "stopped"}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@app.post("/live/interval")
def live_interval(request: LiveIntervalRequest):
    try:
        live_market_service.set_interval(request.interval)
        live_market_service.publish_snapshot()
        return {"status": "changed", "interval": request.interval}
    except (ValueError, RuntimeError) as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@app.get("/live/state")
def live_state():
    return live_market_service.get_state()


@app.get("/live/candles")
def live_candles():
    return {"candles": live_market_service.get_candles()}


@app.websocket("/ws/market")
async def market_websocket(websocket: WebSocket):
    await websocket.accept()
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=100)

    def on_update(payload: dict[str, Any]):
        def enqueue():
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            queue.put_nowait(payload)

        try:
            loop.call_soon_threadsafe(enqueue)
        except RuntimeError:
            pass

    live_market_service.subscribe(on_update)
    try:
        await websocket.send_text(json.dumps(current_snapshot(), default=str))
        while True:
            payload = await queue.get()
            await websocket.send_text(json.dumps(payload, default=str))
    except WebSocketDisconnect:
        pass
    finally:
        live_market_service.unsubscribe(on_update)


if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")
