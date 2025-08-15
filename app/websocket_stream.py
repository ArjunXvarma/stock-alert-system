import asyncio
import json
import ssl
import websockets
import requests
import os
from dotenv import load_dotenv
from fastapi import APIRouter, WebSocket
from google.protobuf.json_format import MessageToDict
import app.MarketDataFeed_pb2 as pb
from app.state import clients

load_dotenv()
router = APIRouter()

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

async def fetch_market_data(instrument_keys, client_websocket):
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    response = get_market_data_feed_authorize_v3()

    async with websockets.connect(response["data"]["authorized_redirect_uri"], ssl=ssl_context) as websocket:
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

        while True:
            msg = await websocket.recv()
            decoded = decode_protobuf(msg)
            data_dict = MessageToDict(decoded)

            try:
                print('sending messages')
                await client_websocket.send_json(data_dict)
            
            except:
                print('Error in sending message to client')
