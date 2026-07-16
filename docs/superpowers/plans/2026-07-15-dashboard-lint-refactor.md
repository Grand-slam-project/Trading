# Dashboard Lint Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `Dashboard.jsx`와 `MobileDashboardPage.jsx`의 중복 순수 로직을 `dashboardModel.js`로 분리하고, 두 파일의 명확한 lint warning을 줄인다.

**Architecture:** 대시보드 페이지 상단에 중복 정의된 통화 포맷, 계좌/보유자산 평가, 관심종목 판별, 잔고 병합 순수 함수를 공통 모델 파일로 이동한다. Supabase 호출, fetch 호출, React state setter, router 연동은 페이지에 남겨 동작 변경 위험을 낮춘다. 모델 파일은 Node test runner로 독립 검증한다.

**Tech Stack:** Vite React, JavaScript ESM, ESLint, Node 내장 test runner, Flask/Pytest 검증.

## Global Constraints

- 모든 설명과 계획서는 한국어로 작성한다.
- 코드 주석은 한국어로 작성하되, 코드 표준은 영문 식별자를 유지한다.
- git 커밋 메시지는 Conventional Commit prefix(`docs:`, `refactor:`, `test:`, `fix:` 등)는 영문으로 유지하고, 콜론 뒤 설명은 한글로 작성한다.
- `console.log`, 사용되지 않는 import, 사용되지 않는 변수, 주석 처리된 코드는 발견 즉시 삭제한다.
- UI 구조, 주문 정책, API 계약, Supabase 스키마는 이번 작업에서 변경하지 않는다.
- lint 규칙을 더 낮추거나 disable 주석을 추가해 warning을 숨기지 않는다.
- 기존 워크트리에 있는 사용자/이전 작업 변경은 되돌리지 않는다.

---

## File Structure

- Create: `frontend/src/pages/dashboardModel.js`
  - React와 Supabase에 의존하지 않는 Dashboard 공통 순수 함수와 상수를 보관한다.
- Create: `frontend/src/pages/dashboardModel.test.mjs`
  - `dashboardModel.js`의 포맷, 평가액, 계좌 병합, 관심종목 판별 로직을 검증한다.
- Modify: `frontend/src/pages/Dashboard.jsx`
  - 공통 모델 import로 전환하고 명확한 unused state/handler를 제거한다.
- Modify: `frontend/src/pages/mobile/MobileDashboardPage.jsx`
  - desktop과 동일하게 공통 모델 import로 전환하고 명확한 unused state/handler를 제거한다.
- Modify: `project_structure.md`
  - 새 모델 파일과 테스트 파일을 frontend pages 구조에 반영한다.
- Modify: `README.md`
  - 실제 lint warning 수와 Dashboard 1차 리팩토링 결과를 기록한다.

---

### Task 1: Dashboard 공통 모델 테스트 추가

**Files:**
- Create: `frontend/src/pages/dashboardModel.test.mjs`

**Interfaces:**
- Consumes: Task 2에서 만들 `frontend/src/pages/dashboardModel.js`
- Produces: 모델 함수의 기대 동작을 고정하는 실패 테스트

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/dashboardModel.test.mjs`:

```js
import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  buildBalanceRequests,
  getDashboardWatchlistAssetType,
  getDashboardWatchlistChartConfig,
  getDashboardWatchlistCurrency,
  getHoldingEvaluationKrw,
  getHoldingEvaluationNative,
  mergeAccountBalances,
  mergeBalanceWithCompletedTransfers,
  mergeBalanceWithTradeEstimates,
  normalizeDashboardTab,
  toKrwAmount,
} from './dashboardModel.js'

