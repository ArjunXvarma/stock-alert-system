import asyncio
import json
import ssl
import websockets
import requests
import os
from dotenv import load_dotenv
from fastapi import WebSocket
from google.protobuf.json_format import MessageToDict
import app.MarketDataFeed_pb2 as pb
from app.redis import redisClient
from starlette.websockets import WebSocketDisconnect
from app.trade_signal_logic import compute_cvd_ohlc

load_dotenv()

UPSTOX_ACCESS_TOKEN = os.getenv('UPSTOX_ACCESS_TOKEN')

def get_market_data_feed_authorize_v3():
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {UPSTOX_ACCESS_TOKEN}'
    }
    url = 'https://api.upstox.com/v3/feed/market-data-feed/authorize'
    resp = requests.get(url=url, headers=headers)
    return resp.json()


def decode_protobuf(buffer):
    feed_response = pb.FeedResponse()
    feed_response.ParseFromString(buffer)
    return feed_response

def extract_market_minute_data(data_dict, instrument_key):
    """
    Extracts the minute data and timestamp from the decoded protobuf dict.
    Returns (market_minute_data, ts_ms) or (None, None) if not found.
    """
    feed = data_dict.get("feeds", {}).get(instrument_key, {})
    market_ff = feed.get("ff", {}).get("marketFF", {})
    market_ohlc = market_ff.get("marketOHLC", {}).get("ohlc", [])
    if not market_ohlc or len(market_ohlc) < 2:
        return None, None
    market_minute_data = market_ohlc[1]
    try:
        ts_ms = int(market_minute_data["ts"])
    except Exception:
        return None, None
    return market_minute_data, ts_ms

def build_payload(ts_sec, price_data, volume_data):
    """
    Builds the payload dict for sending to the client.
    """
    price_payload = {
        "time": ts_sec,
        "open": float(price_data["open"]),
        "high": float(price_data["high"]),
        "low": float(price_data["low"]),
        "close": float(price_data["close"])
    }
    volume_payload = {
        "time": ts_sec,
        "open": volume_data["open"],
        "high": volume_data["high"],
        "low": volume_data["low"],
        "close": volume_data["close"]
    }
    return {
        "time": ts_sec,
        "price": price_payload,
        "volume": volume_payload
    }

def update_redis(redisClient, instrument_key, ts_sec, price_payload=None, volume_payload=None, alert_payload=None):
    price_key = f"{instrument_key}:price"
    volume_key = f"{instrument_key}:volume"
    timestamp_key = f"{instrument_key}:timestamp"
    alert_key = f"{instrument_key}:alerts"

    if redisClient.sadd(timestamp_key, ts_sec):
        redisClient.rpush(price_key, json.dumps(price_payload))
        redisClient.rpush(volume_key, json.dumps(volume_payload))
    if alert_payload:
        redisClient.sadd(alert_key, json.dumps({
            "time": ts_sec,
            **alert_payload
        }))

async def fetch_market_data(instrument_keys, client_websocket: WebSocket):
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    response = get_market_data_feed_authorize_v3()
    if "data" not in response or "authorized_redirect_uri" not in response["data"]:
        print("Failed to get WebSocket URI:", response)
        return

    uri = response["data"]["authorized_redirect_uri"]

    async with websockets.connect(uri, ssl=ssl_context) as websocket:
        await asyncio.sleep(1)
        sub_data = {
            "guid": "someguid",
            "method": "sub",
            "data": {
                "mode": "full",
                "instrumentKeys": instrument_keys
            }
        }
        await websocket.send(json.dumps(sub_data).encode("utf-8"))

        instrument_key = instrument_keys[0]
        last_received_ts_ms = None 
        prev_candle_volume = None
        prev_cum = 0.0

        prev_price_close = None
        prev_cvd_close = None

        while True:
            try:
                msg = await websocket.recv()
                decoded = decode_protobuf(msg)
                data_dict = MessageToDict(decoded)
                # print('-----------------------------------------------------------')
                # print(data_dict)
                # print('-----------------------------------------------------------')

                market_minute_data, ts_ms = extract_market_minute_data(data_dict, instrument_key)
                if market_minute_data is None or ts_ms is None:
                    continue

                if last_received_ts_ms is not None and ts_ms == last_received_ts_ms:
                    continue
                last_received_ts_ms = ts_ms

                ts_sec = ts_ms // 1000
                price_open = float(market_minute_data["open"])
                price_high = float(market_minute_data["high"])
                price_low  = float(market_minute_data["low"])
                price_close= float(market_minute_data["close"])
                current_candle_volume = float(market_minute_data.get("volume", 0.0))

                if prev_candle_volume is None:
                    prev_candle_volume = current_candle_volume

                # vol_open = prev_candle_volume
                # vol_close = current_candle_volume
                # vol_high = max(vol_open, vol_close)
                # vol_low  = min(vol_open, vol_close)

                cvd_open, cvd_high, cvd_low, cvd_close, prev_cum = compute_cvd_ohlc(price_open, price_close, current_candle_volume, prev_cum)

                signal = None
                if prev_price_close is not None and prev_cvd_close is not None:
                    # Bullish engulfing style
                    if price_close > price_open and cvd_close > cvd_open and cvd_close > prev_cvd_close:
                        signal = "BUY"
                    # Bearish engulfing style
                    elif price_close < price_open and cvd_close < cvd_open and cvd_close < prev_cvd_close:
                        signal = "SELL"

                prev_price_close = price_close
                prev_cvd_close = cvd_close
                
                price_data = {
                    "open": price_open,
                    "high": price_high,
                    "low": price_low,
                    "close": price_close
                }

                volume_data = {
                    "open": cvd_open,
                    "high": cvd_high,
                    "low": cvd_low,
                    "close": cvd_close
                }

                payload = build_payload(ts_sec, price_data, volume_data)
                if signal:
                    payload["alert"] = {
                        "signal": signal,
                        "text": "buy" if signal == "BUY" else "sell"
                    } 

                else:
                    payload["alert"] = None

                update_redis(redisClient, instrument_key, ts_sec, payload["price"], payload["volume"], payload["alert"])

                try:
                    await client_websocket.send_json(payload)
                    prev_candle_volume = current_candle_volume
                except WebSocketDisconnect:
                    print("Client disconnected, stopping stream")
                    break
                except RuntimeError as e:
                    print(f"Client websocket already closed: {e}")
                    break

            except Exception as e:
                print(f"Error in sending message", e)
