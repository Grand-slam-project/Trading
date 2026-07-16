# Asset Detail Lint Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `AssetDetail.jsx`와 `MobileAssetDetail.jsx`의 중복 순수 로직을 공통 모델 파일로 추출하고, 해당 파일군의 명확한 lint warning을 줄인다.

**Architecture:** React 페이지 내부에 흩어진 상수와 순수 변환 함수를 `frontend/src/pages/assetDetailModel.js`로 이동한다. 새 모델 파일은 React, router, DOM, Supabase에 의존하지 않으며 Node test runner로 독립 검증한다. 페이지 파일은 import만 사용하도록 바꾸고, 동작 영향이 작은 dead code warning부터 제거한다.

**Tech Stack:** Vite React, JavaScript ESM, ESLint, Node 내장 test runner, Flask/Pytest 검증.

## Global Constraints

- 모든 설명과 계획서는 한국어로 작성한다.
- 코드 주석은 한국어로 작성하되, 코드 표준은 영문 식별자를 유지한다.
- `console.log`, 사용되지 않는 import, 사용되지 않는 변수, 주석 처리된 코드는 발견 즉시 삭제한다.
- UI 구조, 주문 정책, API 계약, Supabase 스키마는 이번 작업에서 변경하지 않는다.
- lint 규칙을 더 낮추거나 disable 주석을 추가해 warning을 숨기지 않는다.
- 기존 워크트리에 있는 사용자/이전 작업 변경은 되돌리지 않는다.

---

### Task 1: Asset Detail 공통 모델과 테스트 추가

**Files:**
- Create: `frontend/src/pages/assetDetailModel.js`
- Create: `frontend/src/pages/assetDetailModel.test.mjs`

**Interfaces:**
- Produces:
  - `ACTIONABLE_ORDER_STATUSES: string[]`
  - `STOCK_WARNING_BADGE_META: Record<string, { tone: string }>`
  - `isActionableOrderStatus(status: unknown): boolean`
  - `isCancelReplaceExchange(exchange: unknown): boolean`
  - `getStockWarningBadgeTone(warningType: unknown): string`
  - `getOrderStatusLabel(status: unknown): string`
  - `getOrderSideLabel(side: unknown): string`
  - `getAutoRuleStatusLabel(status: unknown): string`
  - `getAutoExecutionModeLabel(mode: unknown): string`
  - `getAutoTriggerLabel(triggerSide: unknown): string`
  - `normalizeStockSymbol(value: unknown): string`
  - `isDomesticStockSymbol(value: unknown): boolean`
  - `isUsStockSymbol(value: unknown, market?: unknown): boolean`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/assetDetailModel.test.mjs`:

```js
import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  getAutoExecutionModeLabel,
  getAutoRuleStatusLabel,
  getAutoTriggerLabel,
  getOrderSideLabel,
  getOrderStatusLabel,
  getStockWarningBadgeTone,
  isActionableOrderStatus,
  isCancelReplaceExchange,
  isDomesticStockSymbol,
  isUsStockSymbol,
  normalizeStockSymbol,
} from './assetDetailModel.js'

