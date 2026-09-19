import { describe, expect, it } from "vitest";
import type { Flight } from "../lib/types";
import { baseTime, runwayIntervals } from "../lib/intervals";

const dep = (over: Partial<Flight> = {}): Flight => ({
  id: "F1",
  callsign: "F1",
  operation: "departure",
  runway_id: "09L",
  takeoff_time: "2026-09-19T08:00:00Z",
  enter_offset: 60,
  vacate_offset: 40,
  route: [],
  ...over,
});

describe("runwayIntervals（与后端引擎一致）", () => {
  it("无路线时按进入/脱离偏移生成占用窗口", () => {
    const ivs = runwayIntervals(dep());
    expect(ivs).toHaveLength(1);
    expect(ivs[0].runwayId).toBe("09L");
    expect(ivs[0].role).toBe("use");
    expect(ivs[0].start.toISOString()).toBe("2026-09-19T07:59:00.000Z");
    expect(ivs[0].end.toISOString()).toBe("2026-09-19T08:00:40.000Z");
  });

  it("离场穿越点在主跑道之前，应按 taxi_seconds 回推", () => {
    const f = dep({
      runway_id: "09R",
      route: [
        {
          name: "穿越18",
          type: "runway",
          runway_id: "18",
          crossing_duration: 30,
          taxi_seconds: 40,
        },
        {
          name: "RWY09R",
          type: "runway",
          runway_id: "09R",
          primary: true,
        },
      ],
    });
    const ivs = runwayIntervals(f);
    const cross = ivs.find((i) => i.role === "cross")!;
    // 主跑道锚定 08:00，穿越点在其前一个节点：回推 40s
    expect(cross.start.toISOString()).toBe("2026-09-19T07:59:20.000Z");
    expect(cross.end.toISOString()).toBe("2026-09-19T07:59:50.000Z");
  });

  it("进场以落地时刻为基准", () => {
    const f: Flight = {
      ...dep(),
      id: "A1",
      operation: "arrival",
      runway_id: "18",
      takeoff_time: null,
      landing_time: "2026-09-19T09:10:00Z",
    };
    expect(baseTime(f).toISOString()).toBe("2026-09-19T09:10:00.000Z");
    const ivs = runwayIntervals(f);
    expect(ivs[0].runwayId).toBe("18");
  });
});
