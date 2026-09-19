import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import type {
  AnalyzeResult,
  Closure,
  Flight,
  Runway,
  SeparationMatrix,
} from "../lib/types";
import App from "../App";

const runways: Runway[] = [
  { id: "09L", name: "09 左", active: true },
  { id: "09R", name: "09 右", active: true },
];

const flights: Flight[] = [
  {
    id: "CA1",
    callsign: "CCA001",
    operation: "departure",
    runway_id: "09L",
    takeoff_time: "2026-09-19T08:00:00Z",
    enter_offset: 60,
    vacate_offset: 40,
    route: [],
  },
  {
    id: "CA2",
    callsign: "CCA002",
    operation: "departure",
    runway_id: "09L",
    takeoff_time: "2026-09-19T08:01:00Z",
    enter_offset: 60,
    vacate_offset: 40,
    route: [],
  },
];

const closures: Closure[] = [];
const matrix: SeparationMatrix = {
  departure: { departure: 120, arrival: 90 },
  arrival: { departure: 90, arrival: 100 },
};

const analysis: AnalyzeResult = {
  conflicts: [
    {
      id: "SEPARATION:CA1:CA2",
      type: "SEPARATION",
      runway_id: "09L",
      flight_ids: ["CA1", "CA2"],
      message: "间隔 60s < 规定 120s",
      time: "2026-09-19T08:01:00Z",
      severity: "high",
      actual_gap_seconds: 60,
      required_gap_seconds: 120,
    },
  ],
  resolutions: [
    {
      flight_id: "CA2",
      callsign: "CCA002",
      conflict_ids: ["SEPARATION:CA1:CA2"],
      options: [
        { kind: "DELAY", delta_seconds: 60, description: "顺延 1 分钟" },
      ],
    },
  ],
};

function jsonOk(data: unknown) {
  return {
    ok: true,
    status: 200,
    headers: new Headers({ "Content-Type": "application/json" }),
    json: async () => data,
    text: async () => JSON.stringify(data),
  };
}

describe("App 集成渲染", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        const method = init?.method ?? "GET";
        if (url.endsWith("/api/runways") && method === "GET")
          return jsonOk(runways);
        if (url.endsWith("/api/flights") && method === "GET")
          return jsonOk(flights);
        if (url.endsWith("/api/closures") && method === "GET")
          return jsonOk(closures);
        if (url.endsWith("/api/separation") && method === "GET")
          return jsonOk({ matrix });
        if (url.endsWith("/api/analyze") && method === "POST")
          return jsonOk(analysis);
        if (url.endsWith("/api/auto-resolve") && method === "POST")
          return jsonOk({
            flights,
            adjustments: [],
            total_delay_seconds: 0,
            remaining_conflicts: [],
          });
        return jsonOk({});
      })
    );
  });

  it("加载航班并渲染冲突与时间轴", async () => {
    render(<App />);

    expect((await screen.findAllByText("CCA001")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("CCA002").length).toBeGreaterThan(0);
    expect(await screen.findByTestId("conflict-count")).toHaveTextContent("1");
    expect(screen.getByText("安全间隔不足")).toBeInTheDocument();
    expect(screen.getByText(/间隔 60s/)).toBeInTheDocument();
    expect(screen.getByTestId("timeline")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /顺延 1 分钟/ })
    ).toBeInTheDocument();
  });

  it("可以打开新增航班表单", async () => {
    render(<App />);
    const open = await screen.findByRole("button", { name: "+ 新增航班" });
    open.click();
    expect(await screen.findByTestId("flight-form")).toBeInTheDocument();
  });
});
