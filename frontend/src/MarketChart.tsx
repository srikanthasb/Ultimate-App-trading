import { useEffect, useRef } from 'react'
import {
  CandlestickSeries,
  ColorType,
  createChart,
  CrosshairMode,
  LineStyle,
  LineSeries,
  type IChartApi,
  type ISeriesApi,
  type Time,
  type UTCTimestamp,
} from 'lightweight-charts'
import type { Analysis, Candle } from './types'

type Props = {
  candles: Candle[]
  currentCandle?: Candle | null
  analysis?: Analysis | null
  signal: string
}

function timeOf(value: string): UTCTimestamp {
  return Math.floor(new Date(value).getTime() / 1000) as UTCTimestamp
}

/**
 * Lightweight Charts stores time as UTC timestamps.
 * We keep the actual timestamp unchanged and only convert the
 * displayed tick label to Indian Standard Time (Asia/Kolkata).
 */
function timestampFromChartTime(time: Time): number {
  if (typeof time === 'number') {
    return time
  }

  if (typeof time === 'string') {
    return Math.floor(Date.parse(time) / 1000)
  }

  return Math.floor(
    Date.UTC(time.year, time.month - 1, time.day) / 1000,
  )
}

function formatIST(time: Time): string {
  const timestamp = timestampFromChartTime(time)

  if (!Number.isFinite(timestamp)) {
    return ''
  }

  return new Intl.DateTimeFormat('en-IN', {
    timeZone: 'Asia/Kolkata',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date(timestamp * 1000))
}

function price(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

export default function MarketChart({
  candles,
  currentCandle,
  analysis,
  signal,
}: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const levelSeriesRef = useRef<Map<string, ISeriesApi<'Line'>>>(
    new Map(),
  )
  const userInteractedRef = useRef(false)
  const programmaticViewRef = useRef(false)
  const initializedViewRef = useRef(false)

  useEffect(() => {
    if (!containerRef.current) return

    const chart = createChart(containerRef.current, {
      layout: {
        background: {
          type: ColorType.Solid,
          color: '#ffffff',
        },
        textColor: '#5f6b7a',
        attributionLogo: false,
      },

      grid: {
        vertLines: { color: '#eef1f4' },
        horzLines: { color: '#eef1f4' },
      },

      crosshair: {
        mode: CrosshairMode.Normal,
      },

      rightPriceScale: {
        borderColor: '#dfe3e8',
        scaleMargins: {
          top: 0.08,
          bottom: 0.08,
        },
      },

      timeScale: {
        borderColor: '#dfe3e8',
        rightOffset: 5,
        barSpacing: 8,
        minBarSpacing: 3,
        fixLeftEdge: false,
        fixRightEdge: false,

        // IMPORTANT:
        // Candle timestamps remain absolute Unix timestamps.
        // Only the visible axis label is converted to IST.
        tickMarkFormatter: (time: Time) => formatIST(time),
      },

      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
      },

      handleScale: {
        mouseWheel: true,
        pinch: true,
        axisPressedMouseMove: true,
      },

      autoSize: true,
    })

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#16a34a',
      downColor: '#ef4444',
      borderUpColor: '#16a34a',
      borderDownColor: '#ef4444',
      wickUpColor: '#16a34a',
      wickDownColor: '#ef4444',
      priceLineVisible: false,
      lastValueVisible: true,
    })

    chartRef.current = chart
    candleRef.current = candleSeries

    const markInteraction = () => {
      if (!programmaticViewRef.current) {
        userInteractedRef.current = true
      }
    }

    chart.timeScale().subscribeVisibleTimeRangeChange(markInteraction)

    const resize = () => {
      chart.applyOptions({
        width: containerRef.current?.clientWidth ?? 0,
      })
    }

    window.addEventListener('resize', resize)

    return () => {
      window.removeEventListener('resize', resize)
      chart.remove()
      chartRef.current = null
      candleRef.current = null
      levelSeriesRef.current.clear()
    }
  }, [])

  useEffect(() => {
    const chart = chartRef.current
    const series = candleRef.current

    if (!chart || !series) return

    const byTime = new Map<
      number,
      {
        time: UTCTimestamp
        open: number
        high: number
        low: number
        close: number
      }
    >()

    for (const c of candles) {
      if (
        Number.isFinite(c.open) &&
        Number.isFinite(c.high) &&
        Number.isFinite(c.low) &&
        Number.isFinite(c.close)
      ) {
        const t = Number(timeOf(c.timestamp))

        byTime.set(t, {
          time: t as UTCTimestamp,
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
        })
      }
    }

    // The forming/live candle replaces the historical candle if both
    // have the same timestamp.
    if (
      currentCandle &&
      Number.isFinite(currentCandle.open) &&
      Number.isFinite(currentCandle.high) &&
      Number.isFinite(currentCandle.low) &&
      Number.isFinite(currentCandle.close)
    ) {
      const t = Number(timeOf(currentCandle.timestamp))

      byTime.set(t, {
        time: t as UTCTimestamp,
        open: currentCandle.open,
        high: currentCandle.high,
        low: currentCandle.low,
        close: currentCandle.close,
      })
    }

    const data = Array.from(byTime.values())
      .sort((a, b) => Number(a.time) - Number(b.time))
      .slice(-200)

    series.setData(data)

    if (!userInteractedRef.current && data.length) {
      programmaticViewRef.current = true

      if (!initializedViewRef.current) {
        chart.timeScale().fitContent()
        initializedViewRef.current = true
      } else {
        chart.timeScale().scrollToRealTime()
      }

      window.requestAnimationFrame(() => {
        programmaticViewRef.current = false
      })
    }
  }, [candles, currentCandle])

  useEffect(() => {
    const chart = chartRef.current

    if (!chart) return

    const plan = analysis?.trade_plan ?? {}

    const desired: Record<string, number | null> = {
      entry: price(plan.entry),
      stop: price(plan.stop_loss),
      target1: price(plan.target_1),
      target2: price(plan.target_2),
      trailing: price(plan.trailing_stop),
      support: price(plan.support),
      resistance: price(plan.resistance),
    }

    const configs: Record<
      string,
      { label: string; color: string }
    > = {
      entry: { label: 'ENTRY', color: '#2d9cdb' },
      stop: { label: 'STOP', color: '#eb5757' },
      target1: { label: 'TARGET 1', color: '#27ae60' },
      target2: { label: 'TARGET 2', color: '#219653' },
      trailing: { label: 'TRAIL', color: '#9b51e0' },
      support: { label: 'SUPPORT', color: '#56ccf2' },
      resistance: { label: 'RESISTANCE', color: '#f2c94c' },
    }

    for (const [key, value] of Object.entries(desired)) {
      const existing = levelSeriesRef.current.get(key)

      if (value == null) {
        if (existing) {
          chart.removeSeries(existing)
          levelSeriesRef.current.delete(key)
        }
        continue
      }

      const config = configs[key]

      const line =
        existing ??
        chart.addSeries(LineSeries, {
          color: config.color,
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          title: config.label,
          priceLineVisible: true,
          lastValueVisible: true,
        })

      const first = candles.length
        ? timeOf(candles[0].timestamp)
        : (Math.floor(Date.now() / 1000) - 3600) as UTCTimestamp

      const last = currentCandle
        ? timeOf(currentCandle.timestamp)
        : candles.length
          ? timeOf(candles[candles.length - 1].timestamp)
          : Math.floor(Date.now() / 1000) as UTCTimestamp

      const span = Math.max(
        Number(last) - Number(first),
        3600,
      )

      line.setData([
        {
          time: (
            Number(first) - Math.floor(span * 0.02)
          ) as UTCTimestamp,
          value,
        },
        {
          time: (
            Number(last) + Math.floor(span * 0.02)
          ) as UTCTimestamp,
          value,
        },
      ])

      levelSeriesRef.current.set(key, line)
    }
  }, [analysis, signal, candles, currentCandle])

  return (
    <div
      ref={containerRef}
      className="chart-container"
      aria-label="Live market chart"
    />
  )
}
