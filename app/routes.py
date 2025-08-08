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
async def fetch(request: Request,
                instrument_key: str = Form(...),
                unit: str = Form(...),
                interval: int = Form(...),
                from_date: str = Form(...),
                to_date: str = Form(...)):

    data = fetch_candle_data(instrument_key, unit, interval, to_date, from_date)

    if not data or "data" not in data:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": "No data retrieved or API error."
        })

    candles = data["data"]["candles"]
    timestamps, open_, high, low, close, volume, open_interests = zip(*candles)

    # Convert timestamp strings to datetime
    timestamps = [datetime.fromisoformat(t) for t in timestamps]

    # Create price candlestick chart
    price_fig = go.Figure(data=[go.Candlestick(
        x=timestamps,
        open=open_,
        high=high,
        low=low,
        close=close,
        name="Price"
    )])
    price_fig.update_layout(title="Price Candlestick", xaxis_title="Time", yaxis_title="Price")

    # Create volume bar chart
    volume_fig = go.Figure(data=[go.Bar(x=timestamps, y=volume, name="Volume")])
    volume_fig.update_layout(title="Volume Chart", xaxis_title="Time", yaxis_title="Volume")

    price_chart_html = price_fig.to_html(full_html=False)
    volume_chart_html = volume_fig.to_html(full_html=False)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "price_chart": price_chart_html,
        "volume_chart": volume_chart_html
    })
