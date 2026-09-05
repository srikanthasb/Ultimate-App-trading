export type Instrument = {
  name?: string | null
  short_name?: string | null
  trading_symbol?: string | null
  instrument_key?: string | null
  exchange?: string | null
  segment?: string | null
  instrument_type?: string | null
  isin?: string | null
  lot_size?: number | null
  tick_size?: number | null
}

export type Candle = {
  symbol: string
  instrument_key?: string
  interval: string
  timestamp: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export type Tick = {
  symbol: string
  instrument_key: string
  price: number
  timestamp_ms: number
  quantity: number
}

export type TradePlan = Record<string, any>
export type Analysis = {
  snapshot?: Record<string, any>
  technical_signal?: Record<string, any>
  ai_analysis?: Record<string, any>
  decision?: Record<string, any>
  risk?: Record<string, any>
  trade_plan?: TradePlan
}

export type State = {
  running?: boolean
  symbol?: string
  instrument_key?: string
  selected_interval?: string
  latest_tick?: Tick | null
  analysis_available?: boolean
  analysis_error?: string | null
  websocket_connected?: boolean
  websocket_error?: string | null
  websocket_connected_at?: string | null
  last_websocket_message_at?: string | null
  websocket_mode?: string
  candle_counts?: Record<string, number>
}

export type SnapshotMessage = {
  type: 'snapshot'
  state: State
  candles: Candle[]
  current_candle?: Candle | null
  completed_candles?: Candle[]
  analysis?: Analysis | null
}

export type StateMessage = {
  type: 'state'
  state: State
}

export type TickMessage = {
  type: 'tick'
  state: State
  tick: Tick
  current_candle?: Candle | null
  completed_candles?: Candle[]
  analysis?: Analysis | null
}
