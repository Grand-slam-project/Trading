# Dashboard Lint Refactor Design

## 목적

`Dashboard.jsx`와 `MobileDashboardPage.jsx`는 각각 약 2천 줄이며, 현재 각 12개 lint warning이 남아 있다. 두 파일은 상단의 통화 포맷, 자산 평가, 관심종목 가격 조회, 보유자산 병합, 이체 반영 로직이 거의 동일하다. 이번 리팩토링의 목적은 UI와 API 동작을 바꾸지 않고 공통 순수 로직을 분리해 중복을 줄이고, 명확한 dead code warning을 제거하는 것이다.

## 현재 기준

- 전체 lint 상태: `0 errors`, `109 warnings`
- 최우선 대상:
  - `frontend/src/pages/Dashboard.jsx`: 1926줄, 12 warnings
  - `frontend/src/pages/mobile/MobileDashboardPage.jsx`: 2039줄, 12 warnings
- 두 파일의 warning 구성:
  - `no-unused-vars`: 각 6개
  - `react-hooks/set-state-in-effect`: 각 3개
  - `react-hooks/exhaustive-deps`: 각 2개
  - `react-hooks/immutability`: 각 1개

## 범위

이번 사이클은 Dashboard 계열에 한정한다.

- 공통 순수 함수와 상수를 `frontend/src/pages/dashboardModel.js`로 추출한다.
- `Dashboard.jsx`와 `MobileDashboardPage.jsx`에서 동일한 계산/포맷/병합 로직을 import하도록 전환한다.
- `no-unused-vars`는 기능 영향이 없는 항목부터 제거한다.
- `react-hooks/immutability`의 `loadDashboardWatchlist` 선언 전 접근 warning은 함수 선언 순서나 안정적인 callback 구조로 안전하게 해소한다.
- `react-hooks/exhaustive-deps`와 `set-state-in-effect`는 네트워크 재호출/렌더 루프 가능성을 확인하며 처리한다. 단순 dependency 추가가 API 호출 루프를 만들 수 있으면 이번 사이클에서는 남기고 후속 작업으로 문서화한다.

## 제외 범위

- 대시보드 UI 레이아웃 변경은 하지 않는다.
- 자산 병합 정책, 모의계좌 포함 토글 정책, Supabase 쿼리 조건, API endpoint 계약은 변경하지 않는다.
- `AssetsTab.jsx`, `WatchlistTab.jsx`, `MobileWatchlistTab.jsx`는 이번 범위에 포함하지 않는다.
- lint 규칙을 더 낮추거나 disable 주석을 추가해 warning을 숨기지 않는다.

## 설계

### 공통 모델 파일

`frontend/src/pages/dashboardModel.js`를 추가한다.

이 파일은 React state, router, DOM에 의존하지 않는 순수 함수와 상수만 가진다. Supabase 직접 호출 함수는 1차에서는 페이지에 남기고, 순수 계산 함수만 먼저 옮긴다.

초기 추출 후보:

