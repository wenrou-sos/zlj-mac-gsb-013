import { useState } from 'react'
import { api } from '../api'
import { useStore } from '../store'

export default function Toolbar() {
  const { refresh, flash, rehearsal } = useStore()
  const [busy, setBusy] = useState(false)
  const [log, setLog] = useState(null)

  const auto = async () => {
    setBusy(true)
    setLog(null)
    try {
      const r = await api.autoResolve()
      setLog(r)
      await refresh()
    } catch (e) {
      flash(e.message)
    } finally {
      setBusy(false)
    }
  }

  const reset = async () => {
    setBusy(true)
    try {
      await api.resetDemo()
      setLog(null)
      await refresh()
    } catch (e) {
      flash(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="toolbar">
      <div className="toolbar-actions">
        <button className="btn primary big" disabled={busy} onClick={auto}>
          {busy ? '计算中…' : '⚙ 一键自动调整'}
        </button>
        <button className="btn" disabled={busy} onClick={reset}>
          ↺ 重置演示场景
        </button>
        <button className="btn ghost" disabled={busy} onClick={refresh}>
          ⟳ 重新预演
        </button>
      </div>
      <div className="toolbar-stat">
        当前冲突 <strong className={rehearsal?.conflict_count ? 'stat-bad' : 'stat-ok'}>
          {rehearsal?.conflict_count ?? '—'}
        </strong>
        （严重 {rehearsal?.hard_count ?? 0}）
      </div>
      {log && (
        <div className="resolver-log panel-inner">
          <h3>
            自动调整结果：消解 {log.resolved_count} 项冲突
            {log.remaining.length === 0
              ? '，方案可行 ✓'
              : `，剩余 ${log.remaining.length} 项需人工处理`}
          </h3>
          <ul>
            {log.log.map((line, i) => <li key={i}>{line}</li>)}
          </ul>
        </div>
      )}
    </div>
  )
}
