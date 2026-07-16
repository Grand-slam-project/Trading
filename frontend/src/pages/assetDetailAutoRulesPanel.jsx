import {
  formatSignedPercentValue,
  getAutoExecutionModeLabel,
  getAutoRuleStatusLabel,
  getAutoTriggerLabel,
} from './assetDetailModel.js'

export default function AssetDetailAutoRulesPanel({
  className = 'rounded-xl border border-[#1f2945] bg-[#0e1529]/90 p-4 backdrop-blur-md',
  showAddRuleForm,
  myHolding,
  currentPrice,
  addRulePrice,
  setAddRulePrice,
  addRuleQty,
  setAddRuleQty,
  addRuleProfitRate,
  setAddRuleProfitRate,
  addRuleStopRate,
  setAddRuleStopRate,
  addRuleAutoRestart,
  setAddRuleAutoRestart,
  addRuleExecutionMode,
  setAddRuleExecutionMode,
  autoRulesMessage,
  autoRulesLoading,
  autoRules,
  ruleUpdating,
  editingRuleId,
  editTargetProfit,
  setEditTargetProfit,
  editStopLoss,
  setEditStopLoss,
  editQuantity,
  setEditQuantity,
  brokerEnv,
  resolvedAssetType,
  oppositeCurrentPrice,
  formatUnitPrice,
  getCurrencySign,
  getCurrencyDigits,
  onToggleAddRuleForm,
  onCloseAddRuleForm,
  onRefreshAutoRules,
  onAddRule,
  onStartEditRule,
  onCloseEditRule,
  onUpdateRule,
  onStopRule,
}) {
  return (
    <div className={className}>
      <div className="mb-3 flex flex-col gap-3 border-b border-[#1f2945] pb-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-3 rounded-full bg-emerald-300" />
            <span className="text-xs font-bold text-white">조건감시 상태</span>
          </div>
          <p className="mt-1 text-[10px] text-slate-500">
            익절/손절 감시 규칙은 백그라운드 워커가 조건 도달 여부를 확인합니다.
            트리거는 조건이 실제로 발동된 사유입니다.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => {
              setAddRulePrice(myHolding && myHolding.avg_price ? String(myHolding.avg_price) : String(currentPrice || ''))
              setAddRuleQty(myHolding ? String(myHolding.qty || '') : '')
              onToggleAddRuleForm(!showAddRuleForm)
            }}
            className="rounded bg-cyan-500 px-3 py-2 text-[10px] font-black text-[#070b19] transition hover:bg-cyan-400 cursor-pointer"
          >
            {showAddRuleForm ? '등록 닫기' : '새로운 감시 등록'}
          </button>
          <button
            type="button"
            onClick={onRefreshAutoRules}
            disabled={autoRulesLoading}
            className="rounded border border-emerald-500/30 px-3 py-2 text-[10px] font-black text-emerald-300 transition hover:bg-emerald-950/30 disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer"
          >
            {autoRulesLoading ? '조회 중' : '감시 새로고침'}
          </button>
        </div>
      </div>

      {showAddRuleForm && (
        <div className="mb-4 rounded-lg border border-[#1f2945] bg-[#070b19] p-3 text-xs">
          <p className="mb-2 text-[10px] font-bold text-cyan-300">주문 없이 독립적으로 감시 규칙을 등록합니다. (보유 중인 자산에만 권장)</p>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <div>
              <label className="block text-[9px] text-slate-500 mb-1 font-bold">진입 가격 ({getCurrencySign()})</label>
              <input
                type="number"
                value={addRulePrice}
                onChange={(event) => setAddRulePrice(event.target.value)}
                className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-white focus:border-cyan-400 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-[9px] text-slate-500 mb-1 font-bold">감시 수량</label>
              <input
                type="number"
                step="0.0001"
                value={addRuleQty}
                onChange={(event) => setAddRuleQty(event.target.value)}
                className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-white focus:border-cyan-400 focus:outline-none"
                placeholder="예: 2"
              />
            </div>
            <div>
              <label className="block text-[9px] text-green-400 mb-1 font-bold">목표 익절 (%)</label>
              <input
                type="number"
                step="0.1"
                value={addRuleProfitRate}
                onChange={(event) => setAddRuleProfitRate(event.target.value)}
                className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-white focus:border-cyan-400 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-[9px] text-red-400 mb-1 font-bold">손실 제한 (%)</label>
              <input
                type="number"
                step="0.1"
                value={addRuleStopRate}
                onChange={(event) => setAddRuleStopRate(event.target.value)}
                className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-white focus:border-cyan-400 focus:outline-none"
              />
            </div>
          </div>

          <div className="mt-2.5 flex items-center gap-2 select-none cursor-pointer">
            <input
              type="checkbox"
              id="rule-auto-restart"
              checked={addRuleAutoRestart}
              onChange={(event) => setAddRuleAutoRestart(event.target.checked)}
              className="accent-cyan-400 rounded"
            />
            <label htmlFor="rule-auto-restart" className="text-[10px] text-slate-400 font-bold cursor-pointer">
              부분 체결 시 남은 수량 자동 재감시
            </label>
          </div>

          <div className="mt-3 flex flex-wrap gap-2.5 items-center justify-between border-t border-[#1f2945]/40 pt-2.5">
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setAddRuleExecutionMode('PROPOSAL')}
                className={`rounded px-2.5 py-1 text-[10px] font-bold border transition cursor-pointer ${
                  addRuleExecutionMode === 'PROPOSAL'
                    ? 'border-cyan-400 bg-cyan-950/20 text-cyan-300'
                    : 'border-slate-800 text-slate-500 hover:text-slate-400'
                }`}
              >
                매도 제안만 생성
              </button>
              <button
                type="button"
                onClick={() => setAddRuleExecutionMode('AUTO')}
                className={`rounded px-2.5 py-1 text-[10px] font-bold border transition cursor-pointer ${
                  addRuleExecutionMode === 'AUTO'
                    ? 'border-rose-400 bg-rose-950/20 text-rose-300'
                    : 'border-slate-800 text-slate-500 hover:text-slate-400'
                }`}
              >
                조건 도달 시 자동 매도
              </button>
            </div>

            <div className="flex gap-2">
              <button
                type="button"
                onClick={onCloseAddRuleForm}
                className="rounded border border-slate-700 px-3 py-1 text-[10px] text-slate-300 hover:bg-slate-800 transition cursor-pointer"
              >
                취소
              </button>
              <button
                type="button"
                disabled={ruleUpdating}
                onClick={onAddRule}
                className="rounded bg-cyan-500 px-3 py-1 text-[10px] font-black text-[#070b19] hover:bg-cyan-400 transition disabled:opacity-50 cursor-pointer"
              >
                {ruleUpdating ? '등록 중...' : '감시 등록'}
              </button>
            </div>
          </div>
        </div>
      )}

      {autoRulesMessage ? (
        <div className="mb-3 rounded border border-amber-900/60 bg-amber-950/20 px-3 py-2 text-[11px] leading-5 text-amber-300">
          {autoRulesMessage}
        </div>
      ) : null}

      {autoRulesLoading ? (
        <div className="rounded border border-[#1f2945] bg-[#070b19] px-3 py-6 text-center text-[11px] font-mono text-emerald-300">
          조건감시 규칙을 확인하는 중...
        </div>
      ) : autoRules.length > 0 ? (
        <div className="flex flex-col gap-2">
          {autoRules.map((rule) => {
            const entryPrice = Number(rule.entry_price || 0)
            const targetRate = Number(rule.target_profit_rate || 0)
            const rawStopRate = Number(rule.stop_loss_rate || 0)
            const stopRate = rawStopRate > 0 ? -Math.abs(rawStopRate) : rawStopRate
            const targetPrice = entryPrice > 0 ? entryPrice * (1 + targetRate / 100) : 0
            const stopPrice = entryPrice > 0 ? entryPrice * (1 + stopRate / 100) : 0
            const isRunning = String(rule.status || '').toUpperCase() === 'RUNNING'
            const ruleEnv = rule.broker_env || brokerEnv
            const activePrice = ruleEnv === brokerEnv ? currentPrice : (oppositeCurrentPrice || currentPrice)

            const currentReturnRate = entryPrice > 0 && activePrice > 0
              ? ((Number(activePrice) - entryPrice) / entryPrice) * 100
              : null
            const currentReturnClass = currentReturnRate === null
              ? 'text-slate-300'
              : currentReturnRate >= 0
                ? 'text-rose-300'
                : 'text-blue-300'

            return (
              <div key={rule.id} className="rounded-lg border border-[#1f2945] bg-[#070b19]/90 p-3">
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`rounded px-2 py-1 text-[10px] font-black ${
                      isRunning
                        ? 'bg-emerald-500/15 text-emerald-300'
                        : 'bg-slate-700/50 text-slate-300'
                    }`}>
                      {getAutoRuleStatusLabel(rule.status)}
                    </span>
                    <span className="font-mono text-[10px] text-slate-500">
                      {rule.exchange} · {rule.broker_env || brokerEnv} · {rule.asset_type || resolvedAssetType}
                    </span>
                    <span className={`rounded px-2 py-1 text-[10px] font-black ${
                      String(rule.execution_mode || '').toUpperCase() === 'AUTO'
                        ? 'bg-rose-500/15 text-rose-300'
                        : 'bg-cyan-500/15 text-cyan-300'
                    }`}>
                      {getAutoExecutionModeLabel(rule.execution_mode)}
                    </span>
                  </div>
                  <span className="font-mono text-[10px] text-slate-500">
                    {rule.created_at ? new Date(rule.created_at).toLocaleString('ko-KR') : '-'}
                  </span>
                </div>
                {editingRuleId === rule.id ? (
                  <div className="mt-1 rounded border border-slate-700 bg-slate-900/40 p-2.5">
                    <div className="grid grid-cols-3 gap-2.5 text-xs">
                      <div>
                        <label className="block text-[9px] text-slate-500 mb-1 font-bold">익절 비율 (%)</label>
                        <input
                          type="number"
                          step="0.01"
                          value={editTargetProfit}
                          onChange={(event) => setEditTargetProfit(event.target.value)}
                          className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-white focus:border-cyan-400 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-[9px] text-slate-500 mb-1 font-bold">손절 비율 (%)</label>
                        <input
                          type="number"
                          step="0.01"
                          value={editStopLoss}
                          onChange={(event) => setEditStopLoss(event.target.value)}
                          className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-white focus:border-cyan-400 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-[9px] text-slate-500 mb-1 font-bold">수량</label>
                        <input
                          type="number"
                          step="0.0001"
                          value={editQuantity}
                          onChange={(event) => setEditQuantity(event.target.value)}
                          className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-white focus:border-cyan-400 focus:outline-none"
                          placeholder="미입력 시 전량"
                        />
                      </div>
                    </div>
                    <div className="mt-3 flex justify-end gap-2 text-[10px]">
                      <button
                        type="button"
                        onClick={onCloseEditRule}
                        className="rounded border border-slate-700 px-2.5 py-1 text-slate-300 hover:bg-slate-800 transition cursor-pointer"
                      >
                        취소
                      </button>
                      <button
                        type="button"
                        disabled={ruleUpdating}
                        onClick={() => onUpdateRule(rule.id)}
                        className="rounded bg-emerald-500 px-2.5 py-1 font-black text-slate-950 hover:bg-emerald-400 disabled:opacity-50 transition cursor-pointer"
                      >
                        {ruleUpdating ? '저장 중...' : '저장'}
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="grid grid-cols-2 gap-2 text-[11px] sm:grid-cols-4">
                      <div>
                        <p className="text-slate-500">진입가</p>
                        <p className="font-mono font-bold text-white">{entryPrice > 0 ? formatUnitPrice(entryPrice) : '-'}</p>
                      </div>
                      <div>
                        <p className="text-slate-500">익절 조건</p>
                        <p className="font-mono font-bold text-emerald-300">+{targetRate.toLocaleString()}%</p>
                        <p className="font-mono text-[10px] text-slate-500">{targetPrice > 0 ? formatUnitPrice(targetPrice) : '-'}</p>
                      </div>
                      <div>
                        <p className="text-slate-500">손절 조건</p>
                        <p className="font-mono font-bold text-rose-300">{stopRate.toLocaleString()}%</p>
                        <p className="font-mono text-[10px] text-slate-500">{stopPrice > 0 ? formatUnitPrice(stopPrice) : '-'}</p>
                      </div>
                      <div>
                        <p className="text-slate-500">감시 금액</p>
                        <p className="font-mono font-bold text-white">
                          {Number(rule.investment_amount || 0) > 0
                            ? `${getCurrencySign()}${Number(rule.investment_amount).toLocaleString(undefined, { maximumFractionDigits: getCurrencyDigits() })}`
                            : '-'}
                        </p>
                        <p className="font-mono text-[10px] text-slate-500">
                          수량 {Number(rule.quantity || 0) > 0 ? Number(rule.quantity).toLocaleString(undefined, { maximumFractionDigits: 8 }) : '-'}
                        </p>
                      </div>
                    </div>
                    <div className="mt-3 grid grid-cols-1 gap-2 border-t border-[#1f2945] pt-3 text-[10px] text-slate-500 sm:grid-cols-4">
                      <div>
                        <p>마지막 확인</p>
                        <p className="font-mono text-slate-300">
                          {rule.last_checked_at ? new Date(rule.last_checked_at).toLocaleString('ko-KR') : '-'}
                        </p>
                      </div>
                      <div>
                        <p>현재 수익률</p>
                        <p className={`font-mono font-bold ${currentReturnClass}`}>
                          {formatSignedPercentValue(currentReturnRate)}
                        </p>
                        <p className="font-mono text-[10px] text-slate-600">
                          현재가 {activePrice > 0 ? `${formatUnitPrice(activePrice)}${ruleEnv !== brokerEnv ? ` (${ruleEnv})` : ''}` : '-'}
                        </p>
                      </div>
                      <div>
                        <p>트리거</p>
                        <p className="font-mono text-slate-300">
                          {getAutoTriggerLabel(rule.trigger_side)}
                          {Number(rule.trigger_price || 0) > 0 ? ` · ${formatUnitPrice(rule.trigger_price)}` : ''}
                        </p>
                      </div>
                      <div>
                        <p>최근 오류</p>
                        <p className="truncate text-amber-300">{isRunning ? (rule.last_error || '-') : '-'}</p>
                      </div>
                    </div>
                    {isRunning || String(rule.status || '').toUpperCase() === 'FAILED' ? (
                      <div className="mt-3 flex justify-end gap-2 border-t border-[#1f2945]/40 pt-2.5">
                        <button
                          type="button"
                          onClick={() => onStartEditRule(rule)}
                          className="rounded border border-slate-700 bg-slate-900/30 px-2.5 py-1 text-[10px] text-slate-300 hover:border-slate-500 hover:text-white transition cursor-pointer"
                        >
                          조건 수정
                        </button>
                        <button
                          type="button"
                          disabled={ruleUpdating}
                          onClick={() => onStopRule(rule.id)}
                          className="rounded border border-rose-900/60 bg-rose-950/10 px-2.5 py-1 text-[10px] text-rose-300 hover:border-rose-700 hover:bg-rose-950/20 transition cursor-pointer disabled:opacity-50"
                        >
                          감시 정지
                        </button>
                      </div>
                    ) : (
                      <div className="mt-3 flex justify-end gap-2 border-t border-[#1f2945]/40 pt-2.5">
                        <button
                          type="button"
                          disabled={ruleUpdating}
                          onClick={() => {
                            if (confirm('해당 조건감시 기록을 화면에서 완전히 삭제하시겠습니까?')) {
                              onStopRule(rule.id)
                            }
                          }}
                          className="rounded border border-rose-950 bg-rose-950/20 px-2.5 py-1 text-[10px] text-rose-400 hover:border-rose-800 hover:bg-rose-950/40 transition cursor-pointer disabled:opacity-50"
                        >
                          감시 삭제
                        </button>
                      </div>
                    )}
                  </>
                )}
              </div>
            )
          })}
        </div>
      ) : (
        <div className="rounded border border-[#1f2945] bg-[#070b19] px-3 py-6 text-center text-[11px] text-slate-500">
          현재 종목에 등록된 조건감시 규칙이 없습니다.
        </div>
      )}
    </div>
  )
}
