import os
import requests
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")

def fetch_candle_data(instrument_key, unit, interval, to_date, from_date):
    url = f"https://api.upstox.com/v3/historical-candle/{instrument_key}/{unit}/{interval}/{to_date}/{from_date}"

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    try:
        response = requests.get(url, headers=headers)
        return response.json() if response.ok else None
    except Exception as e:
        print(f"Error fetching candle data: {e}")
        return None
