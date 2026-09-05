from __future__ import annotations

import os
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import requests
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

from src.data.live_candle_store import LiveCandleStore


load_dotenv()

UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")
UPSTOX_API_BASE = "https://api.upstox.com/v3"
UPSTOX_HISTORICAL_URL = f"{UPSTOX_API_BASE}/historical-candle"
UPSTOX_INTRADAY_URL = f"{UPSTOX_API_BASE}/historical-candle/intraday"

IST = ZoneInfo("Asia/Kolkata")
UTC = ZoneInfo("UTC")

SUPPORTED_INTERVALS = {
    "1m": {"unit": "minutes", "interval": "1"},
    "3m": {"unit": "minutes", "interval": "3"},
    "5m": {"unit": "minutes", "interval": "5"},
    "10m": {"unit": "minutes", "interval": "10"},
    "15m": {"unit": "minutes", "interval": "15"},
    "30m": {"unit": "minutes", "interval": "30"},
    "1h": {"unit": "hours", "interval": "1"},
}

# Short-lived cache avoids repeating the same broker requests when a user
# switches timeframes and immediately switches back. Intraday data is kept
# intentionally short-lived because it changes during market hours.
_CANDLE_CACHE: dict[tuple[str, str], tuple[float, list[dict]]] = {}
_CACHE_TTL_SECONDS = 10
_CACHE_LOCK = __import__("threading").RLock()


def _get_headers() -> dict:
    if not UPSTOX_ACCESS_TOKEN:
        raise RuntimeError("UPSTOX_ACCESS_TOKEN is missing from .env")
    return {
        "Accept": "application/json",
        "Authorization": f"Bearer {UPSTOX_ACCESS_TOKEN}",
    }


def _request_json(url: str) -> dict:
    response = requests.get(url, headers=_get_headers(), timeout=8)

    if response.status_code != 200:
        raise RuntimeError(
            f"Upstox candle request failed: HTTP {response.status_code}: "
            f"{response.text}"
        )

    payload = response.json()

    if payload.get("status") != "success":
        raise RuntimeError(
            f"Upstox candle API returned an unsuccessful response: {payload}"
        )

    return payload


def _fetch_historical(
    instrument_key: str,
    unit: str,
    interval: str,
    to_date: str,
    from_date: str,
) -> list:
    url = (
        f"{UPSTOX_HISTORICAL_URL}/{instrument_key}/"
        f"{unit}/{interval}/{to_date}/{from_date}"
    )
    print(f"[HISTORICAL] {url}")
    return _request_json(url).get("data", {}).get("candles", [])


def _fetch_intraday(
    instrument_key: str,
    unit: str,
    interval: str,
) -> list:
    url = (
        f"{UPSTOX_INTRADAY_URL}/{instrument_key}/"
        f"{unit}/{interval}"
    )
    print(f"[INTRADAY]  {url}")
    return _request_json(url).get("data", {}).get("candles", [])


def _parse_timestamp(timestamp) -> datetime:
    parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=IST)
    return parsed.astimezone(UTC)


def _convert_candle(
    symbol: str,
    interval: str,
    candle: list,
    instrument_key: str,
) -> dict:
    if len(candle) < 6:
        raise ValueError(f"Invalid Upstox candle: {candle}")

    return {
        "symbol": symbol,
        "instrument_key": instrument_key,
        "interval": interval,
        "timestamp": _parse_timestamp(candle[0]).isoformat(),
        "open": float(candle[1]),
        "high": float(candle[2]),
        "low": float(candle[3]),
        "close": float(candle[4]),
        "volume": int(candle[5]),
    }


def _combine_and_deduplicate(candles: list[dict]) -> list[dict]:
    by_timestamp: dict[str, dict] = {}

    for candle in candles:
        ts = _parse_timestamp(candle["timestamp"]).isoformat()
        item = candle.copy()
        item["timestamp"] = ts
        # Intraday candles are added after historical candles, so today's
        # version wins if the two sources overlap.
        by_timestamp[ts] = item

    result = list(by_timestamp.values())
    result.sort(key=lambda c: _parse_timestamp(c["timestamp"]))
    return result


def _market_is_open(now: datetime) -> bool:
    now = now.astimezone(IST)
    if now.weekday() >= 5:
        return False
    return time(9, 15) <= now.time() < time(15, 30)


