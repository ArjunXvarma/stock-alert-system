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

                latest_ohlc = market_ohlc[-1]

                candle = {
                    "time": int(latest_ohlc["ts"]) // 1000,  # seconds timestamp
                    "open": float(latest_ohlc["open"]),
                    "high": float(latest_ohlc["high"]),
                    "low": float(latest_ohlc["low"]),
                    "close": float(latest_ohlc["close"]),
                    "volume": float(latest_ohlc.get("volume", 0))
                }

                await client_websocket.send_json(candle)

            except Exception as e:
                print(f"Error in sending message to client: {e}")
