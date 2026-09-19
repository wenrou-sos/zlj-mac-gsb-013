import type { Flight } from "./types";

export type Role = "use" | "cross";

export interface RunwayInterval {
  runwayId: string;
  start: Date;
  end: Date;
  role: Role;
}

/** 与后端 engine.runway_intervals 对应的前端实现，供时间轴绘制。 */
export function runwayIntervals(flight: Flight): RunwayInterval[] {
  const refIso =
    flight.operation === "departure"
      ? flight.takeoff_time
      : flight.landing_time;
  if (!refIso) return [];
  const ref = new Date(refIso);
  const primary = flight.runway_id;
  const steps = (flight.route ?? []).filter((s) => s.type === "runway");

  if (steps.length === 0) {
    return [
      {
        runwayId: primary,
        start: new Date(ref.getTime() - flight.enter_offset * 1000),
        end: new Date(ref.getTime() + flight.vacate_offset * 1000),
        role: "use",
      },
    ];
  }

  const primaryIdx = steps.findIndex((s) => (s.runway_id ?? primary) === primary);
  const out: RunwayInterval[] = [];
  let foundPrimary = false;

  steps.forEach((step, i) => {
    const rid = step.runway_id ?? primary;
    if (!foundPrimary && rid === primary) {
      const enter = step.enter_offset ?? flight.enter_offset;
      const vacate = step.vacate_offset ?? flight.vacate_offset;
      out.push({
        runwayId: rid,
        start: new Date(ref.getTime() - enter * 1000),
        end: new Date(ref.getTime() + vacate * 1000),
        role: "use",
      });
      foundPrimary = true;
    } else {
      let t = ref.getTime();
      if (flight.operation === "departure") {
        for (let j = i; j < primaryIdx; j++) {
          t -= (steps[j].taxi_seconds ?? 45) * 1000;
        }
      } else {
        for (let j = primaryIdx; j < i; j++) {
          t += (steps[j].taxi_seconds ?? 45) * 1000;
        }
      }
      const dur = (step.crossing_duration ?? 30) * 1000;
      out.push({
        runwayId: rid,
        start: new Date(t),
        end: new Date(t + dur),
        role: "cross",
      });
    }
  });
  return out;
}

export function baseTime(flight: Flight): Date {
  return new Date(
    (flight.operation === "departure"
      ? flight.takeoff_time
      : flight.landing_time) as string
  );
}