- `BALANCE_EXCHANGE_ORDER`
- `TRADE_PROPOSAL_HOLDING_FIELDS`
- `TRANSFER_PROPOSAL_FIELDS`
- `DASHBOARD_TAB_SET`
- `normalizeDashboardTab(tab)`
- `toNumber(value)`
- `formatCurrency(value, currency, displayCurrency, exchangeRate)`
- `formatUnitCurrency(value, currency, displayCurrency, exchangeRate)`
- `formatNullableCurrency(value, currency, displayCurrency, exchangeRate)`
- `normalizeSummaryCurrency(currency, source)`
- `formatSummaryCurrency(value, currency)`
- `getSummarySourceLabel(source)`
- `createCurrencySourceMap()`
- `addCurrencySourceAmount(sourceMap, currency, source, amount)`
- `flattenCurrencySourceMap(sourceMap)`
- `fillSummaryDetailEntries(entries, currency)`
- `formatNativeCurrency(value, currency)`
- `getAccountDisplayLabel(item)`
- `getAccountTone(exchange)`
- `buildCashEntriesFromItem(item)`
- `parsePriceNumber(value)`
- `getWatchlistCurrentPrice(item)`
- `getDashboardWatchlistAssetType(item)`
- `getDashboardWatchlistCurrency(item)`
- `getDashboardWatchlistChartConfig(item)`
- `formatSignedRate(value)`
- `formatAllocationPercent(item)`
- `getHoldingMarketType(holding)`
- `getHoldingEvaluationKrw(holding, exchangeRate)`
- `getHoldingEvaluationNative(holding)`
- `getHoldingsTotalNative(holdings)`
- `getHoldingProfitBasis(holding)`
- `getAccountExchangeCode(account)`
- `isCryptoAccount(account)`
- `toKrwAmount(value, currency, exchangeRate)`
- `toPositiveKrwAmount(value, currency, exchangeRate)`
- `getAccountCashKrw(account, exchangeRate)`
- `getPortfolioProfitRate(accountBalance)`
- `mergeAccountBalances(items, showMockAssets)`
- `getHoldingIdentity(holding)`
- `normalizeExchangeText(exchangeText)`
- `getHoldingAccountScope(holding)`
- `buildLiveAccountScopes(liveHoldings, liveSources)`
- `buildEstimatedHoldingsFromTrades(tradeRows, liveHoldings, showMockAssets, liveSources)`
- `mergeBalanceWithTradeEstimates(mergedBalance, tradeRows, showMockAssets)`
- `mergeBalanceWithCompletedTransfers(mergedBalance, transferRows)`
- `getBalanceRequestLabel(exchange, env)`
- `getBalanceAccountLabel(exchange, env, account)`
- `buildBalanceRequests(keyStatus)`

### 남겨둘 로직

아래 로직은 비동기/외부 의존성이 있어 이번 1차 추출에서는 페이지에 남긴다.

- `fetchDashboardWatchlistCurrentPrice`
- `fetchTradeSymbolNameMap`
- `fetchTransferRowsFromSupabase`
- `loadAccountBalance`
- `loadDashboardWatchlist`
- Supabase session, auth header, router, state setter와 직접 연결된 함수

### 테스트

`frontend/src/pages/dashboardModel.test.mjs`를 추가한다.

테스트는 다음을 고정한다.

- 통화 포맷과 KRW 환산
- 국내/해외/코인 보유자산 평가액 계산
- 모의계좌 포함/제외 병합 결과
- completed transfer 차감/가산 반영
- 관심종목 자산 타입/통화/chart config 판별
- dashboard tab normalize fallback

### lint 처리

명확한 dead code는 제거한다.

- `formatKrw`
- 사용하지 않는 `encrypted`, `loading`, `message`
- 사용하지 않는 key input handler

`loadDashboardWatchlist` 선언 전 접근 warning은 기존 effect가 참조하는 함수 선언 위치를 effect보다 앞으로 이동하거나, hook dependency가 안정적으로 유지되는 구조로 정리한다.

## 검증

필수 검증 명령:

```bash
node --test frontend/src/pages/dashboardModel.test.mjs
npm run lint
npm run build
python3 -m pytest -q
```

기대 결과:

- 새 모델 테스트 통과
- lint error 0 유지
- 전체 warning 수는 109보다 감소해야 한다.
- build 성공
- backend pytest 성공

## 문서 최신화

구현 완료 후 다음 문서를 실제 결과 기준으로 갱신한다.

- `project_structure.md`: 새 `dashboardModel.js`와 테스트 파일 반영
- `README.md`: 실제 lint warning 수와 Dashboard 1차 리팩토링 결과 반영

## 후속 사이클 후보

1. Dashboard hook dependency와 `set-state-in-effect` 구조 정리
2. `WatchlistTab.jsx` / `MobileWatchlistTab.jsx` 공통화
3. `backend/routes/trade.py` 주문/조회/자동감시 라우트 분할
4. `backend/services/chatbot/tool_registry.py` 도구 카테고리별 모듈화