def _current_bucket_start(
    interval: str,
    now: datetime | None = None,
) -> datetime | None:
    """Return the start of the currently forming NSE candle, if market is open."""
    now = now or datetime.now(IST)
    if now.tzinfo is None:
        now = now.replace(tzinfo=IST)
    now = now.astimezone(IST)

    if not _market_is_open(now):
        return None

    session_start = 9 * 60 + 15

    if interval == "1h":
        size = 60
    else:
        size = int(interval.removesuffix("m"))

    now_minutes = now.hour * 60 + now.minute
    elapsed = now_minutes - session_start
    bucket = session_start + (elapsed // size) * size

    return now.replace(
        hour=bucket // 60,
        minute=bucket % 60,
        second=0,
        microsecond=0,
    )



def load_historical_candles(
    symbol: str,
    interval: str = "1m",
    period: str = "5d",
    max_candles: int = 200,
    instrument_key: str | None = None,
) -> LiveCandleStore:
    """
    Fast bootstrap for one exact instrument/timeframe.

    Historical previous-day candles and today's intraday candles are fetched
    concurrently. This preserves immediate analysis AND gives the chart the
    current trading day's completed candles. A short-lived cache avoids
    duplicate broker calls during quick timeframe switches.
    """
    if not symbol or not symbol.strip():
        raise ValueError("Symbol is required.")
    if not instrument_key or not instrument_key.strip():
        raise ValueError("instrument_key is required.")
    if interval not in SUPPORTED_INTERVALS:
        raise ValueError(
            f"Unsupported interval '{interval}'. "
            f"Supported intervals: {list(SUPPORTED_INTERVALS)}"
        )
    if max_candles <= 0:
        raise ValueError("max_candles must be greater than 0.")

    symbol = symbol.strip().upper()
    instrument_key = instrument_key.strip()

    try:
        requested_days = (
            max(1, int(period[:-1])) if period.endswith("d") else 5
        )
    except (ValueError, TypeError):
        requested_days = 5

    minimum_days = {
        "1m": 5,
        "3m": 5,
        "5m": 5,
        "10m": 5,
        "15m": 10,
        "30m": 15,
        "1h": 20,
    }[interval]
    requested_days = max(requested_days, minimum_days)

    now_ist = datetime.now(IST)
    today = now_ist.date()
    yesterday = today - timedelta(days=1)
    historical_start = today - timedelta(days=requested_days)
    cfg = SUPPORTED_INTERVALS[interval]
    cache_key = (instrument_key, interval)

    print()
    print("=" * 70)
    print("FAST UPSTOX CANDLE BOOTSTRAP")
    print("=" * 70)
    print(f"Symbol              : {symbol}")
    print(f"Instrument           : {instrument_key}")
    print(f"Interval             : {interval}")
    print(f"Historical from      : {historical_start.isoformat()}")
    print(f"Historical to        : {yesterday.isoformat()}")
    print(f"Intraday              : {today.isoformat()}")

    # Cache completed+intraday candles briefly.
    import time as _time
    now_epoch = _time.monotonic()
    with _CACHE_LOCK:
        cached = _CANDLE_CACHE.get(cache_key)
        if cached and now_epoch - cached[0] < _CACHE_TTL_SECONDS:
            candles = [c.copy() for c in cached[1]]
            print("Cache hit            : yes")
        else:
            candles = None

    if candles is None:
        # These two requests are independent. Parallelizing them preserves
        # both data sources while cutting startup latency roughly to the
        # slower request rather than the sum of both requests.
        with ThreadPoolExecutor(max_workers=2) as executor:
            historical_future = executor.submit(
                _fetch_historical,
                instrument_key,
                cfg["unit"],
                cfg["interval"],
                yesterday.isoformat(),
                historical_start.isoformat(),
            )
            intraday_future = executor.submit(
                _fetch_intraday,
                instrument_key,
                cfg["unit"],
                cfg["interval"],
            )

            historical_raw = historical_future.result()
            intraday_raw = intraday_future.result()

        print(f"Historical candles   : {len(historical_raw)}")
        print(f"Intraday candles     : {len(intraday_raw)}")

        converted: list[dict] = []

        for raw in historical_raw:
            try:
                converted.append(
                    _convert_candle(symbol, interval, raw, instrument_key)
                )
            except Exception as exc:
                print(f"Skipping invalid historical candle {raw}: {exc}")

        for raw in intraday_raw:
            try:
                converted.append(
                    _convert_candle(symbol, interval, raw, instrument_key)
                )
            except Exception as exc:
                print(f"Skipping invalid intraday candle {raw}: {exc}")

        if not converted:
            raise ValueError(
                f"No valid candles returned by Upstox for {symbol} {interval}."
            )

        candles = _combine_and_deduplicate(converted)

        # Do not remove the newest row blindly. Remove only the exact bucket
        # that is currently forming, and only while NSE is open.
        current_bucket = _current_bucket_start(interval, now_ist)
        completed = []
        removed = 0

        for candle in candles:
            candle_dt = _parse_timestamp(candle["timestamp"])
            if current_bucket and candle_dt == current_bucket.astimezone(UTC):
                removed += 1
                continue
            completed.append(candle)

        candles = completed[-max_candles:]

        with _CACHE_LOCK:
            _CANDLE_CACHE[cache_key] = (
                now_epoch,
                [c.copy() for c in candles],
            )

        print(f"Current candle removed: {removed}")
    else:
        print(f"Cache candles        : {len(candles)}")

    if not candles:
        raise ValueError(
            f"No completed candles available for {symbol} {interval}."
        )

    print(f"Final completed      : {len(candles)}")
    print(f"Final first          : {candles[0]['timestamp']}")
    print(f"Final last           : {candles[-1]['timestamp']}")
    print("=" * 70)
    print()

    store = LiveCandleStore(max_candles=max_candles)
    for candle in candles[-max_candles:]:
        store.add_candle(candle)

    return store