describe('assetDetailModel', () => {
  it('normalizes and classifies stock symbols', () => {
    assert.equal(normalizeStockSymbol(' aapl '), 'AAPL')
    assert.equal(isDomesticStockSymbol('005930'), true)
    assert.equal(isDomesticStockSymbol('AAPL'), false)
    assert.equal(isUsStockSymbol('AAPL'), true)
    assert.equal(isUsStockSymbol('005930'), false)
    assert.equal(isUsStockSymbol('005930', 'US'), true)
    assert.equal(isUsStockSymbol('AAPL', 'KR'), false)
  })

  it('classifies actionable order statuses and cancel-replace exchanges', () => {
    assert.equal(isActionableOrderStatus('open'), true)
    assert.equal(isActionableOrderStatus('executed'), false)
    assert.equal(isCancelReplaceExchange('COINONE'), true)
    assert.equal(isCancelReplaceExchange('BINANCE_UM_FUTURES'), true)
    assert.equal(isCancelReplaceExchange('TOSS'), false)
  })

  it('returns Korean labels for order and auto rule states', () => {
    assert.equal(getOrderStatusLabel('PENDING'), '미체결')
    assert.equal(getOrderStatusLabel('APPROVED'), '접수 완료')
    assert.equal(getOrderStatusLabel('EXECUTED'), '체결완료')
    assert.equal(getOrderStatusLabel('CANCELLED'), '취소완료')
    assert.equal(getOrderStatusLabel('FAILED'), '실패')
    assert.equal(getOrderStatusLabel('UNKNOWN_STATUS'), 'UNKNOWN_STATUS')
    assert.equal(getOrderSideLabel('SELL'), '매도')
    assert.equal(getOrderSideLabel('BUY'), '매수')
    assert.equal(getAutoRuleStatusLabel('RUNNING'), '감시 중')
    assert.equal(getAutoRuleStatusLabel('COMPLETED'), '완료')
    assert.equal(getAutoRuleStatusLabel('STOPPED'), '정지')
    assert.equal(getAutoExecutionModeLabel('AUTO'), '조건 도달 시 자동 매도')
    assert.equal(getAutoExecutionModeLabel('PROPOSAL'), '조건 도달 시 매도 제안')
    assert.equal(getAutoTriggerLabel('TAKE_PROFIT'), '익절 도달')
    assert.equal(getAutoTriggerLabel('STOP_LOSS'), '손절 도달')
    assert.equal(getAutoTriggerLabel(''), '아직 미도달')
  })

  it('returns stock warning badge tone with fallback', () => {
    assert.match(getStockWarningBadgeTone('TRADING_SUSPENDED'), /rose/)
    assert.equal(
      getStockWarningBadgeTone('UNKNOWN_WARNING'),
      'border-slate-600 bg-slate-800/70 text-slate-200',
    )
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
node --test frontend/src/pages/assetDetailModel.test.mjs
```

Expected: FAIL with `Cannot find module` or missing export errors.

- [ ] **Step 3: Write minimal implementation**

Create `frontend/src/pages/assetDetailModel.js`:

```js
export const ACTIONABLE_ORDER_STATUSES = [
  'PENDING',
  'APPROVED',
  'ORDERED',
  'OPEN',
  'PARTIALLY_FILLED',
  'MODIFIED',
]

export const STOCK_WARNING_BADGE_META = {
  TRADING_SUSPENDED: {
    tone: 'border-rose-500/50 bg-rose-500/15 text-rose-200',
  },
  LIQUIDATION_TRADING: {
    tone: 'border-rose-500/40 bg-rose-500/12 text-rose-300',
  },
  INVESTMENT_RISK: {
    tone: 'border-orange-500/40 bg-orange-500/12 text-orange-300',
  },
  INVESTMENT_WARNING: {
    tone: 'border-amber-500/40 bg-amber-500/12 text-amber-300',
  },
  OVERHEATED: {
    tone: 'border-yellow-500/40 bg-yellow-500/12 text-yellow-200',
  },
  VI_STATIC_AND_DYNAMIC: {
    tone: 'border-sky-500/40 bg-sky-500/12 text-sky-300',
  },
  VI_STATIC: {
    tone: 'border-sky-500/40 bg-sky-500/12 text-sky-300',
  },
  VI_DYNAMIC: {
    tone: 'border-sky-500/40 bg-sky-500/12 text-sky-300',
  },
  STOCK_WARRANTS: {
    tone: 'border-fuchsia-500/40 bg-fuchsia-500/12 text-fuchsia-300',
  },
}

export const normalizeStockSymbol = (value) => String(value || '').trim().toUpperCase()

export const isDomesticStockSymbol = (value) => /^\d{6}$/.test(normalizeStockSymbol(value))

export const isUsStockSymbol = (value, market = '') => {
  const normalizedMarket = String(market || '').trim().toUpperCase()
  if (['KR', 'KOSPI', 'KOSDAQ', 'KONEX', '국내'].includes(normalizedMarket)) return false
  if (['US', 'USA', 'NASDAQ', 'NYSE', 'AMEX'].includes(normalizedMarket)) return true
  return !isDomesticStockSymbol(value)
}

export const isActionableOrderStatus = (status) => (
  ACTIONABLE_ORDER_STATUSES.includes(String(status || '').toUpperCase())
)

export const isCancelReplaceExchange = (exchange) => (
  ['COINONE', 'BINANCE', 'BINANCE_UM_FUTURES'].includes(String(exchange || '').toUpperCase())
)

export const getStockWarningBadgeTone = (warningType) => (
  STOCK_WARNING_BADGE_META[String(warningType || '').toUpperCase()]?.tone
  || 'border-slate-600 bg-slate-800/70 text-slate-200'
)

export const getOrderStatusLabel = (status) => {
  const normalized = String(status || '').toUpperCase()
  if (['PENDING', 'OPEN', 'PARTIALLY_FILLED', 'MODIFIED'].includes(normalized)) return '미체결'
  if (['APPROVED', 'ORDERED'].includes(normalized)) return '접수 완료'
  if (normalized === 'EXECUTED') return '체결완료'
  if (['CANCELED', 'CANCELLED'].includes(normalized)) return '취소완료'
  if (['FAILED', 'REJECTED', 'EXPIRED'].includes(normalized)) return '실패'
  return normalized || '-'
}

export const getOrderSideLabel = (side) => (
  String(side || '').toUpperCase() === 'SELL' ? '매도' : '매수'
)

export const getAutoRuleStatusLabel = (status) => {
  const normalized = String(status || '').toUpperCase()
  if (normalized === 'RUNNING') return '감시 중'
  if (normalized === 'COMPLETED') return '완료'
  if (normalized === 'STOPPED') return '정지'
  return normalized || '-'
}

export const getAutoExecutionModeLabel = (mode) => {
  const normalized = String(mode || '').toUpperCase()
  if (normalized === 'AUTO') return '조건 도달 시 자동 매도'
  return '조건 도달 시 매도 제안'
}

export const getAutoTriggerLabel = (triggerSide) => {
  const normalized = String(triggerSide || '').toUpperCase()
  if (normalized === 'TAKE_PROFIT') return '익절 도달'
  if (normalized === 'STOP_LOSS') return '손절 도달'
  return '아직 미도달'
}
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
node --test frontend/src/pages/assetDetailModel.test.mjs
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/assetDetailModel.js frontend/src/pages/assetDetailModel.test.mjs
git commit -m "test: add asset detail model coverage"
```

---

### Task 2: AssetDetail 페이지에서 공통 모델 사용 및 dead code warning 제거

**Files:**
- Modify: `frontend/src/pages/AssetDetail.jsx`
- Modify: `frontend/src/pages/mobile/MobileAssetDetail.jsx`

**Interfaces:**
- Consumes: Task 1 exports from `frontend/src/pages/assetDetailModel.js`
- Produces: 두 상세 페이지가 기존 UI/API 동작을 유지하면서 공통 모델 함수를 import한다.

- [ ] **Step 1: Import common model in desktop page**

In `frontend/src/pages/AssetDetail.jsx`, add this import after existing local imports:

```js
import {
  getAutoExecutionModeLabel,
  getAutoRuleStatusLabel,
  getAutoTriggerLabel,
  getOrderSideLabel,
  getOrderStatusLabel,
  getStockWarningBadgeTone,
  isActionableOrderStatus,
  isCancelReplaceExchange,
  isUsStockSymbol,
  normalizeStockSymbol,
} from './assetDetailModel.js'
```

Then remove the local definitions for:

```js
const ACTIONABLE_ORDER_STATUSES = [...]
const STOCK_WARNING_BADGE_META = { ... }
const isActionableOrderStatus = ...
const isCancelReplaceExchange = ...
const getStockWarningBadgeTone = ...
const getOrderStatusLabel = ...
const getOrderSideLabel = ...
const getAutoRuleStatusLabel = ...
const getAutoExecutionModeLabel = ...
const getAutoTriggerLabel = ...
const normalizeStockSymbol = ...
const isDomesticStockSymbol = ...
const isUsStockSymbol = ...
```

- [ ] **Step 2: Import common model in mobile page**

In `frontend/src/pages/mobile/MobileAssetDetail.jsx`, add this import after existing local imports:

```js
import {
  getAutoExecutionModeLabel,
  getAutoRuleStatusLabel,
  getAutoTriggerLabel,
  getOrderSideLabel,
  getOrderStatusLabel,
  getStockWarningBadgeTone,
  isActionableOrderStatus,
  isCancelReplaceExchange,
  isUsStockSymbol,
  normalizeStockSymbol,
} from '../assetDetailModel.js'
```

Then remove the same local definitions listed in Step 1.

- [ ] **Step 3: Remove unused catch variables and empty blocks**

In `frontend/src/pages/AssetDetail.jsx`, update the three affected catch blocks around current lint lines `2026`, `2038`, and `2087`:

```js
} catch {
  return fallbackValue
}
```

or remove the empty `catch` body only when the surrounding function already returns a safe fallback after the block:

```js
} catch {
}
```

must become:

```js
} catch {
  return null
}
```

when the function expects an explicit nullable fallback. Use the existing surrounding return type; do not introduce a new UI message.

Apply the same pattern in `frontend/src/pages/mobile/MobileAssetDetail.jsx` around current lint lines `1970`, `1982`, and `2032`.

- [ ] **Step 4: Remove useless candleSeries assignment**

In both detail files, find the chart effect around current lint lines `2484` and `2430`.

Replace this pattern:

```js
let candleSeries = null
candleSeries = chart.addSeries(CandlestickSeries, options)
```

with:

```js
const candleSeries = chart.addSeries(CandlestickSeries, options)
```

If the variable is not used after assignment, call the method without binding:

```js
chart.addSeries(CandlestickSeries, options)
```

Do not remove cleanup code for the chart instance.

- [ ] **Step 5: Run targeted lint**

Run:

```bash
cd frontend && npx eslint src/pages/AssetDetail.jsx src/pages/mobile/MobileAssetDetail.jsx src/pages/assetDetailModel.js src/pages/assetDetailModel.test.mjs
```

Expected: `no-unused-vars`, `no-empty`, and `no-useless-assignment` warnings are gone from the two detail files. Remaining `react-hooks/exhaustive-deps` warnings may remain if fixing them risks lifecycle changes.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/AssetDetail.jsx frontend/src/pages/mobile/MobileAssetDetail.jsx
git commit -m "refactor: share asset detail model helpers"
```

---

### Task 3: Document results and run full verification

**Files:**
- Modify: `project_structure.md`
- Optional Modify: `README.md`
- Optional Modify: `chatbot_qa_checklist_2026-07-14.md`

**Interfaces:**
- Consumes: Task 1 and Task 2 final file layout and lint counts.
- Produces: Documentation that reflects new `assetDetailModel` files and current lint warning count.

- [ ] **Step 1: Update project structure**

In `project_structure.md`, add the new files under the frontend pages section:

```md
- `frontend/src/pages/assetDetailModel.js` - AssetDetail/MobileAssetDetail 공통 상태 라벨, 심볼 판별, 경고 배지 tone 순수 유틸
- `frontend/src/pages/assetDetailModel.test.mjs` - assetDetailModel 순수 함수 Node test
```

- [ ] **Step 2: Capture current lint summary**

Run:

```bash
cd frontend
npx eslint . --format json > /tmp/teamproject-eslint-after-asset-detail.json
node -e 'const fs=require("fs"); const data=JSON.parse(fs.readFileSync("/tmp/teamproject-eslint-after-asset-detail.json","utf8")); const warnings=data.reduce((sum,file)=>sum+file.warningCount,0); const errors=data.reduce((sum,file)=>sum+file.errorCount,0); console.log(JSON.stringify({errors,warnings}, null, 2));'
```

Expected: `errors` is `0`, `warnings` is less than the previous baseline `122`.

- [ ] **Step 3: Update docs with actual result**

If warning count changed, add a short result note to the existing QA/checklist or README section that already tracks lint verification. Write the actual warning number printed in Step 2 in the final sentence:

```md
- 2026-07-15 AssetDetail 1차 리팩토링: 공통 순수 유틸을 `assetDetailModel.js`로 분리하고 명확한 dead code warning을 제거했다. 전체 lint 상태는 `0 errors`, 실제 측정된 warning 수이다.
```

- [ ] **Step 4: Run full verification**

Run:

```bash
node --test frontend/src/pages/assetDetailModel.test.mjs
npm run lint
npm run build
python3 -m pytest -q
```

Expected:

- `node --test`: PASS
- `npm run lint`: exit code 0
- `npm run build`: exit code 0
- `python3 -m pytest -q`: PASS

- [ ] **Step 5: Commit docs and verification result**

```bash
git add project_structure.md README.md chatbot_qa_checklist_2026-07-14.md
git commit -m "docs: record asset detail refactor status"
```

Only add `README.md` or `chatbot_qa_checklist_2026-07-14.md` if they were actually modified.

---

## Self-Review

- Spec coverage: The plan covers common helper extraction, tests, dead code lint cleanup, verification, and documentation.
- Placeholder scan: No `TBD`, `TODO`, or future-work placeholders remain in implementation steps.
- Type consistency: Export names in Task 1 match imports in Task 2.
- Scope check: Backend route splitting, dashboard refactor, and hook dependency lifecycle rewrites are intentionally outside this first cycle unless a safe local fix is obvious during Task 2.
