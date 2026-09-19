import { useState } from 'react'
import { api } from '../api'
import { useStore } from '../store'
import { fmtTime, toLocalInput, fromLocalInput } from '../utils'

function roundNow(minutesAhead = 1) {
  const d = new Date(Date.now() + minutesAhead * 60_000)
  d.setSeconds(0, 0)
  return toLocalInput(d.toISOString())
}

export default function ClosurePanel() {
  const { closures, config, refresh, flash } = useStore()
  const [runway, setRunway] = useState(config?.runways[0] || '')
  const [start, setStart] = useState(roundNow(2))
  const [end, setEnd] = useState(roundNow(32))
  const [reason, setReason] = useState('道面维护')

  const add = async () => {
    try {
      await api.createClosure({
        runway: runway || config.runways[0],
        start: fromLocalInput(start),
        end: fromLocalInput(end),
        reason: reason || null,
      })
      await refresh()
    } catch (e) {
      flash(e.message)
    }
  }

  const remove = async (id) => {
    await api.deleteClosure(id)
    await refresh()
  }

  return (
    <div className="panel">
      <h2>跑道关闭区间（{closures.length}）</h2>
      <div className="closure-form">
        <select value={runway} onChange={(e) => setRunway(e.target.value)}>
          {config?.runways.map((r) => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
        <label>
          开始
          <input type="datetime-local" step="1" value={start}
                 onChange={(e) => setStart(e.target.value)} />
        </label>
        <label>
          结束
          <input type="datetime-local" step="1" value={end}
                 onChange={(e) => setEnd(e.target.value)} />
        </label>
        <input placeholder="原因" value={reason}
               onChange={(e) => setReason(e.target.value)} />
        <button className="btn primary small" onClick={add}>添加关闭</button>
      </div>
      <ul className="closure-list">
        {closures.map((c) => (
          <li key={c.id}>
            <span className="mono strong">{c.runway}</span>
            <span className="mono">
              {fmtTime(c.start)} – {fmtTime(c.end)}
            </span>
            <span className="muted">{c.reason}</span>
            <button className="link-danger" onClick={() => remove(c.id)}>删除</button>
          </li>
        ))}
        {!closures.length && <li className="muted">暂无关闭区间</li>}
      </ul>
    </div>
  )
}
