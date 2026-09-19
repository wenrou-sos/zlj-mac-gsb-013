import { api } from '../api'
import { useStore } from '../store'
import { fmtTime } from '../utils'

const TYPE_LABEL = {
  SEPARATION: '跑道间隔',
  CLOSURE: '跑道关闭',
  TAXIWAY: '滑行道冲突',
}

export default function ConflictList() {
  const { rehearsal, refresh, flash } = useStore()
  if (!rehearsal) return null
  const { conflicts } = rehearsal

  const apply = async (sug) => {
    try {
      const body =
        sug.action === 'CHANGE_RUNWAY'
          ? { flight_id: sug.flight_id, action: 'CHANGE_RUNWAY', to_runway: sug.to_runway }
          : { flight_id: sug.flight_id, action: 'DELAY', delay_seconds: sug.delay_seconds }
      await api.adjust(body)
      await refresh()
    } catch (e) {
      flash(e.message)
    }
  }

  if (!conflicts.length) {
    return (
      <div className="panel">
        <h2>冲突识别</h2>
        <p className="all-clear">✓ 当前调度方案无冲突</p>
      </div>
    )
  }

  return (
    <div className="panel">
      <h2>
        冲突识别
        <span className="badge hard">{rehearsal.hard_count} 严重</span>
        <span className="badge soft">
          {rehearsal.conflict_count - rehearsal.hard_count} 提示
        </span>
      </h2>
      <div className="conflict-list">
        {conflicts.map((c) => (
          <div key={c.id} className={`conflict-card ${c.severity === 'HARD' ? 'hard' : 'soft'}`}>
            <div className="conflict-head">
              <span className={`tag tag-${c.type}`}>{TYPE_LABEL[c.type]}</span>
              <span className="conflict-flights">{c.flights.join(' × ')}</span>
              <span className="conflict-time">
                {fmtTime(c.start)} – {fmtTime(c.end)}
              </span>
            </div>
            <p className="conflict-msg">{c.message}</p>
            <div className="suggestions">
              {c.suggestions.map((s, i) => (
                <button
                  key={i}
                  className="sug-btn"
                  disabled={s.action === 'DELAY' && s.delay_seconds == null}
                  onClick={() => apply(s)}
                  title={s.note}
                >
                  {s.action === 'DELAY'
                    ? `推迟 ${s.callsign}${s.delay_seconds != null ? ' ' + s.delay_seconds + 's' : ''}`
                    : `${s.callsign} 改用跑道 ${s.to_runway}`}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
