import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'


const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)


test('알 수 없는 필드는 빈 값으로 유지한다', async () => {
  const { normalizeOrderFormPrefill } = await import('./chatbotOrderForm.js')

  assert.deepEqual(normalizeOrderFormPrefill({ symbol_query: 'XRP', quantity: 10 }), {
    exchange: '',
    broker_env: '',
    side: '',
    symbol_query: 'XRP',
    quantity: '10',
    order_type: '',
    price: '',
  })
})


test('허용되지 않은 선택값과 숫자는 폼에 반영하지 않는다', async () => {
  const { normalizeOrderFormPrefill } = await import('./chatbotOrderForm.js')

  assert.deepEqual(normalizeOrderFormPrefill({
    exchange: 'UPBIT',
    broker_env: 'PAPER',
    side: 'HOLD',
    symbol_query: '  BTC  ',
    quantity: -1,
    order_type: 'STOP',
    price: 'not-a-number',
  }), {
    exchange: '',
    broker_env: '',
    side: '',
    symbol_query: 'BTC',
    quantity: '',
    order_type: '',
    price: '',
  })
})


test('정상적인 임시 입력값은 폼 문자열로 정규화한다', async () => {
  const { normalizeOrderFormPrefill } = await import('./chatbotOrderForm.js')

  assert.deepEqual(normalizeOrderFormPrefill({
    exchange: 'COINONE',
    broker_env: 'REAL',
    side: 'BUY',
    symbol_query: 'XRP',
    quantity: 10,
    order_type: 'LIMIT',
    price: 800,
  }), {
    exchange: 'COINONE',
    broker_env: 'REAL',
    side: 'BUY',
    symbol_query: 'XRP',
    quantity: '10',
    order_type: 'LIMIT',
    price: '800',
  })
})


test('챗봇 주문 행동은 임시값을 폼에 전달하고 자동 제출하지 않는다', () => {
  const source = readFileSync(resolve(__dirname, 'ChatbotWidget.jsx'), 'utf8')

  assert.match(source, /action\?\.type === 'open_order_form'/)
  assert.match(source, /setOrderFormInitialValues\(normalizeOrderFormPrefill\(action\.prefill\)\)/)
  assert.match(source, /<ChatOrderForm[\s\S]*?initialValues=\{orderFormInitialValues\}/)
  assert.match(source, /챗봇이 인식한 임시 입력값입니다/)
  assert.equal(source.includes('alert('), false)
})
