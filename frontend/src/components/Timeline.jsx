import { useMemo, useState } from 'react'
import { fmtTime } from '../utils'

/**
 * Horizontal time-line. One swim lane per runway; flights' runway occupancy
 * bars plus taxiway rows are drawn over closure bands. Conflicting flights
 * are outlined in red; hovering a bar highlights its taxi segments.
 */
export default function Timeline({ windows, closures, conflicts }) {
  const [hover, setHover] = useState(null)

  const { t0, t1, lanes } = useMemo(() => {
    const times = []
    windows.forEach((w) => {
      times.push(new Date(w.runway_start), new Date(w.runway_end))
      w.taxi.forEach((t) => {
        times.push(new Date(t.start), new Date(t.end))
      })
    })
    closures.forEach((c) => {
      times.push(new Date(c.start), new Date(c.end))
    })
    if (!times.length) return { t0: 0, t1: 1, lanes: [] }
    let min = Math.min(...times.map((d) => d.getTime()))
    let max = Math.max(...times.map((d) => d.getTime()))
    // pad 60 s each side
    min -= 60_000
    max += 60_000

    const runways = [...new Set(windows.map((w) => w.runway))].sort()
    const byRunway = new Map(runways.map((r) => [r, []]))
    windows.forEach((w) => byRunway.get(w.runway).push(w))
    return { t0: min, t1: max, lanes: runways.map((r) => ({ runway: r, items: byRunway.get(r) })) }
  }, [windows, closures])

  const span = Math.max(1, t1 - t0)
  const x = (iso) => ((new Date(iso).getTime() - t0) / span) * 100
  const w = (a, b) => Math.max(0.3, x(b) - x(a))

  const conflictIds = new Set()
  conflicts.forEach((c) => c.flight_ids.forEach((id) => conflictIds.add(id)))
  const taxiConflictNodes = new Map(
    conflicts.filter((c) => c.type === 'TAXIWAY').map((c) => [c.taxiway, c.flight_ids]),
  )

  // tick marks every 5 minutes
  const ticks = useMemo(() => {
    const out = []
    const step = 5 * 60_000
    const start = Math.ceil(t0 / step) * step
    for (let t = start; t < t1; t += step) out.push(t)
    return out
  }, [t0, t1])

  return (
    <div className="timeline">
      <div className="timeline-header">
        {ticks.map((t) => (
          <div
            key={t}
            className="tick"
            style={{ left: `${((t - t0) / span) * 100}%` }}
          >
            {fmtTime(new Date(t).toISOString())}
          </div>
        ))}
      </div>
      {lanes.map((lane) => (
        <div className="lane" key={lane.runway}>
          <div className="lane-label">{lane.runway}</div>
          <div className="lane-track">
            {closures
              .filter((c) => c.runway === lane.runway)
              .map((c) => (
                <div
                  key={`clo-${c.id}`}
                  className="closure-band"
                  title={`关闭 ${fmtTime(c.start)}–${fmtTime(c.end)} ${c.reason || ''}`}
                  style={{
                    left: `${x(c.start)}%`,
                    width: `${w(c.start, c.end)}%`,
                  }}
                >
                  关闭
                </div>
              ))}
            {ticks.map((t) => (
              <div
                key={t}
                className="gridline"
                style={{ left: `${((t - t0) / span) * 100}%` }}
              />
            ))}
            {/* taxi segments (faded, under runway bars) */}
            {lane.items.flatMap((item) =>
              item.taxi.map((seg) => {
                const hot = taxiConflictNodes.get(seg.taxiway)?.includes(item.flight_id)
                return (
                  <div
                    key={`${item.flight_id}-${seg.taxiway}`}
                    className={`taxi-bar ${item.operation === 'ARR' ? 'arr' : 'dep'} ${hover === item.flight_id ? 'hover' : ''} ${hot ? 'taxi-hot' : ''}`}
                    title={`${item.callsign} @ ${seg.taxiway}`}
                    onMouseEnter={() => setHover(item.flight_id)}
                    onMouseLeave={() => setHover(null)}
                    style={{
                      left: `${x(seg.start)}%`,
                      width: `${w(seg.start, seg.end)}%`,
                      top: item.operation === 'ARR' ? 2 : 16,
                    }}
                  >
                    {seg.taxiway}
                  </div>
                )
              }),
            )}
            {/* runway occupancy bars */}
            {lane.items.map((item) => {
              const bad = conflictIds.has(item.flight_id)
              return (
                <div
                  key={item.flight_id}
                  className={`runway-bar ${item.operation === 'ARR' ? 'arr' : 'dep'} ${bad ? 'conflict' : ''} ${hover === item.flight_id ? 'hover' : ''}`}
                  title={`${item.callsign} (${item.operation === 'ARR' ? '进港' : '离港'}) ${fmtTime(item.runway_start)}–${fmtTime(item.runway_end)}`}
                  onMouseEnter={() => setHover(item.flight_id)}
                  onMouseLeave={() => setHover(null)}
                  style={{
                    left: `${x(item.runway_start)}%`,
                    width: `${w(item.runway_start, item.runway_end)}%`,
                  }}
                >
                  {item.callsign}
                </div>
              )
            })}
          </div>
        </div>
      ))}
      <div className="legend">
        <span><i className="sw dep" /> 离港占用</span>
        <span><i className="sw arr" /> 进港占用</span>
        <span><i className="sw taxi-hot" /> 滑行道</span>
        <span><i className="sw closure-band-sm" /> 关闭区间</span>
        <span><i className="sw conflict-sm" /> 涉冲突航班</span>
      </div>
    </div>
  )
}
