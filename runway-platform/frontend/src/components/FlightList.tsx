import type { Flight } from "../lib/types";
import { fmtClock } from "../lib/time";

interface Props {
  flights: Flight[];
  onEdit: (f: Flight) => void;
  onDelete: (id: string) => void;
  adjusted: Record<string, number>;
}

export function FlightList({ flights, onEdit, onDelete, adjusted }: Props) {
  const sorted = [...flights].sort((a, b) => {
    const ta = new Date(
      (a.operation === "departure" ? a.takeoff_time : a.landing_time) ?? 0
    ).getTime();
    const tb = new Date(
      (b.operation === "departure" ? b.takeoff_time : b.landing_time) ?? 0
    ).getTime();
    return ta - tb;
  });

  return (
    <div className="panel">
      <h3>
        航班计划
        <span className="badge">{flights.length}</span>
      </h3>
      <table className="flight-table">
        <thead>
          <tr>
            <th>航班号</th>
            <th>呼号</th>
            <th>类型</th>
            <th>跑道</th>
            <th>基准时刻</th>
            <th>路线节点</th>
            <th>调整</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((f) => {
            const ref =
              f.operation === "departure" ? f.takeoff_time : f.landing_time;
            const delay = adjusted[f.id] ?? 0;
            return (
              <tr key={f.id}>
                <td>{f.id}</td>
                <td>{f.callsign}</td>
                <td>
                  <span
                    className={`op ${f.operation === "departure" ? "dep" : "arr"}`}
                  >
                    {f.operation === "departure" ? "离场" : "进场"}
                  </span>
                </td>
                <td>{f.runway_id}</td>
                <td>{fmtClock(ref)}</td>
                <td>{f.route?.length ?? 0}</td>
                <td>
                  {delay > 0 ? (
                    <span className="delay">+{delay}s</span>
                  ) : (
                    <span className="sub">—</span>
                  )}
                </td>
                <td className="actions">
                  <button className="small" onClick={() => onEdit(f)}>
                    编辑
                  </button>
                  <button
                    className="small danger"
                    onClick={() => onDelete(f.id)}
                  >
                    删除
                  </button>
                </td>
              </tr>
            );
          })}
          {sorted.length === 0 && (
            <tr>
              <td colSpan={8} className="empty-hint">
                暂无航班
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
