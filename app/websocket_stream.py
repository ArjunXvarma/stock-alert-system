import asyncio
import json
import websockets
from typing import List
import os
import requests
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")
UPSTOX_WS_URL = os.getenv("UPSTOX_WS_URL")

async def stream_ticks(instrument_keys: List[str], send_callback):
    uri = f"{UPSTOX_WS_URL}/feed/market-data-feed"
    async with websockets.connect(uri, additional_headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}) as ws:
        # Subscribe to instruments
        subscribe_msg = {
            "guid": "13syxu852ztodyqncwt0",
            "method": "subscribe",
            "data": {
                "mode": "full",
                "instrumentKeys": instrument_keys
            }
        }
        await ws.send(json.dumps(subscribe_msg))

        async for message in ws:
            if isinstance(message, bytes):
                # Handle binary tick data (decode protobuf or parse accordingly)
                # For now, let's just skip or log length
                print(f"Received binary data: {len(message)} bytes")
                continue
            else:
                # Text message (JSON)
                data = json.loads(message)
                print(data)
                await send_callback(data)  # push to FastAPI websocket
