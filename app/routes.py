from fastapi import APIRouter, Request, Form, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.upstox_api import fetch_candle_data
from app.websocket_stream import fetch_market_data
import plotly.graph_objects as go
from datetime import datetime
import asyncio
from app.state import clients
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
UTC = timezone.utc

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
clients = set()

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@router.post("/getCandleData", response_class=HTMLResponse)
async def fetch(
    request: Request,
    instrument_key: str = Form(...),
    unit: str = Form(...),
    interval: int = Form(...),
    to_date: str = Form(...),
    from_date: str = Form(...)
):
    data = fetch_candle_data(instrument_key, unit, interval, to_date, from_date)
    if not data or "data" not in data:
        return templates.TemplateResponse("periodicChart.html", {"request": request, "candles": [], "volumes": []})

    candle_list = data["data"]["candles"]

    candles = []
    volumes = []

    prev_volume = candle_list[0][5]

    for candle in candle_list:
        dt = datetime.fromisoformat(candle[0]).replace(tzinfo=UTC)
        dt = dt.astimezone(IST)

        timestamp = int(dt.timestamp())

        if unit == "days":
            time_value = dt.strftime("%Y-%m-%d")
        else:
            time_value = int(dt.timestamp())

        candles.append({
            "time": time_value,
            "open": candle[1],
            "high": candle[2],
            "low": candle[3],
            "close": candle[4]
        })

        current_volume = candle[5]
        open_vol = prev_volume
        close_vol = current_volume
        high_vol = max(open_vol, close_vol)
        low_vol = min(open_vol, close_vol)

        volumes.append({
            "time": time_value,
            "open": open_vol,
            "high": high_vol,
            "low": low_vol,
            "close": close_vol
        })

        prev_volume = current_volume

        candles.sort(key=lambda x: x["time"])
        volumes.sort(key=lambda x: x["time"])

    return templates.TemplateResponse("periodicChart.html", {
        "request": request,
        "candles": candles,
        "volumes": volumes
    })

@router.websocket("/ws/live/{instrument_key}")
async def live_data(websocket: WebSocket, instrument_key: str):
    await websocket.accept()
    clients.add(websocket)

    # Start streaming in the background (if not already running)
    asyncio.create_task(fetch_market_data([instrument_key], websocket))

    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except:
        print('Socket being removed')
        clients.remove(websocket)

@router.get("/live/{instrument_key}", response_class=HTMLResponse)
async def live_page(request: Request, instrument_key: str):
    return templates.TemplateResponse(
        "liveChart.html", 
        {
            "request": request,
            "instrument_key": instrument_key
        }
    )