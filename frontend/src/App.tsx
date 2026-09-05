import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import {
  searchInstruments,
  setIntervalRemote,
  startLive,
  stopLive,
  WS_URL,
} from './api'
import MarketChart from './MarketChart'
import type {
  Analysis,
  Candle,
  Instrument,
  SnapshotMessage,
  State,
  StateMessage,
  TickMessage,
} from './types'

const INTERVALS = ['1m', '3m', '5m', '10m', '15m', '30m', '1h']

type Status =
  | 'OFFLINE'
  | 'CONNECTING'
  | 'LIVE'
  | 'WAITING'
  | 'RECONNECTING'

function money(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value)
    ? `₹${value.toFixed(2)}`
    : '—'
}

function pct(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value)
    ? `${value.toFixed(0)}%`
    : '—'
}

export default function App() {
  const [state, setState] = useState<State>({})
  const [candles, setCandles] = useState<Candle[]>([])
  const [currentCandle, setCurrentCandle] =
    useState<Candle | null>(null)
  const [analysis, setAnalysis] =
    useState<Analysis | null>(null)

  const [instrument, setInstrument] =
    useState<Instrument | null>(null)

  const [interval, setInterval] = useState('1m')

  const [search, setSearch] = useState('')
  const [results, setResults] = useState<Instrument[]>([])
  const [searching, setSearching] = useState(false)

  const [error, setError] = useState('')

  const [wsStatus, setWsStatus] =
    useState<Status>('CONNECTING')

  // ---------------------------------------------------------------
  // UI operation states
  // ---------------------------------------------------------------

  const [starting, setStarting] = useState(false)
  const [stopping, setStopping] = useState(false)
  const [changingInterval, setChangingInterval] =
    useState(false)

  const socketRef = useRef<WebSocket | null>(null)
  const runningRef = useRef(false)

  const reconnectTimerRef =
    useRef<number | null>(null)

  const retryRef = useRef(0)

  // ---------------------------------------------------------------
  // Keep runningRef synchronized
  // ---------------------------------------------------------------

  useEffect(() => {
    runningRef.current = Boolean(state.running)
  }, [state.running])

  // ---------------------------------------------------------------
  // Browser WebSocket
  // ---------------------------------------------------------------

  const connect = useCallback(() => {
    const existing = socketRef.current

    if (
      existing?.readyState === WebSocket.OPEN ||
      existing?.readyState === WebSocket.CONNECTING
    ) {
      return
    }

    setWsStatus(
      retryRef.current
        ? 'RECONNECTING'
        : 'CONNECTING'
    )

    const socket = new WebSocket(WS_URL)

    socketRef.current = socket

    socket.onopen = () => {
      retryRef.current = 0

      setWsStatus(
        runningRef.current
          ? 'LIVE'
          : 'WAITING'
      )
    }

    socket.onmessage = (event) => {
      try {
        const message =
          JSON.parse(event.data) as
            | SnapshotMessage
            | StateMessage
            | TickMessage

        // ---------------------------------------------------------
        // Snapshot
        // ---------------------------------------------------------

        if (message.type === 'snapshot') {
          setState(message.state)

          setCandles(
            message.candles ?? []
          )

          setCurrentCandle(
            message.current_candle ?? null
          )

          setAnalysis(
            message.analysis ?? null
          )

          if (
            message.state.selected_interval
          ) {
            setInterval(
              message.state.selected_interval
            )
          }

          if (
            message.state.instrument_key &&
            !instrument
          ) {
            setInstrument({
              instrument_key:
                message.state.instrument_key,
              trading_symbol:
                message.state.symbol,
            })
          }

          setWsStatus(
            message.state.websocket_connected
              ? 'LIVE'
              : message.state.running
                ? 'WAITING'
                : 'WAITING'
          )

          return
        }

        // ---------------------------------------------------------
        // State
        // ---------------------------------------------------------

        if (message.type === 'state') {
          setState(message.state)

          setWsStatus(
            message.state.websocket_connected
              ? 'LIVE'
              : message.state.running
                ? 'WAITING'
                : 'WAITING'
          )

          return
        }

        // ---------------------------------------------------------
        // Live tick
        // ---------------------------------------------------------

        if (message.type === 'tick') {
          setState(message.state)

          setCurrentCandle(
            message.current_candle ?? null
          )

          if (
            message.completed_candles?.length
          ) {
            setCandles((previous) => {
              const byTime =
                new Map(
                  previous.map(
                    (candle) => [
                      candle.timestamp,
                      candle,
                    ]
                  )
                )

              for (
                const candle of
                  message.completed_candles ?? []
              ) {
                byTime.set(
                  candle.timestamp,
                  candle
                )
              }

              return Array.from(
                byTime.values()
              )
                .sort(
                  (a, b) =>
                    new Date(
                      a.timestamp
                    ).getTime() -
                    new Date(
                      b.timestamp
                    ).getTime()
                )
                .slice(-200)
            })
          }

          if (message.analysis) {
            setAnalysis(
              message.analysis
            )
          }

          setWsStatus(
            message.state.websocket_connected
              ? 'LIVE'
              : 'RECONNECTING'
          )
        }
      } catch (e) {
        console.error(
          'WebSocket message error',
          e
        )
      }
    }

    socket.onerror = () => {
      setWsStatus('RECONNECTING')
    }

    socket.onclose = () => {
      socketRef.current = null

      setWsStatus('RECONNECTING')

      const delay = Math.min(
        1000 *
          2 ** retryRef.current,
        10000
      )

      retryRef.current += 1

      reconnectTimerRef.current =
        window.setTimeout(
          connect,
          delay
        )
    }
  }, [instrument])

  // ---------------------------------------------------------------
  // Connect once
  // ---------------------------------------------------------------

  useEffect(() => {
    connect()

    return () => {
      if (
        reconnectTimerRef.current
      ) {
        window.clearTimeout(
          reconnectTimerRef.current
        )
      }

      socketRef.current?.close()
    }
  }, [connect])

  // ---------------------------------------------------------------
  // Search
  // ---------------------------------------------------------------

  async function doSearch() {
    if (!search.trim()) {
      return
    }

    setSearching(true)
    setError('')

    try {
      const response =
        await searchInstruments(
          search.trim()
        )

      setResults(
        response.instruments ?? []
      )
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : 'Instrument search failed'
      )
    } finally {
      setSearching(false)
    }
  }

  // ---------------------------------------------------------------
  // Choose instrument
  // ---------------------------------------------------------------

  async function chooseInstrument(
    item: Instrument
  ) {
    // If another live session is running, stop it first.
    if (state.running || starting) {
      setError(
        'Stop the current live feed before selecting another instrument.'
      )
      return
    }

    setInstrument(item)
    setResults([])
    setSearch(
      item.trading_symbol ?? ''
    )
    setError('')
  }

  // ---------------------------------------------------------------
  // Start
  // ---------------------------------------------------------------

  async function handleStart() {
    if (
      !instrument?.instrument_key ||
      !instrument.trading_symbol ||
      starting ||
      state.running
    ) {
      return
    }

    setError('')
    setStarting(true)
    setWsStatus('CONNECTING')

    try {
      await startLive(
        instrument,
        interval
      )
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : 'Unable to start live feed'
      )

      setWsStatus('WAITING')
    } finally {
      setStarting(false)
    }
  }

  // ---------------------------------------------------------------
  // Stop
  // ---------------------------------------------------------------

  async function handleStop() {
    if (stopping) {
      return
    }

    setError('')
    setStopping(true)

    try {
      await stopLive()

      setCandles([])
      setCurrentCandle(null)
      setAnalysis(null)
      setState({})
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : 'Unable to stop live feed'
      )
    } finally {
      setStopping(false)
    }
  }

  // ---------------------------------------------------------------
  // Change timeframe
  // ---------------------------------------------------------------

  async function handleInterval(
    next: string
  ) {
    if (
      next === interval ||
      changingInterval ||
      !state.running
    ) {
      return
    }

    setError('')
    setChangingInterval(true)

    try {
      await setIntervalRemote(next)

      // Backend publishes a snapshot after the change.
      // We also update immediately for responsive UI.
      setInterval(next)

      setCandles([])
      setCurrentCandle(null)
      setAnalysis(null)
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : 'Unable to change timeframe'
      )
    } finally {
      setChangingInterval(false)
    }
  }

  // ---------------------------------------------------------------
  // Derived values
  // ---------------------------------------------------------------

  const decision =
    analysis?.decision ?? {}

  const trade =
    analysis?.trade_plan ?? {}

  const technical =
    analysis?.technical_signal ?? {}

  const ai =
    analysis?.ai_analysis ?? {}

  const risk =
    analysis?.risk ?? {}

  const signal =
    String(
      decision.final_signal ?? 'HOLD'
    ).toUpperCase()

  const symbol =
    instrument?.trading_symbol ??
    state.symbol ??
    'Select an instrument'

  const ltp =
    state.latest_tick?.price

  const statusLabel: Record<
    Status,
    string
  > = {
    OFFLINE: '○ OFFLINE',
    CONNECTING: '◌ CONNECTING',
    LIVE: '● LIVE',
    WAITING: '◌ WAITING',
    RECONNECTING: '↻ RECONNECTING',
  }

  const signalClass =
    signal === 'BUY'
      ? 'buy'
      : signal === 'SELL'
        ? 'sell'
        : 'hold'

  const hasLive =
    Boolean(state.running)

  const chartKey = useMemo(
    () =>
      `${
        state.instrument_key ??
        symbol
      }:${interval}`,
    [
      state.instrument_key,
      symbol,
      interval,
    ]
  )

  // ---------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------

  return (
    <main className="app-shell">

      <header className="topbar">
        <div>
          <div className="brand">
            <span className="brand-mark">
              ↗
            </span>
            AI Investment
          </div>

          <div className="subtitle">
            Real-time market intelligence ·
            deterministic confluence ·
            AI-assisted risk guidance
          </div>
        </div>

        <div className="connection-pill">
          <span
            className={`status-dot ${
              wsStatus.toLowerCase()
            }`}
          />

          {statusLabel[wsStatus]}
        </div>
      </header>

      <section className="control-bar">

        <div className="instrument-area">
          <label>
            Instrument
          </label>

          <div className="search-row">
            <input
              value={search}
              onChange={(e) =>
                setSearch(e.target.value)
              }
              onKeyDown={(e) =>
                e.key === 'Enter' &&
                doSearch()
              }
              disabled={
                hasLive ||
                starting
              }
              placeholder="Search NSE equity e.g. HDFCBANK"
            />

            <button
              onClick={doSearch}
              disabled={
                searching ||
                hasLive ||
                starting
              }
            >
              {searching
                ? 'Searching…'
                : 'Search'}
            </button>
          </div>

          {results.length > 0 && (
            <div className="results-panel">
              {results.map(
                (
                  item,
                  index
                ) => (
                  <button
                    className="result"
                    key={`${item.instrument_key}-${index}`}
                    onClick={() =>
                      chooseInstrument(
                        item
                      )
                    }
                  >
                    <span>
                      <strong>
                        {
                          item.trading_symbol
                        }
                      </strong>
                      {' · '}
                      {item.name}
                    </span>

                    <small>
                      {
                        item.instrument_key
                      }
                    </small>
                  </button>
                )
              )}
            </div>
          )}
        </div>

        <div className="instrument-selected">
          <strong>
            {symbol}
          </strong>

          {instrument?.instrument_key && (
            <span>
              {
                instrument.instrument_key
              }
            </span>
          )}
        </div>

        <div className="action-area">

          {!hasLive ? (
            <button
              className={
                starting
                  ? 'primary loading'
                  : 'primary'
              }
              onClick={
                handleStart
              }
              disabled={
                !instrument?.instrument_key ||
                starting
              }
            >
              {starting
                ? 'Starting…'
                : '▶ Start Live'}
            </button>
          ) : (
            <button
              className="danger"
              onClick={
                handleStop
              }
              disabled={
                stopping
              }
            >
              {stopping
                ? 'Stopping…'
                : '■ Stop'}
            </button>
          )}

        </div>
      </section>

      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}

      {hasLive && (
        <>

          <section className="market-header">
            <div>
              <div className="symbol-line">
                <span>
                  {symbol}
                </span>

                <span className="muted">
                  {
                    state.instrument_key
                  }
                </span>
              </div>

              <div className="price-line">
                {money(ltp)}

                <span className="market-state">
                  {
                    state.websocket_connected
                      ? 'LIVE FEED'
                      : 'WAITING FOR FEED'
                  }
                </span>
              </div>
            </div>

            <div
              className={`decision-card ${signalClass}`}
            >
              <div className="decision-label">
                GUIDANCE
              </div>

              <div className="decision-signal">
                {signal}
              </div>

              <div className="decision-meta">
                {
                  decision.trend ??
                  '—'
                }
                {' · '}
                {
                  decision.momentum ??
                  '—'
                }
              </div>
            </div>
          </section>

          <section className="timeframe-row">

            {INTERVALS.map(
              (item) => (
                <button
                  key={item}
                  className={
                    item === interval
                      ? 'active'
                      : ''
                  }
                  onClick={() =>
                    handleInterval(
                      item
                    )
                  }
                  disabled={
                    changingInterval
                  }
                >
                  {
                    changingInterval &&
                    item === interval
                      ? '…'
                      : item
                  }
                </button>
              )
            )}

            <span className="chart-note">
              Wheel = zoom · drag = pan ·
              chart view is preserved during
              live ticks
            </span>
          </section>

          <section
            className="chart-card"
            key={chartKey}
          >
            <MarketChart
              candles={candles}
              currentCandle={
                currentCandle
              }
              analysis={analysis}
              signal={signal}
            />

            <div className="chart-overlay top-left">
              <strong>
                Confluence
              </strong>

              <span>
                {
                  technical.strategy_count ??
                  0
                } strategies
              </span>

              <span>
                Bull {
                  technical.bullish_score ??
                  '—'
                }
                {' · '}
                Bear {
                  technical.bearish_score ??
                  '—'
                }
              </span>
            </div>

            <div className="chart-overlay top-right">
              <span>
                Technical {
                  pct(
                    decision.technical_alignment
                  )
                }
              </span>

              <span>
                AI {
                  pct(
                    decision.ai_confidence
                  )
                }
              </span>
            </div>
          </section>

          <section className="plan-grid">

            <Metric
              label="Entry"
              value={money(
                trade.entry
              )}
            />

            <Metric
              label="Stop loss"
              value={money(
                trade.stop_loss
              )}
            />

            <Metric
              label="Target 1"
              value={money(
                trade.target_1
              )}
            />

            <Metric
              label="Target 2"
              value={money(
                trade.target_2
              )}
            />

            <Metric
              label="Quantity"
              value={
                trade.position_size ??
                '—'
              }
            />

            <Metric
              label="Risk / reward"
              value={
                trade.risk_reward_1
                  ? `1:${trade.risk_reward_1} / 1:${
                      trade.risk_reward_2 ??
                      '—'
                    }`
                  : '—'
              }
            />

          </section>

          {signal === 'HOLD' && (
            <div className="hold-strip">
              <strong>
                HOLD — no forced trade.
              </strong>

              {' Support '}
              {money(
                trade.support
              )}

              {' · Resistance '}
              {money(
                trade.resistance
              )}

              {' · '}

              {
                trade.reason ??
                'Wait for stronger confirmation.'
              }
            </div>
          )}

          <section className="details-grid">

            <Detail
              title="Strategy confluence"
            >
              <div className="strategy-score">
                <span>
                  Bull {
                    technical.bullish_score ??
                    '—'
                  }
                </span>

                <span>
                  Bear {
                    technical.bearish_score ??
                    '—'
                  }
                </span>

                <span>
                  Alignment {
                    pct(
                      technical.technical_alignment
                    )
                  }
                </span>
              </div>

              {(
                technical.strategies ??
                []
              ).map(
                (
                  item: any,
                  index: number
                ) => (
                  <div
                    className="strategy-row"
                    key={`${item.name}-${index}`}
                  >
                    <b>
                      {item.name}
                    </b>

                    <span>
                      {item.signal}
                    </span>

                    <small>
                      {item.reason}
                    </small>
                  </div>
                )
              )}
            </Detail>

            <Detail
              title="AI interpretation"
            >
              <p>
                {
                  ai.summary ??
                  'Waiting for AI interpretation.'
                }
              </p>

              {(
                ai.reasons ??
                []
              ).map(
                (
                  reason: string,
                  index: number
                ) => (
                  <div
                    className="reason"
                    key={index}
                  >
                    • {reason}
                  </div>
                )
              )}
            </Detail>

            <Detail
              title="Risk control"
            >
              <div className="risk-row">
                <span>
                  Risk
                </span>

                <b>
                  {
                    risk.risk ??
                    '—'
                  }
                </b>
              </div>

              <div className="risk-row">
                <span>
                  Risk score
                </span>

                <b>
                  {
                    risk.risk_score ??
                    '—'
                  }
                </b>
              </div>

              <div className="risk-row">
                <span>
                  Risk/share
                </span>

                <b>
                  {
                    money(
                      trade.risk_per_share
                    )
                  }
                </b>
              </div>

              <div className="risk-row">
                <span>
                  Trailing stop
                </span>

                <b>
                  {
                    money(
                      trade.trailing_stop
                    )
                  }
                </b>
              </div>

              <p>
                {
                  trade.reason ??
                  'No trade plan generated.'
                }
              </p>
            </Detail>

          </section>

          <details className="raw-details">
            <summary>
              Calculated market snapshot
            </summary>

            <pre>
              {
                JSON.stringify(
                  analysis?.snapshot ??
                    {},
                  null,
                  2
                )
              }
            </pre>
          </details>

        </>
      )}

      {!hasLive && (
        <section className="welcome">

          <div className="welcome-icon">
            ↗
          </div>

          <h1>
            Choose an NSE instrument
            to begin
          </h1>

          <p>
            The trading screen stays
            browser-native and continuously
            sharp. Live ticks update the
            existing chart instead of
            rebuilding the page.
          </p>

          {starting && (
            <div className="starting-message">
              Loading {interval} market data
              and connecting to the live feed…
            </div>
          )}

        </section>
      )}

    </main>
  )
}

function Metric({
  label,
  value,
}: {
  label: string
  value: string | number
}) {
  return (
    <div className="metric">
      <span>
        {label}
      </span>

      <strong>
        {value}
      </strong>
    </div>
  )
}

function Detail({
  title,
  children,
}: {
  title: string
  children: ReactNode
}) {
  return (
    <article className="detail-card">
      <h3>
        {title}
      </h3>

      {children}
    </article>
  )
}
