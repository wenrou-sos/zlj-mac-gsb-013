import { useState } from 'react'
import { api } from '../api'
import { useStore } from '../store'
import { fmtTime, toLocalInput, fromLocalInput } from '../utils'

const EMPTY = {
  callsign: '',
  operation: 'DEP',
  runway: '',
  wake: 'M',
  scheduled: toLocalInput(new Date(Date.now() + 3600_000).toISOString()),
  route: '',
  eta_to_runway: 300,
  vacate_to_gate: 240,
  stand: '',
}

export default function FlightPanel() {
  const { flights, config, rehearsal, refresh, flash } = useStore()
  const [form, setForm] = useState(EMPTY)
  const [showForm, setShowForm] = useState(false)

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const submit = async () => {
    try {
      await api.createFlight({
        callsign: form.callsign.trim().toUpperCase(),
        operation: form.operation,
        runway: form.runway || config.runways[0],
        wake: form.wake,
        scheduled: fromLocalInput(form.scheduled),
        route: form.route
          .split(/[,\s]+/)
          .map((s) => s.trim())
          .filter(Boolean),
        eta_to_runway: Number(form.eta_to_runway),
        vacate_to_gate: Number(form.vacate_to_gate),
        stand: form.stand || null,
      })
      setForm({ ...EMPTY, scheduled: form.scheduled, runway: form.runway })
      setShowForm(false)
      await refresh()
    } catch (e) {
      flash(e.message)
    }
  }

  const remove = async (id) => {
    await api.deleteFlight(id)
    await refresh()
  }

  const conflictFlights = new Set()
  rehearsal?.conflicts.forEach((c) =>
    c.flight_ids.forEach((id) => conflictFlights.add(id)),
  )

  return (
    <div className="panel">
      <h2>
        航班计划（{flights.length}）
        <button className="btn small" onClick={() => setShowForm((v) => !v)}>
          {showForm ? '取消' : '+ 新增航班'}
        </button>
      </h2>

      {showForm && (
        <div className="form-grid">
          <label>
            呼号
            <input value={form.callsign} onChange={set('callsign')} placeholder="CA1234" />
          </label>
          <label>
            进/离港
            <select value={form.operation} onChange={set('operation')}>
              <option value="DEP">离港 DEP</option>
              <option value="ARR">进港 ARR</option>
            </select>
          </label>
          <label>
            跑道
            <select value={form.runway} onChange={set('runway')}>
              <option value="">请选择</option>
              {config.runways.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </label>
          <label>
            尾流等级
            <select value={form.wake} onChange={set('wake')}>
              <option value="L">L 轻型</option>
              <option value="M">M 中型</option>
              <option value="H">H 重型</option>
            </select>
          </label>
          <label>
            时刻（落地/起飞）
            <input
              type="datetime-local"
              step="1"
              value={form.scheduled}
              onChange={set('scheduled')}
            />
          </label>
          <label>
            机位
            <input value={form.stand} onChange={set('stand')} placeholder="GATE101" />
          </label>
          <label className="span2">
            滑行路线（节点以逗号分隔，离港以跑道入口如 R09L 结尾；进港以跑道入口开头）
            <input
              value={form.route}
              onChange={set('route')}
              placeholder="GATE102, C1, B3, A, R09L"
            />
          </label>
          <label>
            离港：机位→跑道秒数
            <input type="number" value={form.eta_to_runway} onChange={set('eta_to_runway')} />
          </label>
          <label>
            进港：脱离跑道→机位秒数
            <input type="number" value={form.vacate_to_gate} onChange={set('vacate_to_gate')} />
          </label>
          <div className="span2">
            <button className="btn primary" onClick={submit}>保存航班</button>
          </div>
        </div>
      )}

      <table className="data-table">
        <thead>
          <tr>
            <th>呼号</th>
            <th>类型</th>
            <th>尾流</th>
            <th>跑道</th>
            <th>计划时刻</th>
            <th>滑行路线</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {flights.map((f) => (
            <tr key={f.id} className={conflictFlights.has(f.id) ? 'row-conflict' : ''}>
              <td className="mono">{f.callsign}</td>
              <td>
                <span className={`op-badge ${f.operation === 'ARR' ? 'arr' : 'dep'}`}>
                  {f.operation === 'ARR' ? '进港' : '离港'}
                </span>
              </td>
              <td>{f.wake}</td>
              <td className="mono">{f.runway}</td>
              <td className="mono">{fmtTime(f.scheduled)}</td>
              <td className="route-cell" title={f.route.join(' → ')}>
                {f.route.slice(0, 4).join(' → ')}
                {f.route.length > 4 ? ' …' : ''}
              </td>
              <td>
                <button className="link-danger" onClick={() => remove(f.id)}>删除</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
