import os
import requests
from dotenv import load_dotenv


load_dotenv()

TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")

INSTRUMENT = "NSE_EQ|INE467B01029"

TIMEFRAMES = {
    "1m": ("minutes", "1"),
    "5m": ("minutes", "5"),
    "15m": ("minutes", "15"),
    "30m": ("minutes", "30"),
    "1h": ("hours", "1"),
}


headers = {
    "Accept": "application/json",
    "Authorization": f"Bearer {TOKEN}",
}


for name, (unit, interval) in TIMEFRAMES.items():

    print()
    print("=" * 70)
    print(f"UPSTOX {name} CANDLE TEST")
    print("=" * 70)

    url = (
        "https://api.upstox.com/v3/"
        f"historical-candle/"
        f"{INSTRUMENT}/"
        f"{unit}/"
        f"{interval}/"
        "2026-09-01/"
        "2026-08-28"
    )

    response = requests.get(
        url,
        headers=headers,
        timeout=15,
    )

    print("HTTP:", response.status_code)

    data = response.json()

    candles = (
        data
        .get("data", {})
        .get("candles", [])
    )

    print("Total candles:", len(candles))

    print("\nNEWEST 3:")

    for candle in candles[:3]:
        print(candle)

    print("\nOLDEST 3:")

    for candle in candles[-3:]:
        print(candle)