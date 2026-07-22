import { useEffect, useState } from 'react'
import { supabase } from '../supabaseClient'

export default function AdminAiFundDashboard({ userId }) {
  const [exchangeType, setExchangeType] = useState('coinone')
  const [capital, setCapital] = useState(5000000)
  const [riskPreset, setRiskPreset] = useState('neutral')
  const [isActive, setIsActive] = useState(false)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [currentUserId, setCurrentUserId] = useState(userId || '')

  useEffect(() => {
    if (!currentUserId) {
      supabase.auth.getSession().then(({ data: { session } }) => {
        if (session?.user?.id) {
          setCurrentUserId(session.user.id)
        }
      })
    }
  }, [currentUserId])

  useEffect(() => {
    if (!currentUserId) return

    // Fetch initial config
    const fetchConfig = async () => {
      const { data } = await supabase
        .from('admin_ai_fund_configs')
        .select('*')
        .eq('user_id', currentUserId)
        .eq('exchange_type', exchangeType)
        .maybeSingle()


      if (data) {
        setCapital(data.allocated_capital || 5000000)
        setRiskPreset(data.risk_preset || 'neutral')
        setIsActive(data.is_active || false)
      }
    }

    fetchConfig()

    // Realtime Subscription
    const channel = supabase
      .channel('admin-ai-fund-changes')
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'admin_ai_fund_configs',
          filter: `user_id=eq.${currentUserId}`,
        },
        (payload) => {
          if (payload.new) {
            setIsActive(payload.new.is_active || false)
            if (payload.new.allocated_capital) setCapital(payload.new.allocated_capital)
            if (payload.new.risk_preset) setRiskPreset(payload.new.risk_preset)
          }
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [currentUserId, exchangeType])

  const handleToggleActive = async () => {
    setLoading(true)
    setMessage('')
    try {
      const nextActive = !isActive
      const { error } = await supabase.from('admin_ai_fund_configs').upsert({
        user_id: currentUserId,
        exchange_type: exchangeType,
        allocated_capital: capital,
        max_position_size: capital * 0.1,
        risk_preset: riskPreset,
        is_active: nextActive,
      })

      if (error) throw error
      setIsActive(nextActive)
      setMessage(nextActive ? '✅ AI 위탁 운용이 시작되었습니다.' : '⏸ AI 위탁 운용이 일시정지되었습니다.')
    } catch (err) {
      setMessage(`❌ 오류: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleEmergencyKillSwitch = async () => {
    if (!confirm('🚨 긴급 셧다운을 실행하시겠습니까? 모든 AI 자동 매매가 즉시 정지됩니다.')) return
    setLoading(true)
    try {
      const { error } = await supabase
        .from('admin_ai_fund_configs')
        .update({ is_active: false })
        .eq('user_id', currentUserId)


      if (error) throw error
      setIsActive(false)
      setMessage('🚨 [긴급 셧다운 완료] 모든 AI 위탁 운용이 정지되었습니다.')
    } catch (err) {
      setMessage(`❌ 셧다운 오류: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 max-w-4xl mx-auto bg-slate-900 text-white rounded-xl shadow-2xl border border-slate-800 space-y-6">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-bold text-emerald-400">관리자 전용 AI 위탁 자동투자 대시보드</h1>
          <p className="text-xs text-slate-400 mt-1">
            Human-on-the-Loop 모델 기반 AI 자율 운용 및 리스크 관리 시스템
          </p>
        </div>
        <button
          onClick={handleEmergencyKillSwitch}
          disabled={loading}
          className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs rounded-lg shadow-lg transition-colors border border-rose-500 animate-pulse"
        >
          🚨 Emergency Stop (Kill-Switch)
        </button>
      </div>

      {message && (
        <div className="p-3 text-xs rounded-md bg-slate-800 border border-slate-700 font-medium">
          {message}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-3">
          <label className="text-xs font-semibold text-slate-300 block">운용 거래소</label>
          <select
            value={exchangeType}
            onChange={(e) => setExchangeType(e.target.value)}
            className="w-full bg-slate-900 border border-slate-700 text-slate-200 text-xs rounded p-2"
          >
            <option value="coinone">코인원 (Coinone)</option>
            <option value="toss">토스증권 (Toss)</option>
            <option value="binance">바이낸스 (Binance)</option>
          </select>
        </div>

        <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-3">
          <label className="text-xs font-semibold text-slate-300 block">위탁 할당 자금 (KRW)</label>
          <input
            type="number"
            value={capital}
            onChange={(e) => setCapital(Number(e.target.value))}
            className="w-full bg-slate-900 border border-slate-700 text-slate-200 text-xs rounded p-2"
          />
        </div>
      </div>

      <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-3">
        <label className="text-xs font-semibold text-slate-300 block">리스크 정책 프리셋</label>
        <div className="grid grid-cols-3 gap-2">
          {['conservative', 'neutral', 'aggressive'].map((preset) => (
            <button
              key={preset}
              type="button"
              onClick={() => setRiskPreset(preset)}
              className={`p-2 text-xs font-medium rounded border ${
                riskPreset === preset
                  ? 'bg-emerald-600 border-emerald-500 text-white'
                  : 'bg-slate-900 border-slate-800 text-slate-400 hover:border-slate-700'
              }`}
            >
              {preset === 'conservative' ? '보수적 (-1%)' : preset === 'neutral' ? '중립적 (-2%)' : '공격적 (-4%)'}
            </button>
          ))}
        </div>
      </div>

      <div className="pt-4 flex justify-end">
        <button
          onClick={handleToggleActive}
          disabled={loading}
          className={`px-6 py-2.5 rounded-lg text-xs font-bold transition-all shadow-md ${
            isActive
              ? 'bg-amber-600 hover:bg-amber-700 text-white'
              : 'bg-emerald-600 hover:bg-emerald-700 text-white'
          }`}
        >
          {isActive ? '⏸ 운용 일시정지' : '▶ AI 위탁 운용 시작'}
        </button>
      </div>
    </div>
  )
}
