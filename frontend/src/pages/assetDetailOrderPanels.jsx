import {
  getOrderSideLabel,
  getOrderStatusLabel,
  isCancelReplaceExchange,
} from './assetDetailModel.js'

export function AssetDetailPositionSummary({
  holdingSummaryLabel,
  availableCashLabel,
  openOrdersCount,
  className = 'grid grid-cols-1 gap-3 sm:grid-cols-3',
}) {
  return (
    <div className={className}>
      <div className="rounded-xl border border-[#1f2945] bg-[#0e1529]/90 p-4 backdrop-blur-md">
        <p className="text-[10px] font-bold tracking-[0.08em] text-slate-500">보유 현황</p>
        <p className="mt-2 font-mono text-sm font-black text-white">{holdingSummaryLabel}</p>
        <p className="mt-1 text-[10px] text-slate-500">현재 선택 계좌 기준</p>
      </div>
      <div className="rounded-xl border border-[#1f2945] bg-[#0e1529]/90 p-4 backdrop-blur-md">
        <p className="text-[10px] font-bold tracking-[0.08em] text-slate-500">주문 가능 금액</p>
        <p className="mt-2 font-mono text-sm font-black text-cyan-300">{availableCashLabel}</p>
        <p className="mt-1 text-[10px] text-slate-500">주문 입력 시 사전검증 반영</p>
      </div>
      <div className="rounded-xl border border-[#1f2945] bg-[#0e1529]/90 p-4 backdrop-blur-md">
        <p className="text-[10px] font-bold tracking-[0.08em] text-slate-500">주문 관리</p>
        <p className="mt-2 font-mono text-sm font-black text-amber-300">{openOrdersCount}건 미체결</p>
        <p className="mt-1 text-[10px] text-slate-500">현재 종목 취소/정정 가능</p>
      </div>
    </div>
  )
}