describe('dashboardModel', () => {
  it('normalizes dashboard tab with fallback', () => {
    assert.equal(normalizeDashboardTab('assets'), 'assets')
    assert.equal(normalizeDashboardTab('unknown-tab'), 'overview')
    assert.equal(normalizeDashboardTab(null), 'overview')
  })

  it('converts currencies to KRW using the representative exchange rate', () => {
    assert.equal(toKrwAmount(10, 'USD', 1500), 15000)
    assert.equal(toKrwAmount(2, 'USDT', 1400), 2800)
    assert.equal(toKrwAmount(3000, 'KRW', 1500), 3000)
    assert.equal(toKrwAmount('bad-value', 'USD', 1500), 0)
  })

  it('calculates holding evaluation in native and KRW values', () => {
    const usHolding = {
      qty: 3,
      current_price: 10,
      currency: 'USD',
    }
    const krHolding = {
      qty: 2,
      current_price: 50000,
      currency: 'KRW',
    }

    assert.equal(getHoldingEvaluationNative(usHolding), 30)
    assert.equal(getHoldingEvaluationKrw(usHolding, 1500), 45000)
    assert.equal(getHoldingEvaluationNative(krHolding), 100000)
    assert.equal(getHoldingEvaluationKrw(krHolding, 1500), 100000)
  })

  it('merges account balances and filters mock accounts', () => {
    const items = [
      {
        exchange: 'TOSS',
        raw_exchange: 'TOSS',
        env: 'REAL',
        currency: 'KRW',
        total_evaluation: 100000,
        available_cash: 50000,
        holdings: [
          {
            symbol: '005930',
            name: '삼성전자',
            qty: 1,
            avg_price: 70000,
            current_price: 80000,
            profit: 10000,
            currency: 'KRW',
          },
        ],
      },
      {
        exchange: 'KIS',
        raw_exchange: 'KIS',
        env: 'MOCK',
        currency: 'KRW',
        total_evaluation: 90000,
        available_cash: 10000,
        holdings: [
          {
            symbol: '000660',
            name: 'SK하이닉스',
            qty: 1,
            avg_price: 80000,
            current_price: 90000,
            profit: 10000,
            currency: 'KRW',
          },
        ],
      },
    ]

    const withMock = mergeAccountBalances(items, true)
    const withoutMock = mergeAccountBalances(items, false)

    assert.equal(withMock.total_evaluation, 190000)
    assert.equal(withMock.available_cash, 60000)
    assert.equal(withMock.holdings.length, 2)
    assert.equal(withoutMock.total_evaluation, 100000)
    assert.equal(withoutMock.available_cash, 50000)
    assert.equal(withoutMock.holdings.length, 1)
  })

  it('adds estimated trade holdings without duplicating live holdings', () => {
    const mergedBalance = {
      holdings: [
        {
          symbol: 'BTC',
          raw_exchange: 'COINONE',
          exchange: 'COINONE',
          env: 'REAL',
          asset_type: 'CRYPTO',
        },
      ],
      sources: ['COINONE'],
    }
    const tradeRows = [
      {
        status: 'EXECUTED',
        exchange: 'BINANCE',
        asset_type: 'CRYPTO',
        symbol: 'ETH',
        side: 'BUY',
        price: 2000,
        volume: 0.5,
        currency: 'USD',
        broker_env: 'REAL',
      },
    ]

    const result = mergeBalanceWithTradeEstimates(mergedBalance, tradeRows, true)

    assert.equal(result.holdings.length, 2)
    assert.equal(result.holdings[1].symbol, 'ETH')
    assert.equal(result.holdings[1].source, 'DB_ESTIMATED')
  })

  it('delegates completed transfer cash adjustments', () => {
    const mergedBalance = {
      available_cash: 100000,
      available_cash_breakdown: { KRW: 100000 },
      available_cash_breakdown_entries: [],
      cash_breakdown_by_currency: { KRW: [], USD: [], USDT: [] },
    }
    const transferRows = [
      {
        status: 'COMPLETED',
        from_exchange: 'COINONE',
        to_exchange: 'BINANCE',
        currency: 'XRP',
        amount: 10,
        received_amount: 9,
        expected_receive_amount: 9,
      },
    ]

    const result = mergeBalanceWithCompletedTransfers(mergedBalance, transferRows)

    assert.ok(result)
    assert.equal(typeof result, 'object')
  })

  it('classifies dashboard watchlist metadata', () => {
    const stockItem = { id: 'AAPL', market: '해외 주식', account: 'TOSS' }
    const cryptoItem = { id: 'BTC', market: '코인', account: 'COINONE' }
    const binanceItem = { id: 'ETHUSDT', market: '코인', account: 'BINANCE' }

    assert.equal(getDashboardWatchlistAssetType(stockItem), 'STOCK')
    assert.equal(getDashboardWatchlistCurrency(stockItem), 'USD')
    assert.deepEqual(getDashboardWatchlistChartConfig(stockItem), { exchange: 'TOSS', symbol: 'AAPL', brokerEnv: 'REAL' })
    assert.equal(getDashboardWatchlistAssetType(cryptoItem), 'CRYPTO')
    assert.equal(getDashboardWatchlistCurrency(cryptoItem), 'KRW')
    assert.deepEqual(getDashboardWatchlistChartConfig(cryptoItem), { exchange: 'COINONE', symbol: 'BTC', brokerEnv: 'REAL' })
    assert.equal(getDashboardWatchlistCurrency(binanceItem), 'USDT')
    assert.deepEqual(getDashboardWatchlistChartConfig(binanceItem), { exchange: 'BINANCE', symbol: 'ETHUSDT', brokerEnv: 'REAL' })
  })

  it('builds balance requests from registered key status', () => {
    const requests = buildBalanceRequests({
      TOSS: { registered: true, broker_env: 'REAL', accounts: [{ broker_env: 'REAL', toss_account_no: '123' }] },
      KIS: { registered: true, broker_env: 'MOCK' },
      COINONE: { registered: false },
      BINANCE: { registered: true, broker_env: 'REAL' },
    })

    assert.deepEqual(
      requests.map((request) => `${request.exchange}:${request.env}`),
      ['TOSS:REAL', 'KIS:MOCK', 'BINANCE:REAL', 'BINANCE_UM_FUTURES:REAL'],
    )
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
node --test frontend/src/pages/dashboardModel.test.mjs
```

Expected: FAIL with `Cannot find module` or missing export errors.

- [ ] **Step 3: Commit failing test**

Do not commit the failing test by itself. Keep it in the working tree for Task 2.

---

### Task 2: Dashboard 공통 모델 구현

**Files:**
- Create: `frontend/src/pages/dashboardModel.js`

**Interfaces:**
- Produces:
  - `BALANCE_EXCHANGE_ORDER: string[]`
  - `TRADE_PROPOSAL_HOLDING_FIELDS: string`
  - `TRANSFER_PROPOSAL_FIELDS: string`
  - `normalizeDashboardTab(tab: unknown): string`
  - `toNumber(value: unknown): number`
  - `formatCurrency(value: unknown, currency: string, displayCurrency?: string, exchangeRate?: number): string`
  - `formatUnitCurrency(value: unknown, currency: string, displayCurrency?: string, exchangeRate?: number): string`
  - `formatNullableCurrency(value: unknown, currency: string, displayCurrency?: string, exchangeRate?: number): string`
  - `normalizeSummaryCurrency(currency: unknown, source?: unknown): string`
  - `formatSummaryCurrency(value: unknown, currency: string): string`
  - `getSummarySourceLabel(source?: unknown): string`
  - `createCurrencySourceMap(): Record<string, object>`
  - `addCurrencySourceAmount(sourceMap: object, currency: string, source: string, amount: unknown): void`
  - `flattenCurrencySourceMap(sourceMap: object): object`
  - `fillSummaryDetailEntries(entries?: Array<object>, currency?: string): Array<object>`
  - `formatNativeCurrency(value: unknown, currency: string): string`
  - `getAccountDisplayLabel(item?: object): string`
  - `getAccountTone(exchange?: unknown): string`
  - `buildCashEntriesFromItem(item?: object): Array<object>`
  - `parsePriceNumber(value: unknown): number | null`
  - `getWatchlistCurrentPrice(item?: object): number | null`
  - `getDashboardWatchlistAssetType(item?: object): string`
  - `getDashboardWatchlistCurrency(item?: object): string`
  - `getDashboardWatchlistChartConfig(item?: object): { exchange: string, symbol: string, brokerEnv: string }`
  - `formatSignedRate(value: unknown): string`
  - `formatAllocationPercent(item?: object): string`
  - `getHoldingMarketType(holding?: object): string`
  - `getHoldingEvaluationKrw(holding?: object, exchangeRate?: number): number`
  - `getHoldingEvaluationNative(holding?: object): number`
  - `getHoldingsTotalNative(holdings?: Array<object>): number`
  - `getHoldingProfitBasis(holding?: object): { profit: number, invested: number }`
  - `getAccountExchangeCode(account?: object): string`
  - `isCryptoAccount(account?: object): boolean`
  - `toKrwAmount(value: unknown, currency?: string, exchangeRate?: number): number`
  - `toPositiveKrwAmount(value: unknown, currency?: string, exchangeRate?: number): number`
  - `getAccountCashKrw(account?: object, exchangeRate?: number): number`
  - `getPortfolioProfitRate(accountBalance?: object): number`
  - `mergeAccountBalances(items?: Array<object>, showMockAssets?: boolean): object`
  - `getHoldingIdentity(holding?: object): string`
  - `normalizeExchangeText(exchangeText?: unknown): string`
  - `getHoldingAccountScope(holding?: object): string`
  - `buildLiveAccountScopes(liveHoldings?: Array<object>, liveSources?: Array<string>): Set<string>`
  - `buildEstimatedHoldingsFromTrades(tradeRows?: Array<object>, liveHoldings?: Array<object>, showMockAssets?: boolean, liveSources?: Array<string>): Array<object>`
  - `mergeBalanceWithTradeEstimates(mergedBalance: object, tradeRows?: Array<object>, showMockAssets?: boolean): object`
  - `mergeBalanceWithCompletedTransfers(mergedBalance: object, transferRows?: Array<object>): object`
  - `getBalanceRequestLabel(exchange: string, env: string): string`
  - `getBalanceAccountLabel(exchange: string, env: string, account?: object): string`
  - `buildBalanceRequests(keyStatus: object): Array<object>`

- [ ] **Step 1: Create the model file**

Create `frontend/src/pages/dashboardModel.js`.

Implementation rule:

```js
import {
  deductCoinoneTransfersFromEstimatedHoldings,
  mergeCompletedTransfersIntoCash,
} from '../lib/transferBalanceAdjustments.js'
import { DASHBOARD_TAB_KEYS, DEFAULT_DASHBOARD_TAB } from '../dashboardConstants.js'
```

Then move the matching pure constants and functions from `frontend/src/pages/Dashboard.jsx` into this file. Do not move these functions:

```js
fetchDashboardWatchlistCurrentPrice
fetchTradeSymbolNameMap
fetchTransferRowsFromSupabase
RefreshIcon
HeartIcon
```

Keep `mergeBalanceWithCompletedTransfers` implemented as:

```js
export const mergeBalanceWithCompletedTransfers = (mergedBalance, transferRows = []) => (
  mergeCompletedTransfersIntoCash(mergedBalance, transferRows)
)
```

If moved functions call `deductCoinoneTransfersFromEstimatedHoldings`, keep the import available for later page use only when actually needed. If `dashboardModel.js` does not call it, remove that import from the model file.

- [ ] **Step 2: Export every moved declaration**

Every moved declaration must be exported with its complete implementation:

```js
export const BALANCE_EXCHANGE_ORDER = ['TOSS', 'KIS', 'COINONE', 'BINANCE', 'BINANCE_UM_FUTURES']
```

Do not default export.

- [ ] **Step 3: Run model tests**

Run:

```bash
node --test frontend/src/pages/dashboardModel.test.mjs
```

Expected: PASS.

- [ ] **Step 4: Commit model and test**

```bash
git add frontend/src/pages/dashboardModel.js frontend/src/pages/dashboardModel.test.mjs
git commit -m "test: Dashboard 모델 테스트 추가"
```

---

### Task 3: Dashboard 페이지 import 전환과 dead code 제거

**Files:**
- Modify: `frontend/src/pages/Dashboard.jsx`
- Modify: `frontend/src/pages/mobile/MobileDashboardPage.jsx`

**Interfaces:**
- Consumes: Task 2 exports from `frontend/src/pages/dashboardModel.js`
- Produces: 두 페이지가 공통 모델 함수를 import하고, 명확한 unused warning을 제거한다.

- [ ] **Step 1: Add imports to desktop Dashboard**

In `frontend/src/pages/Dashboard.jsx`, add this import after local imports:

```js
import {
  BALANCE_EXCHANGE_ORDER,
  TRADE_PROPOSAL_HOLDING_FIELDS,
  TRANSFER_PROPOSAL_FIELDS,
  buildBalanceRequests,
  buildEstimatedHoldingsFromTrades,
  fillSummaryDetailEntries,
  formatAllocationPercent,
  formatCurrency,
  formatNativeCurrency,
  formatNullableCurrency,
  formatSignedRate,
  formatSummaryCurrency,
  formatUnitCurrency,
  getAccountCashKrw,
  getAccountDisplayLabel,
  getAccountTone,
  getBalanceAccountLabel,
  getBalanceRequestLabel,
  getDashboardWatchlistAssetType,
  getDashboardWatchlistChartConfig,
  getDashboardWatchlistCurrency,
  getHoldingEvaluationKrw,
  getHoldingEvaluationNative,
  getHoldingMarketType,
  getPortfolioProfitRate,
  getSummarySourceLabel,
  getWatchlistCurrentPrice,
  mergeAccountBalances,
  mergeBalanceWithCompletedTransfers,
  mergeBalanceWithTradeEstimates,
  normalizeDashboardTab,
  parsePriceNumber,
  toNumber,
} from './dashboardModel.js'
```

Then delete the equivalent local declarations from `Dashboard.jsx`.

- [ ] **Step 2: Add imports to mobile Dashboard**

In `frontend/src/pages/mobile/MobileDashboardPage.jsx`, add this import after local imports:

```js
import {
  BALANCE_EXCHANGE_ORDER,
  TRADE_PROPOSAL_HOLDING_FIELDS,
  TRANSFER_PROPOSAL_FIELDS,
  buildBalanceRequests,
  buildEstimatedHoldingsFromTrades,
  fillSummaryDetailEntries,
  formatAllocationPercent,
  formatCurrency,
  formatNativeCurrency,
  formatNullableCurrency,
  formatSignedRate,
  formatSummaryCurrency,
  formatUnitCurrency,
  getAccountCashKrw,
  getAccountDisplayLabel,
  getAccountTone,
  getBalanceAccountLabel,
  getBalanceRequestLabel,
  getDashboardWatchlistAssetType,
  getDashboardWatchlistChartConfig,
  getDashboardWatchlistCurrency,
  getHoldingEvaluationKrw,
  getHoldingEvaluationNative,
  getHoldingMarketType,
  getPortfolioProfitRate,
  getSummarySourceLabel,
  getWatchlistCurrentPrice,
  mergeAccountBalances,
  mergeBalanceWithCompletedTransfers,
  mergeBalanceWithTradeEstimates,
  normalizeDashboardTab,
  parsePriceNumber,
  toNumber,
} from '../dashboardModel.js'
```

Then delete the equivalent local declarations from `MobileDashboardPage.jsx`.

- [ ] **Step 3: Keep async helpers in page files**

Do not delete these page-local functions:

```js
fetchDashboardWatchlistCurrentPrice
fetchTradeSymbolNameMap
fetchTransferRowsFromSupabase
loadAccountBalance
loadDashboardWatchlist
```

These functions depend on `fetch`, `supabase`, auth session, component state, or component lifecycle.

- [ ] **Step 4: Remove unused key test state and handlers**

In both Dashboard files, delete unused state:

```js
const [inputs, setInputs] = useState({
  appkey: '',
  appsecret: '',
  cano: '',
  env: 'MOCK'
})
const [encrypted, setEncrypted] = useState(null)
const [loading, setLoading] = useState(false)
const [message, setMessage] = useState({ text: '', isError: false })
```

Delete the complete unused `handleInputChange` and `handleTestKeys` function declarations from both files. The declarations currently start with:

```js
const handleInputChange = (e) => {
const handleTestKeys = async (e) => {
```

If deleting `handleTestKeys` leaves `DASHBOARD_API_BASE_URL` unused, keep `DASHBOARD_API_BASE_URL` only if `fetchDashboardWatchlistCurrentPrice`, `fetchTradeSymbolNameMap`, or `loadAccountBalance` still use it. Current code still uses it, so it should remain.

- [ ] **Step 5: Move loadDashboardWatchlist before the effect that calls it**

In both Dashboard files, move the complete existing `loadDashboardWatchlist` function declaration above the effect that calls it. The declaration currently starts with:

```js
const loadDashboardWatchlist = async ({ manual = false } = {}) => {
```

above:

```js
useEffect(() => {
  loadDashboardWatchlist()
}, [isLoggedIn, activeTab])
```

Do not change the function body in this step. This removes the React Compiler `immutability` warning for declaration-before-use without changing behavior.

- [ ] **Step 6: Run targeted lint**

Run:

```bash
cd frontend
npx eslint src/pages/Dashboard.jsx src/pages/mobile/MobileDashboardPage.jsx src/pages/dashboardModel.js src/pages/dashboardModel.test.mjs
```

Expected:

- `no-unused-vars` warnings for `formatKrw`, `encrypted`, `loading`, `message`, `handleInputChange`, `handleTestKeys` are gone.
- `react-hooks/immutability` for `loadDashboardWatchlist` declaration-before-use is gone.
- `react-hooks/exhaustive-deps` and `set-state-in-effect` warnings may remain if changing them would alter fetch/render lifecycle.

- [ ] **Step 7: Commit page refactor**

```bash
git add frontend/src/pages/Dashboard.jsx frontend/src/pages/mobile/MobileDashboardPage.jsx
git commit -m "refactor: Dashboard 공통 모델 적용"
```

---

### Task 4: 문서 최신화와 전체 검증

**Files:**
- Modify: `project_structure.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: Task 2 and Task 3 final file layout and actual lint count.
- Produces: 문서가 새 Dashboard 모델 파일과 실제 lint 상태를 반영한다.

- [ ] **Step 1: Update project structure**

In `project_structure.md`, add the new files under `frontend/src/pages/`:

```md
        ├── dashboardModel.js
        ├── dashboardModel.test.mjs
```

In frontend role notes, add:

```md
- `dashboardModel.js`
  - `Dashboard.jsx`와 `MobileDashboardPage.jsx`가 공유하는 통화 포맷, 자산 평가, 보유자산 병합, 관심종목 판별 순수 유틸
- `dashboardModel.test.mjs`
  - `dashboardModel.js`의 순수 함수 Node test
```

- [ ] **Step 2: Capture current lint summary**

Run:

```bash
cd frontend
npx eslint . --format json > /tmp/teamproject-eslint-after-dashboard.json
node -e 'const fs=require("fs"); const data=JSON.parse(fs.readFileSync("/tmp/teamproject-eslint-after-dashboard.json","utf8")); const warnings=data.reduce((sum,file)=>sum+file.warningCount,0); const errors=data.reduce((sum,file)=>sum+file.errorCount,0); console.log(JSON.stringify({errors,warnings}, null, 2));'
```

Expected: `errors` is `0`, `warnings` is less than previous baseline `109`.

- [ ] **Step 3: Update README with actual result**

In `README.md`, update the test/verification section by adding one bullet with the actual warning count from Step 2. The final sentence must contain the numeric warning count printed in Step 2:

```md
- 2026-07-15 Dashboard 1차 리팩토링: 공통 순수 유틸을 `frontend/src/pages/dashboardModel.js`로 분리하고 명확한 dead code warning을 제거했습니다. 전체 lint 상태는 `0 errors`, 101 warnings입니다.
```

- [ ] **Step 4: Run full verification**

Run:

```bash
node --test frontend/src/pages/dashboardModel.test.mjs
npm run lint
npm run build
python3 -m pytest -q
```

Expected:

- `node --test`: PASS
- `npm run lint`: exit code 0
- `npm run build`: exit code 0
- `python3 -m pytest -q`: PASS

- [ ] **Step 5: Commit docs**

```bash
git add project_structure.md README.md
git commit -m "docs: Dashboard 리팩토링 상태 기록"
```

---

## Self-Review

- Spec coverage: The plan covers common helper extraction, tests, dead code cleanup, declaration-before-use cleanup, verification, and documentation.
- Placeholder scan: No future-work placeholders remain in implementation steps.
- Type consistency: Export names in Task 2 match imports in Task 3.
- Scope check: Dashboard hook dependency lifecycle rewrites are intentionally outside this first implementation unless a local fix is proven safe during targeted lint.
