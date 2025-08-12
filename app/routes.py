from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.upstox_api import fetch_candle_data
import plotly.graph_objects as go
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

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
        return templates.TemplateResponse("chart.html", {"request": request, "candles": [], "volumes": []})

    candle_list = data["data"]["candles"]

    candles = []
    volumes = []

    for candle in candle_list:
        # Parse date string into timestamp (seconds)
        dt = datetime.fromisoformat(candle[0])
        timestamp = int(dt.timestamp())

        candles.append({
            "time": candle[0],
            "open": candle[1],
            "high": candle[2],
            "low": candle[3],
            "close": candle[4]
        })

        volumes.append({
            "time": candle[0],
            "value": candle[5],
            "color": '#26a69a' if candle[4] >= candle[1] else '#ef5350'
        })

        candles.sort(key=lambda x: x["time"])
        volumes.sort(key=lambda x: x["time"])

    return templates.TemplateResponse("chart.html", {
        "request": request,
        "candles": candles,
        "volumes": volumes
    })