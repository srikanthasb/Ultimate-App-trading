import os
import requests

from dotenv import load_dotenv


load_dotenv()


ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")

INSTRUMENT_KEY = "NSE_EQ|INE467B01029"

URL = (
    "https://api.upstox.com/v3/historical-candle/"
    f"{INSTRUMENT_KEY}/minutes/1/"
    "2026-08-28/2026-08-27"
)


headers = {
    "Accept": "application/json",
    "Authorization": f"Bearer {ACCESS_TOKEN}",
}


print()
print("=" * 70)
print("TESTING UPSTOX HISTORICAL CANDLE API")
print("=" * 70)
print()

print("Instrument :", INSTRUMENT_KEY)
print("URL        :", URL)
print()


response = requests.get(
    URL,
    headers=headers,
    timeout=15,
)


print("HTTP status:", response.status_code)
print()

print("Response:")
print(response.text)

print()
print("=" * 70)