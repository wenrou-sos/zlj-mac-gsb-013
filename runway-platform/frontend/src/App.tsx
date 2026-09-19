import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./lib/api";
import type {
  AnalyzeResult,
  AutoResolveResult,
  Closure,
  Conflict,
  Flight,
  Resolution,
  Runway,
  SeparationMatrix,
} from "./lib/types";
import { Timeline } from "./components/Timeline";
import { FlightList } from "./components/FlightList";
import { FlightForm } from "./components/FlightForm";
import { ClosurePanel } from "./components/ClosurePanel";
import { ConflictPanel } from "./components/ConflictPanel";
import { SeparationEditor } from "./components/SeparationEditor";
import { fmtDuration } from "./lib/time";

const EMPTY_ANALYSIS: AnalyzeResult = { conflicts: [], resolutions: [] };

export default function App() {
  const [runways, setRunways] = useState<Runway[]>([]);
  const [flights, setFlights] = useState<Flight[]>([]);
  const [closures, setClosures] = useState<Closure[]>([]);
  const [matrix, setMatrix] = useState<SeparationMatrix | null>(null);
  const [analysis, setAnalysis] = useState<AnalyzeResult>(EMPTY_ANALYSIS);
  const [editing, setEditing] = useState<Flight | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [adjusted, setAdjusted] = useState<Record<string, number>>({});
  const [autoPlan, setAutoPlan] = useState<AutoResolveResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const refreshAll = useCallback(async () => {
    const [rw, fl, cl, sp] = await Promise.all([
      api.listRunways(),
      api.listFlights(),
      api.listClosures(),
      api.getSeparation(),
    ]);
    setRunways(rw);
    setFlights(fl);
    setClosures(cl);
    setMatrix(sp.matrix);
  }, []);

  const runAnalysis = useCallback(async () => {
    try {
      const result = await api.analyze();
      setAnalysis(result);
      return result;
    } catch (e) {
      setError((e as Error).message);
      return EMPTY_ANALYSIS;
    }
  }, []);

  useEffect(() => {
    refreshAll().catch((e) => setError(String(e)));
  }, [refreshAll]);

  useEffect(() => {
    if (runways.length) {
      runAnalysis();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flights, closures, matrix, runways]);

  const activeRunways = useMemo(
    () => runways.filter((r) => r.active),
    [runways]
  );

  const saveFlight = async (f: Flight) => {
    if (editing) {
      await api.updateFlight(editing.id, f);
    } else {
      await api.createFlight(f);
    }
    setEditing(null);
    setShowForm(false);
    setAdjusted({});
    setAutoPlan(null);
    await refreshAll();
  };

  const deleteFlight = async (id: string) => {
    await api.deleteFlight(id);
    await refreshAll();
  };

  const createClosure = async (c: Closure) => {
    await api.createClosure(c);
    await refreshAll();
  };

  const deleteClosure = async (id: string) => {
    await api.deleteClosure(id);
    await refreshAll();
  };

  const applyDelay = async (flightId: string, delta: number) => {
    const target = flights.find((f) => f.id === flightId);
    if (!target) return;
    const key =
      target.operation === "departure" ? "takeoff_time" : "landing_time";
    const updated: Flight = {
      ...target,
      [key]: new Date(
        new Date(target[key] as string).getTime() + delta * 1000
      ).toISOString(),
    };
    await api.updateFlight(flightId, updated);
    setAdjusted((m) => ({ ...m, [flightId]: (m[flightId] ?? 0) + delta }));
    await refreshAll();
  };

  const autoResolve = async () => {
    setBusy(true);
    try {
      const plan = await api.autoResolve();
      setAutoPlan(plan);
      // 将贪心排程结果写回数据库
      for (const f of plan.flights) {
        const original = flights.find((x) => x.id === f.id);
        if (
          original &&
          (original.takeoff_time !== f.takeoff_time ||
            original.landing_time !== f.landing_time)
        ) {
          await api.updateFlight(f.id, f);
        }
      }
      const delayMap: Record<string, number> = {};
      plan.adjustments.forEach((a) => (delayMap[a.flight_id] = a.delta_seconds));
      setAdjusted(delayMap);
      await refreshAll();
    } finally {
      setBusy(false);
    }
  };

  const conflicts: Conflict[] = analysis.conflicts;
  const resolutions: Resolution[] = analysis.resolutions;

  return (
    <div className="app">
      <header className="app-header">
        <h1>机场跑道占用冲突预演平台</h1>
        <div className="header-actions">
          <button
            className="primary"
            onClick={() => {
              setEditing(null);
              setShowForm((v) => !v);
            }}
          >
            {showForm ? "收起表单" : "+ 新增航班"}
          </button>
          <button onClick={() => runAnalysis()} disabled={busy}>
            重新预演
          </button>
          <button className="accent" onClick={autoResolve} disabled={busy}>
            {busy ? "排程中…" : "一键自动排程"}
          </button>
        </div>
      </header>

      {error && <div className="error banner">{error}</div>}

      {autoPlan && (
        <div
          className={`banner ${
            autoPlan.remaining_conflicts.length === 0 ? "ok" : "warn"
          }`}
        >
          自动排程完成：共调整 {autoPlan.adjustments.length} 架航班，
          累计延误 {fmtDuration(autoPlan.total_delay_seconds)}，
          剩余冲突 {autoPlan.remaining_conflicts.length} 项
        </div>
      )}

      {showForm && (
        <FlightForm
          runways={activeRunways}
          initial={editing}
          onSubmit={saveFlight}
          onCancel={() => {
            setShowForm(false);
            setEditing(null);
          }}
        />
      )}

      <section className="timeline-section panel">
        <h3>跑道占用时间轴（UTC）</h3>
        <Timeline
          flights={flights}
          closures={closures}
          conflicts={conflicts}
          runways={activeRunways}
        />
      </section>

      <div className="grid-main">
        <div className="col-left">
          <FlightList
            flights={flights}
            adjusted={adjusted}
            onEdit={(f) => {
              setEditing(f);
              setShowForm(true);
            }}
            onDelete={deleteFlight}
          />
          {matrix && (
            <SeparationEditor
              matrix={matrix}
              onSave={async (m) => {
                await api.updateSeparation(m);
                await refreshAll();
              }}
            />
          )}
        </div>
        <div className="col-right">
          <ConflictPanel
            conflicts={conflicts}
            resolutions={resolutions}
            onApplyDelay={applyDelay}
          />
          <ClosurePanel
            closures={closures}
            runways={activeRunways}
            onCreate={createClosure}
            onDelete={deleteClosure}
          />
        </div>
      </div>

      <footer className="app-footer">
        冲突类型：SEPARATION 安全间隔 · OCCUPANCY 占用重叠 · CROSSING
        滑行穿越 · CLOSURE 关闭区间
      </footer>
    </div>
  );
}
