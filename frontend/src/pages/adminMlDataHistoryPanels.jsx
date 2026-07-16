import { formatPath, formatTime } from './adminMlDataModel.js'
import { AuditBadge, GuardSummary } from './adminMlDataCorePanels.jsx'

function JobStatusBadge({ status }) {
  return (
    <span className={`rounded border px-2 text-[9px] font-bold ${
      status === 'success'
        ? 'border-emerald-500/40 bg-emerald-950/20 text-emerald-300'
        : status === 'failed'
          ? 'border-red-500/40 bg-red-950/20 text-red-300'
          : 'border-ai-cyan/40 bg-ai-cyan/5 text-ai-cyan'
    }`}>
      {String(status || 'running').toUpperCase()}
    </span>
  )
}

function JobAuditSummary({ job, table = false }) {
  const className = table ? 'min-w-[180px] space-y-1' : 'space-y-1'

  return (
    <div className={className}>
      {job.training_audit?.promotion_guard ? (
        <GuardSummary guardReport={job.training_audit.promotion_guard} compact />
      ) : job.guard_report ? (
        <GuardSummary guardReport={job.guard_report} compact />
      ) : job.serving_audit_report ? (
        <div className="space-y-1">
          <AuditBadge status={job.serving_audit_report.status}>
            {job.serving_audit_report.status === 'healthy' ? '서빙 정상' : '서빙 경고'}
          </AuditBadge>
          <p className="text-[10px] text-slate-500">
            차단 {job.serving_audit_report.blocking_count ?? 0}건
          </p>
        </div>
      ) : (
        <p className="text-[10px] text-slate-500">감사 정보 없음</p>
      )}
    </div>
  )
}

export function JobHistoryPanel({ jobs = [], loading, error, onShowLog, variant = 'desktop' }) {
  if (loading) {
    return (
      <div className="rounded-lg border border-slate-800 bg-[#0f172a] p-4 text-sm text-slate-400">
        작업 이력을 불러오는 중입니다.
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-800 bg-red-950/30 p-4 text-sm leading-6 text-red-300">
        {error}
      </div>
    )
  }

  if (!jobs.length) {
    return (
      <div className="rounded-lg border border-slate-800 bg-[#0f172a] p-4 text-sm text-slate-400">
        아직 기록된 작업이 없습니다.
      </div>
    )
  }

  if (variant === 'mobile') {
    return (
      <div className="grid gap-2.5">
        {jobs.map((job) => (
          <article key={job.id} className="rounded-lg border border-slate-800 bg-[#0f172a] p-3 text-xs text-slate-300">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-bold text-white" title={job.label || job.exchange || job.id}>
                  {job.label || job.exchange || job.id}
                </p>
                <p className="mt-1 truncate font-mono text-[10px] text-slate-500" title={job.output || job.config || ''}>
                  {formatPath(job.output) || formatPath(job.config) || job.interval || '-'}
                </p>
              </div>
              <JobStatusBadge status={job.status} />
            </div>

            <div className="mt-3 grid grid-cols-2 gap-2">
              <div className="rounded bg-slate-950/50 px-2.5 py-2">
                <p className="text-[10px] font-bold text-slate-500">유형</p>
                <p className="mt-1 truncate font-mono text-[11px] text-slate-300">{job.type || '-'}</p>
              </div>
              <div className="rounded bg-slate-950/50 px-2.5 py-2">
                <p className="text-[10px] font-bold text-slate-500">실패</p>
                <p className="mt-1 font-mono text-[11px] text-amber-300">{job.failure_count || 0}건</p>
              </div>
              <div className="rounded bg-slate-950/50 px-2.5 py-2">
                <p className="text-[10px] font-bold text-slate-500">시작</p>
                <p className="mt-1 font-mono text-[11px] text-slate-300">{formatTime(job.started_at)}</p>
              </div>
              <div className="rounded bg-slate-950/50 px-2.5 py-2">
                <p className="text-[10px] font-bold text-slate-500">종료</p>
                <p className="mt-1 font-mono text-[11px] text-slate-300">{formatTime(job.finished_at)}</p>
              </div>
            </div>

            <div className="mt-3 rounded bg-slate-950/50 px-2.5 py-2">
              <JobAuditSummary job={job} />
            </div>

            <button
              type="button"
              onClick={() => onShowLog?.(job)}
              className="mt-3 w-full rounded border border-slate-700 bg-slate-800/40 px-3 py-2 text-[11px] font-bold text-slate-300 transition hover:border-ai-cyan hover:text-white"
            >
              로그 보기
            </button>
          </article>
        ))}
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-800 bg-[#0f172a]">
      <table className="min-w-full text-left text-xs text-slate-300">
        <thead className="text-[10px] uppercase tracking-wider text-slate-500">
          <tr>
            <th className="px-3 py-2">작업</th>
            <th className="px-3 py-2">유형</th>
            <th className="px-3 py-2">상태</th>
            <th className="px-3 py-2">설정</th>
            <th className="px-3 py-2">검증</th>
            <th className="px-3 py-2">시작</th>
            <th className="px-3 py-2">종료</th>
            <th className="px-3 py-2 text-right">로그</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.id} className="border-t border-slate-800 align-top transition hover:bg-white/5">
              <td className="px-3 py-2">
                <p className="font-semibold text-white truncate max-w-[150px]" title={job.label || job.exchange || job.id}>
                  {job.label || job.exchange || job.id}
                </p>
                {job.output ? (
                  <p className="mt-1 truncate font-mono text-[10px] text-slate-500 max-w-[150px]" title={job.output}>
                    {formatPath(job.output)}
                  </p>
                ) : null}
                {job.failure_count ? (
                  <p className="mt-1 text-[10px] text-amber-300">실패 심볼 {job.failure_count}건</p>
                ) : null}
              </td>
              <td className="px-3 py-2 font-mono text-[10px] text-slate-400">{job.type}</td>
              <td className="px-3 py-2">
                <JobStatusBadge status={job.status} />
              </td>
              <td className="px-3 py-2">
                <p className="truncate font-mono text-[10px] text-slate-400 max-w-[150px]" title={job.config || job.interval || '-'}>
                  {formatPath(job.config) || job.interval || '-'}
                </p>
              </td>
              <td className="px-3 py-2">
                <JobAuditSummary job={job} table />
              </td>
              <td className="px-3 py-2 font-mono text-[10px] text-slate-400 whitespace-nowrap">{formatTime(job.started_at)}</td>
              <td className="px-3 py-2 font-mono text-[10px] text-slate-400 whitespace-nowrap">{formatTime(job.finished_at)}</td>
              <td className="px-3 py-2 text-right">
                <button
                  type="button"
                  onClick={() => onShowLog?.(job)}
                  className="rounded border border-slate-700 bg-slate-800/40 px-2 py-1 text-[10px] font-bold text-slate-300 transition hover:border-ai-cyan hover:text-white"
                >
                  로그 보기
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
