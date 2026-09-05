from __future__ import annotations

import os
import time as _time
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import requests
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
# switches timeframes and immediately switches back.
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
    """
    Make an Upstox HTTP request.

    Timing is intentionally measured here so we can determine whether
    the remaining startup delay is caused by the broker/network.
    """
    request_started = _time.perf_counter()

    response = requests.get(
        url,
        headers=_get_headers(),
        timeout=8,
    )

    request_elapsed = _time.perf_counter() - request_started

    print(
        f"[HTTP] completed in {request_elapsed:.3f} sec "
        f"(HTTP {response.status_code})"
    )

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

    started = _time.perf_counter()

    candles = _request_json(url).get(
        "data", {}
    ).get(
        "candles", []
    )

    elapsed = _time.perf_counter() - started

    print(
        f"[HISTORICAL] received {len(candles)} candles "
        f"in {elapsed:.3f} sec"
    )

    return candles


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

    started = _time.perf_counter()

    candles = _request_json(url).get(
        "data", {}
    ).get(
        "candles", []
    )

    elapsed = _time.perf_counter() - started

    print(
        f"[INTRADAY] received {len(candles)} candles "
        f"in {elapsed:.3f} sec"
    )

    return candles


def _parse_timestamp(timestamp) -> datetime:
    parsed = datetime.fromisoformat(
        str(timestamp).replace("Z", "+00:00")
    )

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
        raise ValueError(
            f"Invalid Upstox candle: {candle}"
        )

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


