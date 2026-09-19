import type { Conflict, Resolution } from "../lib/types";
import { fmtClock, fmtDuration } from "../lib/time";

interface Props {
  conflicts: Conflict[];
  resolutions: Resolution[];
  onApplyDelay?: (flightId: string, delta: number) => void;
}

const TYPE_LABEL: Record<Conflict["type"], string> = {
  SEPARATION: "安全间隔不足",
  OCCUPANCY: "跑道占用重叠",
  CROSSING: "穿越冲突",
  CLOSURE: "跑道关闭冲突",
};

const TYPE_COLOR: Record<Conflict["type"], string> = {
  SEPARATION: "sep",
  OCCUPANCY: "occ",
  CROSSING: "cross",
  CLOSURE: "closure",
};

export function ConflictPanel({ conflicts, resolutions, onApplyDelay }: Props) {
  return (
    <div className="panel">
      <h3>
        调度冲突
        <span
          className={`badge ${conflicts.length ? "bad" : "good"}`}
          data-testid="conflict-count"
        >
          {conflicts.length}
        </span>
      </h3>
      {conflicts.length === 0 ? (
        <p className="empty-hint">✓ 当前方案无冲突</p>
      ) : (
        <ul className="conflict-list">
          {conflicts.map((c) => (
            <li key={c.id} className={`conflict-item ${TYPE_COLOR[c.type]}`}>
              <div className="conflict-head">
                <span className={`tag ${TYPE_COLOR[c.type]}`}>
                  {TYPE_LABEL[c.type]}
                </span>
                <span className="conflict-time">{fmtClock(c.time)}</span>
                <span className={`severity ${c.severity}`}>{c.severity}</span>
              </div>
              <p>{c.message}</p>
              {c.actual_gap_seconds !== undefined && (
                <p className="sub">
                  实际 {c.actual_gap_seconds}s / 规定{" "}
                  {c.required_gap_seconds}s
                </p>
              )}
            </li>
          ))}
        </ul>
      )}

      {resolutions.length > 0 && (
        <>
          <h3>调整方案建议</h3>
          <ul className="resolution-list">
            {resolutions.map((r) => (
              <li key={r.flight_id} className="resolution-item">
                <div className="resolution-head">
                  <strong>{r.callsign}</strong>
                  <span className="sub">
                    涉及 {r.conflict_ids.length} 项冲突
                  </span>
                </div>
                <div className="options">
                  {r.options.length === 0 && (
                    <span className="hint">在允许延误范围内无可消解方案</span>
                  )}
                  {r.options.map((o, i) => (
                    <button
                      key={i}
                      className="option"
                      disabled={
                        o.kind === "CHANGE_RUNWAY" &&
                        (o.residual_conflicts ?? 0) > 0
                      }
                      title={o.description}
                      onClick={() =>
                        o.kind === "DELAY" &&
                        onApplyDelay?.(
                          r.flight_id,
                          o.delta_seconds ?? 0
                        )
                      }
                    >
                      {o.kind === "DELAY" ? "⏱" : "↔"} {o.description}
                      {o.kind === "DELAY" && o.delta_seconds !== undefined && (
                        <em> 点击应用顺延</em>
                      )}
                    </button>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

export function formatDelay(seconds: number) {
  return fmtDuration(seconds);
}
