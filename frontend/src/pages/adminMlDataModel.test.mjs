import assert from 'node:assert/strict'
import test from 'node:test'

import {
  buildQualityDetail,
  findRegistryRow,
  formatMetric,
  formatPath,
  formatPercent,
  formatReturnPercent,
  formatSignedDelta,
  formatStaleness,
  formatTime,
  formatTrustValue,
  formatVersionBacktest,
  getHealthLabel,
  getHealthTone,
  getSignalGradeLabel,
  getSimpleGuardStatus,
  getVersionSnapshot,
  operationalAutomationPresets,
  presets,
  summarizeFailedChecks,
  v8TuningPresets,
} from './adminMlDataModel.js'

test('ML 관리자 표시 포맷을 안정적으로 변환한다', () => {
  assert.equal(formatMetric(0.812345), '0.8123')
  assert.equal(formatPercent(0.1234), '12.3%')
  assert.equal(formatReturnPercent(-0.01234), '-1.23%')
  assert.equal(formatSignedDelta(0.012345), '+0.0123')
  assert.equal(formatSignedDelta(-0.0312, 'return'), '-3.12%')
  assert.equal(formatStaleness(90), '1시간 전')
  assert.equal(formatTime('2026-07-15T11:22:33Z'), '07-15 20:22:33')
})

test('프로젝트 경로와 백테스트 값을 화면용으로 요약한다', () => {
  assert.equal(
    formatPath('/Users/kangheesung/10-19_개발/13_프로젝트/13.05_트레이딩/teamproject/ml/data/report.json'),
    './ml/data/report.json',
  )
  assert.equal(
    formatVersionBacktest({
      backtests: { composite: { data: { excess_return: 0.042 } } },
    }, 'excess_return_net'),
    '4.20%',
  )
})

test('승격 검증과 레지스트리 행을 요약한다', () => {
  const guardReport = {
    passed: false,
    failed_checks: [
      { name: 'cv_roc_auc', actual: 0.51, comparator: '>=', threshold: 0.55 },
    ],
  }

  assert.deepEqual(getSimpleGuardStatus(guardReport), {
    label: '기준 미달',
    tone: 'border-amber-500/40 bg-amber-950/20 text-amber-300',
  })
  assert.deepEqual(summarizeFailedChecks(guardReport), ['시계열 CV 구분력: 0.5100 >= 0.5500'])
  assert.equal(
    findRegistryRow({ stock: [{ model_version: 'v11' }], crypto: [] }, 'STOCK', 'v11')?.model_version,
    'v11',
  )
})

test('운영 신뢰도와 품질 상세를 순수 데이터로 계산한다', () => {
  assert.equal(getHealthLabel('healthy'), '정상')
  assert.match(getHealthTone('missing'), /red/)
  assert.equal(getSignalGradeLabel('STRONG_BUY_CANDIDATE'), '강한 후보')
  assert.equal(formatTrustValue({ name: 'composite_excess_return_net', actual: 0.021 }), '2.10%')
  assert.equal(getVersionSnapshot({
    metrics: { time_series_cv_average: { roc_auc: 0.61, precision_at_top_10pct: 0.7 } },
    risk_metrics: { roc_auc: 0.58 },
    backtests: { composite: { data: { excess_return_net: 0.032 } } },
  }).compositeExcessReturnNet, 0.032)

  const detail = buildQualityDetail({
    rows: 120,
    path: 'ml/data/raw.csv',
    quality: {
      status: 'healthy',
      unique_symbol_count: 10,
      duplicate_symbol_date_count: 0,
      missing_required_value_count: 1,
      invalid_price_row_count: 2,
      invalid_volume_row_count: 3,
      staleness_hours: 4,
      issues: [],
    },
  })

  assert.match(detail, /120 rows/)
  assert.match(detail, /status: 정상/)
})

test('관리자 ML 프리셋 파생 목록을 제공한다', () => {
  assert.equal(presets.stock.exchange, 'TOSS')
  assert.deepEqual(operationalAutomationPresets.map((preset) => preset.key), [
    'stock-v8-full',
    'crypto-v8-full',
    'kr-stock-v1-full',
    'us-stock-v1-full',
  ])
  assert.deepEqual(v8TuningPresets.map((preset) => preset.key), ['stock-v8-tune', 'crypto-v8-tune'])
})