def _combine_and_deduplicate(
    candles: list[dict],
) -> list[dict]:
    by_timestamp: dict[str, dict] = {}

    for candle in candles:
        ts = _parse_timestamp(
            candle["timestamp"]
        ).isoformat()

        item = candle.copy()
        item["timestamp"] = ts

        # Intraday candles are added after historical candles,
        # so today's version wins if the two sources overlap.
        by_timestamp[ts] = item

    result = list(by_timestamp.values())

    result.sort(
        key=lambda c: _parse_timestamp(c["timestamp"])
    )

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
    """
    Return the start of the currently forming NSE candle,
    if the market is open.
    """
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

    bucket = (
        session_start
        + (elapsed // size) * size
    )

    return now.replace(
        hour=bucket // 60,
        minute=bucket % 60,
        second=0,
        microsecond=0,
    )


def _cache_get(
    cache_key: tuple[str, str],
):
    now_epoch = _time.monotonic()

    with _CACHE_LOCK:
        cached = _CANDLE_CACHE.get(cache_key)

        if (
            cached
            and now_epoch - cached[0]
            < _CACHE_TTL_SECONDS
        ):
            return [
                c.copy()
                for c in cached[1]
            ]

    return None


def _cache_put(
    cache_key: tuple[str, str],
    candles: list[dict],
    now_epoch: float,
):
    with _CACHE_LOCK:
        _CANDLE_CACHE[cache_key] = (
            now_epoch,
            [
                c.copy()
                for c in candles
            ],
        )


def _prepare_completed_candles(
    symbol: str,
    interval: str,
    instrument_key: str,
    raw_candles: list,
    max_candles: int,
    now_ist: datetime,
) -> list[dict]:
    """
    Convert, deduplicate, remove the currently-forming candle,
    and retain the requested number of completed candles.

    Timing is included so we can distinguish API latency from
    local Python processing time.
    """
    started = _time.perf_counter()

    converted: list[dict] = []

    for raw in raw_candles:
        try:
            converted.append(
                _convert_candle(
                    symbol,
                    interval,
                    raw,
                    instrument_key,
                )
            )
        except Exception as exc:
            print(
                f"Skipping invalid candle {raw}: {exc}"
            )

    conversion_elapsed = (
        _time.perf_counter() - started
    )

    if not converted:
        print(
            f"[PROCESSING] conversion: "
            f"{conversion_elapsed:.3f} sec"
        )
        return []

    combine_started = _time.perf_counter()

    candles = _combine_and_deduplicate(
        converted
    )

    combine_elapsed = (
        _time.perf_counter()
        - combine_started
    )

    # Remove only the currently-forming bucket.
    # Do not blindly discard the newest row,
    # especially after market close or on weekends.
    current_bucket = _current_bucket_start(
        interval,
        now_ist,
    )

    completed = []
    removed = 0

    for candle in candles:
        candle_dt = _parse_timestamp(
            candle["timestamp"]
        )

        if (
            current_bucket
            and candle_dt
            == current_bucket.astimezone(UTC)
        ):
            removed += 1
            continue

        completed.append(candle)

    filtering_elapsed = (
        _time.perf_counter()
        - combine_started
        - combine_elapsed
    )

    total_elapsed = (
        _time.perf_counter()
        - started
    )

    print(
        f"[PROCESSING] conversion : "
        f"{conversion_elapsed:.3f} sec"
    )

    print(
        f"[PROCESSING] combine     : "
        f"{combine_elapsed:.3f} sec"
    )

    print(
        f"[PROCESSING] filtering   : "
        f"{filtering_elapsed:.3f} sec"
    )

    print(
        f"[PROCESSING] total       : "
        f"{total_elapsed:.3f} sec"
    )

    print(
        f"Current candle removed: {removed}"
    )

    return completed[-max_candles:]


def load_historical_candles(
    symbol: str,
    interval: str = "1m",
    period: str = "5d",
    max_candles: int = 200,
    instrument_key: str | None = None,
) -> LiveCandleStore:
    """
    Fast historical bootstrap for one exact instrument/timeframe.

    IMPORTANT:
    The historical request is the critical path because it provides
    enough candles for immediate indicators/strategies/AI.

    Today's intraday request is deliberately NOT awaited here.
    It is refreshed asynchronously by the LiveFeedManager after the
    historical store is installed.

    Timing instrumentation in this function allows us to determine
    exactly where startup time is being spent.
    """
    bootstrap_started = _time.perf_counter()

    if not symbol or not symbol.strip():
        raise ValueError("Symbol is required.")

    if not instrument_key or not instrument_key.strip():
        raise ValueError(
            "instrument_key is required."
        )

    if interval not in SUPPORTED_INTERVALS:
        raise ValueError(
            f"Unsupported interval '{interval}'. "
            f"Supported intervals: "
            f"{list(SUPPORTED_INTERVALS)}"
        )

    if max_candles <= 0:
        raise ValueError(
            "max_candles must be greater than 0."
        )

    symbol = symbol.strip().upper()
    instrument_key = instrument_key.strip()

    try:
        requested_days = (
            max(
                1,
                int(period[:-1]),
            )
            if period.endswith("d")
            else 5
        )
    except (
        ValueError,
        TypeError,
    ):
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

    requested_days = max(
        requested_days,
        minimum_days,
    )

    now_ist = datetime.now(IST)

    today = now_ist.date()
    yesterday = today - timedelta(days=1)

    historical_start = (
        today
        - timedelta(days=requested_days)
    )

    cfg = SUPPORTED_INTERVALS[interval]

    cache_key = (
        instrument_key,
        interval,
    )

    print()
    print("=" * 70)
    print("FAST UPSTOX HISTORICAL BOOTSTRAP")
    print("=" * 70)

    print(
        f"Symbol              : {symbol}"
    )

    print(
        f"Instrument           : "
        f"{instrument_key}"
    )

    print(
        f"Interval             : {interval}"
    )

    print(
        f"Historical from      : "
        f"{historical_start.isoformat()}"
    )

    print(
        f"Historical to        : "
        f"{yesterday.isoformat()}"
    )

    print(
        "Intraday refresh     : "
        "background (not startup critical)"
    )

    # ---------------------------------------------------------------
    # CACHE
    # ---------------------------------------------------------------

    cache_started = _time.perf_counter()

    candles = _cache_get(
        cache_key
    )

    cache_elapsed = (
        _time.perf_counter()
        - cache_started
    )

    if candles is not None:
        print(
            f"Cache hit            : yes "
            f"({cache_elapsed:.3f} sec)"
        )

    else:
        print(
            f"Cache hit            : no "
            f"({cache_elapsed:.3f} sec)"
        )

        # -----------------------------------------------------------
        # HISTORICAL API
        # -----------------------------------------------------------

        historical_started = (
            _time.perf_counter()
        )

        raw = _fetch_historical(
            instrument_key,
            cfg["unit"],
            cfg["interval"],
            yesterday.isoformat(),
            historical_start.isoformat(),
        )

        historical_elapsed = (
            _time.perf_counter()
            - historical_started
        )

        print(
            f"Historical candles   : "
            f"{len(raw)}"
        )

        print(
            f"[TIMING] Historical stage: "
            f"{historical_elapsed:.3f} sec"
        )

        # -----------------------------------------------------------
        # LOCAL PROCESSING
        # -----------------------------------------------------------

        processing_started = (
            _time.perf_counter()
        )

        candles = _prepare_completed_candles(
            symbol=symbol,
            interval=interval,
            instrument_key=instrument_key,
            raw_candles=raw,
            max_candles=max_candles,
            now_ist=now_ist,
        )

        processing_elapsed = (
            _time.perf_counter()
            - processing_started
        )

        print(
            f"[TIMING] Local processing: "
            f"{processing_elapsed:.3f} sec"
        )

        if not candles:
            raise ValueError(
                f"No valid historical candles "
                f"returned by Upstox for "
                f"{symbol} {interval}."
            )

        _cache_put(
            cache_key,
            candles,
            _time.monotonic(),
        )

    # ---------------------------------------------------------------
    # FINAL DATASET
    # ---------------------------------------------------------------

    print(
        f"Final completed      : "
        f"{len(candles)}"
    )

    print(
        f"Final first          : "
        f"{candles[0]['timestamp']}"
    )

    print(
        f"Final last           : "
        f"{candles[-1]['timestamp']}"
    )

    bootstrap_elapsed = (
        _time.perf_counter()
        - bootstrap_started
    )

    print(
        f"[TIMING] TOTAL historical "
        f"bootstrap: "
        f"{bootstrap_elapsed:.3f} sec"
    )

    print(
        "Historical bootstrap ready."
    )

    print("=" * 70)
    print()

    # ---------------------------------------------------------------
    # BUILD LIVE CANDLE STORE
    # ---------------------------------------------------------------

    store_started = _time.perf_counter()

    store = LiveCandleStore(
        max_candles=max_candles
    )

    for candle in candles[-max_candles:]:
        store.add_candle(candle)

    store_elapsed = (
        _time.perf_counter()
        - store_started
    )

    print(
        f"[TIMING] Store creation: "
        f"{store_elapsed:.3f} sec"
    )

    return store


def refresh_intraday_candles(
    symbol: str,
    interval: str,
    instrument_key: str,
    store: LiveCandleStore,
    max_candles: int = 200,
) -> int:
    """
    Refresh today's intraday candles without blocking
    historical bootstrap.

    Returns the number of new/updated completed candles
    added to `store`.

    A slow/empty intraday request is intentionally non-fatal
    because the historical dataset is already sufficient for
    initial analysis.
    """
    refresh_started = _time.perf_counter()

    interval = interval.strip().lower()

    if interval not in SUPPORTED_INTERVALS:
        raise ValueError(
            f"Unsupported interval '{interval}'. "
            f"Supported intervals: "
            f"{list(SUPPORTED_INTERVALS)}"
        )

    cfg = SUPPORTED_INTERVALS[interval]

    now_ist = datetime.now(IST)

    print()
    print("-" * 70)
    print(
        f"BACKGROUND INTRADAY REFRESH: "
        f"{symbol} {interval}"
    )
    print("-" * 70)

    # ---------------------------------------------------------------
    # INTRADAY API
    # ---------------------------------------------------------------

    request_started = _time.perf_counter()

    raw = _fetch_intraday(
        instrument_key,
        cfg["unit"],
        cfg["interval"],
    )

    request_elapsed = (
        _time.perf_counter()
        - request_started
    )

    print(
        f"[TIMING] Intraday request: "
        f"{request_elapsed:.3f} sec"
    )

    print(
        f"Intraday candles     : "
        f"{len(raw)}"
    )

    if not raw:
        total_elapsed = (
            _time.perf_counter()
            - refresh_started
        )

        print(
            "Intraday result empty; "
            "historical bootstrap remains valid."
        )

        print(
            f"[TIMING] Intraday refresh "
            f"total: {total_elapsed:.3f} sec"
        )

        print("-" * 70)
        print()

        return 0

    # ---------------------------------------------------------------
    # PROCESS INTRADAY DATA
    # ---------------------------------------------------------------

    processing_started = (
        _time.perf_counter()
    )

    completed = _prepare_completed_candles(
        symbol=symbol,
        interval=interval,
        instrument_key=instrument_key,
        raw_candles=raw,
        max_candles=max_candles,
        now_ist=now_ist,
    )

    processing_elapsed = (
        _time.perf_counter()
        - processing_started
    )

    print(
        f"[TIMING] Intraday processing: "
        f"{processing_elapsed:.3f} sec"
    )

    # ---------------------------------------------------------------
    # MERGE INTO LIVE STORE
    # ---------------------------------------------------------------

    merge_started = (
        _time.perf_counter()
    )

    before = store.count()

    for candle in completed:
        store.add_candle(candle)

    after = store.count()

    merge_elapsed = (
        _time.perf_counter()
        - merge_started
    )

    added = max(
        0,
        after - before,
    )

    print(
        f"Intraday merged      : "
        f"{len(completed)}"
    )

    print(
        f"Store count          : "
        f"{store.count()}"
    )

    print(
        f"[TIMING] Store merge: "
        f"{merge_elapsed:.3f} sec"
    )

    total_elapsed = (
        _time.perf_counter()
        - refresh_started
    )

    print(
        f"[TIMING] Intraday refresh "
        f"total: {total_elapsed:.3f} sec"
    )

    print("-" * 70)
    print()

    return added