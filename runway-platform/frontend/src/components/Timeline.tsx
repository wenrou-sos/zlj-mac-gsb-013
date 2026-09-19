import { useMemo } from "react";
import type { Closure, Conflict, Flight } from "../lib/types";
import { runwayIntervals } from "../lib/intervals";

interface Props {
  flights: Flight[];
  closures: Closure[];
  conflicts: Conflict[];
  runways: { id: string }[];
}

const PADDING = 60; // 秒：时间轴两侧留白

export function Timeline({ flights, closures, conflicts, runways }: Props) {
  const model = useMemo(() => {
    const bars: {
      runwayId: string;
      start: number;
      end: number;
      role: "use" | "cross";
      label: string;
      flightId: string;
      conflicting: boolean;
    }[] = [];

    flights.forEach((f) => {
      runwayIntervals(f).forEach((iv) => {
        const conflicting = conflicts.some(
          (c) => c.runway_id === iv.runwayId && f.id && c.flight_ids.includes(f.id)
        );
        bars.push({
          runwayId: iv.runwayId,
          start: iv.start.getTime(),
          end: iv.end.getTime(),
          role: iv.role,
          label: f.callsign,
          flightId: f.id,
          conflicting,
        });
      });
    });

    const closureBars = closures.map((c) => ({
      runwayId: c.runway_id,
      start: new Date(c.start_time).getTime(),
      end: new Date(c.end_time).getTime(),
      label: c.reason || "关闭",
      id: c.id,
    }));

    const points = [
      ...bars.map((b) => [b.start, b.end]).flat(),
      ...closureBars.map((b) => [b.start, b.end]).flat(),
    ];
    if (points.length === 0) return null;
    const min = Math.min(...points) / 1000 - PADDING;
    const max = Math.max(...points) / 1000 + PADDING;
    return {
      bars,
      closureBars,
      min,
      max,
      rows: runways.map((r) => r.id),
    };
  }, [flights, closures, conflicts, runways]);

  if (!model) {
    return <div className="empty-hint">暂无数据，请先配置航班。</div>;
  }

  const span = Math.max(model.max - model.min, 1);
  const pct = (tSec: number) =>
    ((tSec - model.min) / span) * 100;

  const tickCount = 6;
  const ticks = Array.from({ length: tickCount + 1 }, (_, i) => {
    const t = model.min + (span * i) / tickCount;
    return { left: (i / tickCount) * 100, label: fmtTick(t) };
  });

  const conflictFlightIds = new Set(conflicts.flatMap((c) => c.flight_ids));

  return (
    <div className="timeline" data-testid="timeline">
      <div className="timeline-axis">
        {ticks.map((t, i) => (
          <span key={i} className="tick" style={{ left: `${t.left}%` }}>
            {t.label}
          </span>
        ))}
      </div>
      {model.rows.map((rid) => (
        <div className="timeline-row" key={rid}>
          <div className="timeline-label">跑道 {rid}</div>
          <div className="timeline-track">
            {model.closureBars
              .filter((b) => b.runwayId === rid)
              .map((b) => (
                <div
                  key={`cl-${b.id}`}
                  className="bar closure"
                  title={`关闭：${b.label}`}
                  style={{
                    left: `${pct(b.start / 1000)}%`,
                    width: `${pct(b.end / 1000) - pct(b.start / 1000)}%`,
                  }}
                >
                  {b.label}
                </div>
              ))}
            {model.bars
              .filter((b) => b.runwayId === rid)
              .map((b, idx) => (
                <div
                  key={`${b.flightId}-${idx}`}
                  className={`bar ${b.role} ${
                    b.conflicting || conflictFlightIds.has(b.flightId)
                      ? "conflict"
                      : ""
                  }`}
                  title={`${b.label} ${b.role === "cross" ? "穿越" : "占用"}`}
                  style={{
                    left: `${pct(b.start / 1000)}%`,
                    width: `${Math.max(
                      pct(b.end / 1000) - pct(b.start / 1000),
                      1.2
                    )}%`,
                  }}
                >
                  {b.label}
                </div>
              ))}
          </div>
        </div>
      ))}
      <div className="timeline-legend">
        <span><i className="dot use" /> 跑道占用</span>
        <span><i className="dot cross" /> 滑行穿越</span>
        <span><i className="dot closure" /> 关闭区间</span>
        <span><i className="dot conflict" /> 涉及冲突</span>
      </div>
    </div>
  );
}

function fmtTick(unixSec: number): string {
  const d = new Date(unixSec * 1000);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(
    d.getUTCSeconds()
  )}`;
}