export function AssetDetailOpenOrdersPanel({
  openOrders,
  openOrdersLoading,
  orderActionLoadingId,
  orderManagementMessage,
  brokerEnv,
  modifyOrderId,
  modifyDraft,
  formatUnitPrice,
  onSyncOpenOrders,
  onOpenModifyOrder,
  onCancelOpenOrder,
  onSubmitModifyOrder,
  onModifyDraftChange,
  onCloseModifyOrder,
  className = 'rounded-xl border border-[#1f2945] bg-[#0e1529]/90 p-4 backdrop-blur-md',
}) {
  return (
    <div className={className}>
      <div className="mb-3 flex flex-col gap-3 border-b border-[#1f2945] pb-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-3 rounded-full bg-amber-300" />
            <span className="text-xs font-bold text-white">미체결 주문 관리</span>
          </div>
          <p className="mt-1 text-[10px] text-slate-500">
            현재 종목과 선택 계좌 기준으로 취소/정정을 처리합니다.
          </p>
        </div>
        <button
          type="button"
          onClick={onSyncOpenOrders}
          disabled={Boolean(orderActionLoadingId)}
          className="rounded border border-cyan-500/30 px-3 py-2 text-[10px] font-black text-cyan-300 transition hover:bg-cyan-950/40 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {orderActionLoadingId === 'sync-open-orders' ? '갱신 중' : '상태 새로고침'}
        </button>
      </div>

      {orderManagementMessage.text ? (
        <div className={`mb-3 rounded border px-3 py-2 text-[11px] leading-5 ${
          orderManagementMessage.isError
            ? 'border-rose-900/60 bg-rose-950/30 text-rose-300'
            : 'border-cyan-900/60 bg-cyan-950/20 text-cyan-300'
        }`}>
          {orderManagementMessage.text}
        </div>
      ) : null}

      {openOrdersLoading ? (
        <div className="rounded border border-[#1f2945] bg-[#070b19] px-3 py-6 text-center text-[11px] font-mono text-cyan-300">
          미체결 주문을 불러오는 중...
        </div>
      ) : openOrders.length > 0 ? (
        <div className="flex flex-col gap-2">
          {openOrders.map((order) => {
            const isEditing = modifyOrderId === order.id
            const orderSideLabel = getOrderSideLabel(order.side)
            const orderStatusLabel = getOrderStatusLabel(order.status)
            const isCancelReplace = isCancelReplaceExchange(order.exchange)

            return (
              <div key={order.id} className="rounded-lg border border-[#1f2945] bg-[#070b19]/90 p-3">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`rounded px-2 py-1 text-[10px] font-black ${
                        String(order.side || '').toUpperCase() === 'SELL'
                          ? 'bg-blue-500/15 text-blue-300'
                          : 'bg-red-500/15 text-red-300'
                      }`}>
                        {orderSideLabel}
                      </span>
                      <span className="rounded border border-slate-700 px-2 py-1 text-[10px] font-bold text-slate-300">
                        {orderStatusLabel}
                      </span>
                      <span className="font-mono text-[10px] text-slate-500">
                        {order.exchange} · {order.broker_env || brokerEnv}
                      </span>
                    </div>
                    <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-[11px] sm:grid-cols-4">
                      <div>
                        <p className="text-slate-500">가격</p>
                        <p className="font-mono font-bold text-white">{formatUnitPrice(order.price)}</p>
                      </div>
                      <div>
                        <p className="text-slate-500">수량</p>
                        <p className="font-mono font-bold text-white">{Number(order.volume || 0).toLocaleString()}</p>
                      </div>
                      <div>
                        <p className="text-slate-500">유형</p>
                        <p className="font-mono font-bold text-white">{order.ord_type || 'LIMIT'}</p>
                      </div>
                      <div>
                        <p className="text-slate-500">주문번호</p>
                        <p className="max-w-[120px] truncate font-mono font-bold text-slate-300">{order.external_order_id || '-'}</p>
                      </div>
                    </div>
                  </div>
                  <div className="flex shrink-0 flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => onOpenModifyOrder(order)}
                      disabled={Boolean(orderActionLoadingId)}
                      className="rounded border border-cyan-500/30 px-3 py-1.5 text-[10px] font-bold text-cyan-300 transition hover:bg-cyan-950/30 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {isCancelReplace ? '취소 후 재주문' : '정정'}
                    </button>
                    <button
                      type="button"
                      onClick={() => onCancelOpenOrder(order)}
                      disabled={Boolean(orderActionLoadingId)}
                      className="rounded border border-rose-500/30 px-3 py-1.5 text-[10px] font-bold text-rose-300 transition hover:bg-rose-950/30 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {orderActionLoadingId === `cancel-${order.id}` ? '취소 중' : '취소'}
                    </button>
                  </div>
                </div>

                {isEditing ? (
                  <div className="mt-3 rounded border border-cyan-900/40 bg-cyan-950/10 p-3">
                    <div className="mb-2 text-[10px] font-bold text-cyan-300">
                      {isCancelReplace ? '새 주문 값 입력' : '정정 값 입력'}
                    </div>
                    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                      <label className="flex flex-col gap-1 text-[10px] font-bold text-slate-400">
                        가격
                        <input
                          type="number"
                          step="any"
                          value={modifyDraft.price}
                          onChange={(event) => onModifyDraftChange((prev) => ({ ...prev, price: event.target.value }))}
                          className="rounded border border-slate-700 bg-[#070b19] px-2 py-2 font-mono text-xs text-white outline-none focus:border-cyan-400"
                        />
                      </label>
                      <label className="flex flex-col gap-1 text-[10px] font-bold text-slate-400">
                        수량
                        <input
                          type="number"
                          step="any"
                          value={modifyDraft.quantity}
                          onChange={(event) => onModifyDraftChange((prev) => ({ ...prev, quantity: event.target.value }))}
                          className="rounded border border-slate-700 bg-[#070b19] px-2 py-2 font-mono text-xs text-white outline-none focus:border-cyan-400"
                        />
                      </label>
                    </div>
                    <div className="mt-3 flex justify-end gap-2">
                      <button
                        type="button"
                        onClick={onCloseModifyOrder}
                        className="rounded border border-slate-700 px-3 py-1.5 text-[10px] font-bold text-slate-300 transition hover:text-white"
                      >
                        닫기
                      </button>
                      <button
                        type="button"
                        onClick={() => onSubmitModifyOrder(order)}
                        disabled={Boolean(orderActionLoadingId)}
                        className="rounded border border-cyan-500/40 bg-cyan-950/30 px-3 py-1.5 text-[10px] font-black text-cyan-300 transition hover:bg-cyan-900/40 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {orderActionLoadingId === `modify-${order.id}` ? '처리 중' : isCancelReplace ? '재주문 요청' : '정정 요청'}
                      </button>
                    </div>
                  </div>
                ) : null}
              </div>
            )
          })}
        </div>
      ) : (
        <div className="rounded border border-[#1f2945] bg-[#070b19] px-3 py-6 text-center text-[11px] text-slate-500">
          현재 선택한 계좌의 미체결 주문이 없습니다.
        </div>
      )}
    </div>
  )
}
