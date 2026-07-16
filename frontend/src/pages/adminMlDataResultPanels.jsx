import { useMemo, useState } from 'react'
import {
  formatMetric,
  formatPercent,
  formatReturnPercent,
} from './adminMlDataModel.js'
import { VersionDeltaPanel } from './adminMlDataCorePanels.jsx'
import { VersionComparisonTable } from './adminMlDataOperationalPanels.jsx'

export function ModelResultCard({ title, result }) {
  const versions = useMemo(() => result?.versions || [], [result?.versions])
  const defaultSelectedVersion = result?.serving_version || result?.recommended_version || result?.selected_version || ''
  const [selectedVersion, setSelectedVersion] = useState(defaultSelectedVersion)
  const resolvedSelectedVersion = versions.some((item) => item.version === selectedVersion)
    ? selectedVersion
    : defaultSelectedVersion

  const activeResult = useMemo(() => {
    if (!versions.length) return result
    return versions.find((item) => item.version === resolvedSelectedVersion) || result
  }, [result, resolvedSelectedVersion, versions])

  const metrics = activeResult?.metrics
  const riskMetrics = activeResult?.risk_metrics
  const predictions = activeResult?.predictions || []
  const upOnlyBacktest = activeResult?.backtests?.up_only?.data
  const compositeBacktest = activeResult?.backtests?.composite?.data
  const comparisonBaselines = useMemo(() => {
    const candidates = [
      { label: '서비스 반영 기준', version: result?.serving_version },
      { label: '추천 기준', version: result?.recommended_version },
      { label: '최신 기준', version: result?.latest_version },
    ]

    return candidates
      .filter((candidate, index, array) => candidate.version && array.findIndex((item) => item.version === candidate.version) === index)
      .map((candidate) => ({
        ...candidate,
        ...versions.find((item) => item.version === candidate.version),
      }))
      .filter((candidate) => candidate.version)
  }, [result?.latest_version, result?.recommended_version, result?.serving_version, versions])

  const renderProgressBar = (value, minVal = 0.5, maxVal = 0.65) => {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return null
    const num = Number(value)
    const percent = Math.max(0, Math.min(100, ((num - minVal) / (maxVal - minVal)) * 100))
    
    let colorClass = 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]'
    if (num >= 0.55) {
      colorClass = 'bg-ai-cyan shadow-[0_0_8px_rgba(0,243,255,0.5)]'
    } else if (num >= 0.51) {
      colorClass = 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.5)]'
    }

    return (
      <div className="mt-2 h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
        <div 
          className={`h-full rounded-full transition-all duration-500 ${colorClass}`}
          style={{ width: `${percent}%` }}
        />
      </div>
    )
  }

  const renderMetricValue = (val, isPercent = false, isReturn = false) => {
    if (val === null || val === undefined || Number.isNaN(Number(val))) {
      return <span className="font-mono text-slate-500">-</span>
    }
    const num = Number(val)
    const text = isPercent ? formatPercent(num) : (isReturn ? formatReturnPercent(num) : formatMetric(num))
    
    if (num > 0) {
      return <span className="font-mono text-emerald-400 font-bold">+{text}</span>
    } else if (num < 0) {
      return <span className="font-mono text-rose-500 font-bold">{text}</span>
    }
    return <span className="font-mono text-slate-300">{text}</span>
  }

  return (
    <article className="rounded-lg border border-slate-700/80 bg-slate-surface p-5">
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-ai-cyan">{activeResult?.asset_type || result?.asset_type || '-'}</p>
          <h3 className="mt-1 text-sm font-bold uppercase tracking-wider text-white">{title}</h3>
        </div>
        <span className={`w-fit rounded border px-2 py-1 text-[10px] font-bold ${
          activeResult?.updated ? 'border-emerald-500/40 text-emerald-300' : 'border-slate-700 text-slate-500'
        }`}>
          {activeResult?.updated ? 'READY' : 'NO DATA'}
        </span>
      </div>

      <div className="mb-4 flex flex-wrap gap-2">
        <span className="rounded border border-fuchsia-500/30 px-2 py-1 text-[10px] font-bold text-fuchsia-300">
          SERVING {result?.serving_version || '-'}
        </span>
        <span className="rounded border border-emerald-500/30 px-2 py-1 text-[10px] font-bold text-emerald-300">
          PICK {result?.recommended_version || '-'}
        </span>
        <span className="rounded border border-slate-600 px-2 py-1 text-[10px] font-bold text-slate-300">
          LATEST {result?.latest_version || '-'}
        </span>
      </div>

      {metrics ? (
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-lg bg-[#0f172a] p-3 border border-slate-800 hover:border-slate-700 transition">
            <p className="text-xs font-bold text-slate-400">구분력 (ROC-AUC)</p>
            <p className="mt-0.5 text-[10px] leading-4 text-slate-500 font-sans">상승/비상승을 가르는 전체 힘</p>
            <p className="mt-1 font-mono text-xl font-bold text-white">{formatMetric(metrics.roc_auc)}</p>
            {renderProgressBar(metrics.roc_auc, 0.5, 0.65)}
          </div>
          <div className="rounded-lg bg-[#0f172a] p-3 border border-slate-800 hover:border-slate-700 transition">
            <p className="text-xs font-bold text-slate-400">시계열 CV 구분력</p>
            <p className="mt-0.5 text-[10px] leading-4 text-slate-500 font-sans">기간 분할 검증 평균 구분력</p>
            <p className="mt-1 font-mono text-xl font-bold text-white">{formatMetric(metrics.time_series_cv_average?.roc_auc || metrics.roc_auc)}</p>
            {renderProgressBar(metrics.time_series_cv_average?.roc_auc || metrics.roc_auc, 0.5, 0.65)}
          </div>
          <div className="rounded-lg bg-[#0f172a] p-3 border border-slate-800 hover:border-slate-700 transition">
            <p className="text-xs font-bold text-slate-400">상위 10% 적중</p>
            <p className="mt-0.5 text-[10px] leading-4 text-slate-500 font-sans">점수 상위 후보의 실제 상승 비율</p>
            <p className="mt-1 font-mono text-xl font-bold text-white">{formatMetric(metrics.time_series_cv_average?.precision_at_top_10pct || metrics.precision_at_top_10pct)}</p>
            {renderProgressBar(metrics.time_series_cv_average?.precision_at_top_10pct || metrics.precision_at_top_10pct, 0.1, 0.3)}
          </div>
          <div className="rounded-lg bg-[#0f172a] p-3 border border-slate-800 hover:border-slate-700 transition">
            <p className="text-xs font-bold text-slate-400">상승 적중도 (AP)</p>
            <p className="mt-0.5 text-[10px] leading-4 text-slate-500 font-sans font-sans">상승 후보 쪽 랭킹 신뢰도</p>
            <p className="mt-1 font-mono text-xl font-bold text-white">{formatMetric(metrics.average_precision)}</p>
          </div>
          <div className="rounded-lg bg-[#0f172a] p-3 border border-slate-800 hover:border-slate-700 transition">
            <p className="text-xs font-bold text-slate-400">Precision / Recall</p>
            <p className="mt-0.5 text-[10px] leading-4 text-slate-500 font-sans">예측 정확도 / 탐지 커버리지</p>
            <p className="mt-1 font-mono text-sm font-bold text-white">
              {formatMetric(metrics.precision)} / {formatMetric(metrics.recall)}
            </p>
          </div>
          <div className="rounded-lg bg-[#0f172a] p-3 border border-slate-800 hover:border-slate-700 transition">
            <p className="text-xs font-bold text-slate-400">전체 정답률</p>
            <p className="mt-0.5 text-[10px] leading-4 text-slate-500 font-sans">전체 0/1 매칭 비율</p>
            <p className="mt-1 font-mono text-xl font-bold text-white">{formatMetric(metrics.accuracy)}</p>
          </div>
          <div className="rounded-lg bg-[#0f172a] p-3 sm:col-span-3 border border-slate-800 font-sans">
            <p className="text-xs text-slate-500">학습/검증 구간</p>
            <p className="mt-1 break-words font-mono text-xs leading-5 text-slate-300">
              train {metrics.train_rows} rows: {metrics.train_start_date} ~ {metrics.train_end_date}
            </p>
            <p className="break-words font-mono text-xs leading-5 text-slate-300">
              valid {metrics.valid_rows} rows: {metrics.valid_start_date} ~ {metrics.valid_end_date}
            </p>
          </div>
        </div>
      ) : (
        <div className="rounded-lg border border-slate-800 bg-[#0f172a] p-4 text-sm text-slate-400 font-sans">
          아직 학습 결과 파일이 없습니다.
        </div>
      )}

      <div className="mt-5 grid gap-4 xl:grid-cols-2">
        <div className="rounded-lg border border-slate-800 bg-[#0f172a] p-4">
          <p className="text-xs font-bold uppercase tracking-wider text-slate-400">하락 위험 모델</p>
          {riskMetrics ? (
            <div className="mt-3 grid gap-2 sm:grid-cols-3">
              <div>
                <p className="text-[10px] text-slate-500 font-sans">구분력 (ROC-AUC)</p>
                <p className="font-mono text-sm text-white">{formatMetric(riskMetrics.roc_auc)}</p>
                {renderProgressBar(riskMetrics.roc_auc, 0.5, 0.65)}
              </div>
              <div>
                <p className="text-[10px] text-slate-500 font-sans">상위후보 적중도</p>
                <p className="font-mono text-sm text-white">{formatMetric(riskMetrics.average_precision)}</p>
              </div>
              <div>
                <p className="text-[10px] text-slate-500 font-sans">전체 정답률</p>
                <p className="font-mono text-sm text-white">{formatMetric(riskMetrics.accuracy)}</p>
              </div>
            </div>
          ) : (
            <p className="mt-3 text-sm text-slate-400 font-sans">아직 risk_label 모델 결과가 없습니다.</p>
          )}
        </div>

        <div className="rounded-lg border border-slate-800 bg-[#0f172a] p-4">
          <p className="text-xs font-bold uppercase tracking-wider text-slate-400">백테스트 요약</p>
          <div className="mt-3 grid gap-3">
            <div className="rounded-lg border border-slate-800 bg-black/10 p-3 font-sans">
              <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">상승 점수 기준</p>
              {upOnlyBacktest ? (
                <div className="mt-2 grid gap-1 text-xs text-slate-300">
                  <p>상위 {upOnlyBacktest.top_n}개 평균 수익률: {renderMetricValue(upOnlyBacktest.top_avg_future_return, false, true)}</p>
                  <p>비용 반영 평균 수익률: {renderMetricValue(upOnlyBacktest.top_avg_future_return_net, false, true)}</p>
                  <p>전체 평균 수익률: {renderMetricValue(upOnlyBacktest.universe_avg_future_return, false, true)}</p>
                  <p>순 초과 수익률: {renderMetricValue(upOnlyBacktest.excess_return_net ?? upOnlyBacktest.excess_return, false, true)}</p>
                  <p>후보 승률: <span className="font-mono text-white">{formatPercent(upOnlyBacktest.selection_win_rate_net ?? upOnlyBacktest.selection_win_rate)}</span></p>
                </div>
              ) : (
                <p className="mt-2 text-sm text-slate-400">아직 단순 백테스트 결과가 없습니다.</p>
              )}
            </div>

            <div className="rounded-lg border border-slate-800 bg-black/10 p-3 font-sans">
              <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">복합 점수 기준</p>
              {compositeBacktest ? (
                <div className="mt-2 grid gap-1 text-xs text-slate-300">
                  <p>상위 {compositeBacktest.top_n}개 평균 수익률: {renderMetricValue(compositeBacktest.top_avg_future_return, false, true)}</p>
                  <p>비용 반영 평균 수익률: {renderMetricValue(compositeBacktest.top_avg_future_return_net, false, true)}</p>
                  <p>전체 평균 수익률: {renderMetricValue(compositeBacktest.universe_avg_future_return, false, true)}</p>
                  <p>순 초과 수익률: {renderMetricValue(compositeBacktest.excess_return_net ?? compositeBacktest.excess_return, false, true)}</p>
                  <p>후보 승률: <span className="font-mono text-white">{formatPercent(compositeBacktest.selection_win_rate_net ?? compositeBacktest.selection_win_rate)}</span></p>
                  <p>최대 낙폭: <span className="font-mono text-rose-450 font-bold">{formatReturnPercent(compositeBacktest.max_drawdown_net)}</span></p>
                </div>
              ) : (
                <p className="mt-2 text-sm text-slate-400">아직 복합 백테스트 결과가 없습니다.</p>
              )}
            </div>
          </div>
        </div>
      </div>

      <VersionComparisonTable
        versions={versions}
        selectedVersion={resolvedSelectedVersion}
        recommendedVersion={result?.recommended_version}
        latestVersion={result?.latest_version}
        servingVersion={result?.serving_version}
        onSelectVersion={setSelectedVersion}
      />

      <VersionDeltaPanel activeVersion={activeResult} baselines={comparisonBaselines} />

      <div className="mt-5">
        <h4 className="mb-3 text-xs font-bold uppercase tracking-wider text-slate-400">예측 순위</h4>
        {predictions.length ? (
          <div className="grid gap-2">
            {predictions.slice(0, 10).map((row) => (
              <div
                key={`${row.model_version}-${row.symbol}`}
                className="grid gap-3 rounded-lg border border-slate-800 bg-[#0f172a] p-3 sm:grid-cols-[1fr_auto_auto_auto]"
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="break-words text-sm font-bold text-white">{row.display_name || row.symbol}</p>
                    {row.position ? (
                      <span className={`rounded px-1.5 py-0.5 text-[9px] font-black tracking-widest ${
                        row.position === 'SHORT'
                          ? 'bg-rose-950/80 text-rose-300 border border-rose-700/60'
                          : 'bg-emerald-950/80 text-emerald-300 border border-emerald-700/60'
                      }`}>
                        {row.position}
                      </span>
                    ) : null}
                  </div>
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    <span className="rounded border border-slate-700 px-1.5 py-0.5 font-mono text-[10px] text-slate-400">
                      {row.symbol}
                    </span>
                    {row.market ? (
                      <span className="rounded border border-slate-700 px-1.5 py-0.5 text-[10px] text-slate-400">
                        {row.market}
                      </span>
                    ) : null}
                    {row.sector ? (
                      <span className="rounded border border-ai-cyan/30 px-1.5 py-0.5 text-[10px] text-ai-cyan">
                        {row.sector}
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-1 break-words text-xs text-slate-500">{row.date}</p>
                </div>
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">상승 확률</p>
                  <p className="font-mono text-sm text-emerald-300">{formatPercent(row.up_probability)}</p>
                </div>
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">하락 위험</p>
                  <p className="font-mono text-sm text-amber-300">{formatPercent(row.risk_probability)}</p>
                </div>
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">복합 점수</p>
                  <p className="font-mono text-sm text-ai-cyan">{row.signal_score}</p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded-lg border border-slate-800 bg-[#0f172a] p-4 text-sm text-slate-400">
            아직 예측 CSV가 없습니다.
          </div>
        )}
      </div>
    </article>
  )
}
