import os
import requests
from dotenv import load_dotenv


load_dotenv()


UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")

UPSTOX_INSTRUMENT_SEARCH_URL = (
    "https://api.upstox.com/v2/instruments/search"
)


class UpstoxInstrumentResolver:

    def __init__(self):
        if not UPSTOX_ACCESS_TOKEN:
            raise RuntimeError(
                "UPSTOX_ACCESS_TOKEN is missing from .env"
            )

        self.headers = {
            "Accept": "application/json",
            "Authorization": (
                f"Bearer {UPSTOX_ACCESS_TOKEN}"
            ),
        }

    def search(
        self,
        query: str,
        exchanges: str = "NSE",
        segments: str = "EQ,INDEX",
        records: int = 30,
    ) -> list[dict]:

        if not query:
            raise ValueError(
                "Instrument search query cannot be empty."
            )

        query = query.strip()

        if len(query) > 50:
            raise ValueError(
                "Instrument search query cannot exceed 50 characters."
            )

        params = {
            "query": query,
            "exchanges": exchanges,
            "segments": segments,
            "page_number": 1,
            "records": min(records, 30),
        }

        response = requests.get(
            UPSTOX_INSTRUMENT_SEARCH_URL,
            headers=self.headers,
            params=params,
            timeout=15,
        )

        response.raise_for_status()

        payload = response.json()

        if payload.get("status") != "success":
            raise RuntimeError(
                f"Upstox instrument search failed: {payload}"
            )

        instruments = payload.get(
            "data",
            [],
        )

        results = []

        for instrument in instruments:

            results.append(
                {
                    "name": instrument.get("name"),
                    "short_name": instrument.get(
                        "short_name"
                    ),
                    "trading_symbol": instrument.get(
                        "trading_symbol"
                    ),
                    "instrument_key": instrument.get(
                        "instrument_key"
                    ),
                    "exchange": instrument.get(
                        "exchange"
                    ),
                    "segment": instrument.get(
                        "segment"
                    ),
                    "instrument_type": instrument.get(
                        "instrument_type"
                    ),
                    "isin": instrument.get(
                        "isin"
                    ),
                    "lot_size": instrument.get(
                        "lot_size"
                    ),
                    "tick_size": instrument.get(
                        "tick_size"
                    ),
                    "expiry": instrument.get(
                        "expiry"
                    ),
                }
            )

        return results

    def resolve_equity(
        self,
        query: str,
    ) -> dict:

        results = self.search(
            query=query,
            exchanges="NSE",
            segments="EQ",
            records=30,
        )

        if not results:
            raise LookupError(
                f"No NSE equity found for '{query}'."
            )

        # Prefer exact trading-symbol match.
        query_upper = query.upper()

        for instrument in results:

            trading_symbol = (
                instrument.get("trading_symbol")
                or ""
            ).upper()

            if trading_symbol == query_upper:
                return instrument

        # Otherwise return first matching result.
        return results[0]