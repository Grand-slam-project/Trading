const EXCHANGES = new Set(['TOSS', 'KIS', 'COINONE', 'BINANCE'])
const BROKER_ENVS = new Set(['REAL', 'MOCK'])
const SIDES = new Set(['BUY', 'SELL'])
const ORDER_TYPES = new Set(['LIMIT', 'MARKET'])

function normalizeChoice(value, allowedValues) {
  const normalized = String(value || '').trim().toUpperCase()
  return allowedValues.has(normalized) ? normalized : ''
}

function toPositiveText(value) {
  if (value === null || value === undefined || value === '') return ''
  const numberValue = Number(value)
  return Number.isFinite(numberValue) && numberValue > 0 ? String(numberValue) : ''
}

export function normalizeOrderFormPrefill(prefill = {}) {
  return {
    exchange: normalizeChoice(prefill.exchange, EXCHANGES),
    broker_env: normalizeChoice(prefill.broker_env, BROKER_ENVS),
    side: normalizeChoice(prefill.side, SIDES),
    symbol_query: String(prefill.symbol_query || '').trim(),
    quantity: toPositiveText(prefill.quantity),
    order_type: normalizeChoice(prefill.order_type, ORDER_TYPES),
    price: toPositiveText(prefill.price),
  }
}
