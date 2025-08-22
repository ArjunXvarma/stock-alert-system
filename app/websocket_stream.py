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
        await websocket.send(json.dumps(sub_data).encode('utf-8'))

        instrument_key = instrument_keys[0]

        # State to compute volume OHLC across consecutive candles
        last_sent_ts_ms = None        # last candle timestamp (ms) we sent
        prev_candle_volume = None     # volume of the previous candle

        while True:
            try:
                msg = await websocket.recv()
                decoded = decode_protobuf(msg)
                data_dict = MessageToDict(decoded)

                feed = data_dict.get("feeds", {}).get(instrument_key, {})
                market_ff = feed.get("ff", {}).get("marketFF", {})
                market_ohlc = market_ff.get("marketOHLC", {}).get("ohlc", [])

                if not market_ohlc:
                    continue

                unsent = []
                last_ts_seen = last_sent_ts_ms or 0
                for o in market_ohlc:
                    try:
                        ts_ms = int(o["ts"])
                        if ts_ms > last_ts_seen:
                            unsent.append(o)
                    except Exception:
                        continue

                if not unsent:
                    # No new completed candle; skip (avoid sending intra-minute duplicates)
                    continue

                # Send unsent candles in chronological order
                unsent.sort(key=lambda x: int(x["ts"]))

                for o in unsent:
                    ts_ms = int(o["ts"])
                    ts_sec = ts_ms // 1000

                    price_open = float(o["open"])
                    price_high = float(o["high"])
                    price_low  = float(o["low"])
                    price_close= float(o["close"])
                    current_candle_volume = float(o.get("volume", 0.0))

                    # Initialize prev_candle_volume on the very first candle we ever send
                    if prev_candle_volume is None:
                        prev_candle_volume = current_candle_volume

                    # Build volume OHLC like your historical route:
                    vol_open = prev_candle_volume
                    vol_close = current_candle_volume
                    vol_high = max(vol_open, vol_close)
                    vol_low  = min(vol_open, vol_close)

                    price_payload = {
                        "open": price_open,
                        "high": price_high,
                        "low": price_low,
                        "close": price_close
                    }

                    volume_payload = {
                        "open": vol_open,
                        "high": vol_high,
                        "low": vol_low,
                        "close": vol_close
                    }

                    payload = {
                        "time": ts_sec,
                        "price": price_payload,
                        "volume": volume_payload
                    }

                    # --- Store in Redis with uniqueness check ---
                    price_key = f"{instrument_key}:price"
                    volume_key = f"{instrument_key}:volume"
                    timestamp_key = f"{instrument_key}:timestamp"

                    if redisClient.ttl(price_key) == -1:
                        redisClient.expire(price_key, 86400)
                    if redisClient.ttl(volume_key) == -1:
                        redisClient.expire(volume_key, 86400)
                    if redisClient.ttl(timestamp_key) == -1:
                        redisClient.expire(timestamp_key, 86400)

                    if redisClient.sadd(timestamp_key, ts_sec):
                        redisClient.rpush(price_key, json.dumps(price_payload))
                        redisClient.rpush(volume_key, json.dumps(volume_payload))

                    await client_websocket.send_json(payload)

                    # Update state for next candle
                    prev_candle_volume = current_candle_volume
                    last_sent_ts_ms = ts_ms

            except Exception as e:
                print(f"Error in sending message to client: {e}")