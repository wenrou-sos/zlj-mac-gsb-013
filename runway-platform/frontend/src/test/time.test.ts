import { describe, expect, it } from "vitest";
import {
  fmtClock,
  fmtDuration,
  localToUtcIso,
  secondsOfDay,
  toLocalInput,
} from "../lib/time";

describe("time utils", () => {
  it("formats UTC clock", () => {
    expect(fmtClock("2026-09-19T08:05:20Z")).toBe("08:05:20Z");
    expect(fmtClock(null)).toBe("—");
  });

  it("converts duration in seconds to Chinese text", () => {
    expect(fmtDuration(90)).toBe("1 分 30 秒");
    expect(fmtDuration(120)).toBe("2 分钟");
  });

  it("round-trips through datetime-local input format", () => {
    const iso = "2026-09-19T08:00:00Z";
    const local = toLocalInput(iso);
    expect(local).toBeTruthy();
    expect(localToUtcIso(local)).toBe(iso);
  });

  it("returns null for invalid local input", () => {
    expect(localToUtcIso("")).toBeNull();
    expect(localToUtcIso("not-a-date")).toBeNull();
  });

  it("computes seconds of day", () => {
    expect(secondsOfDay("2026-09-19T01:02:03Z")).toBe(3723);
  });
});
