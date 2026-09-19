import { useState } from "react";
import type { Flight, RouteStep, Runway } from "../lib/types";
import { localToUtcIso, toLocalInput } from "../lib/time";

interface Props {
  runways: Runway[];
  initial?: Flight | null;
  onSubmit: (f: Flight) => Promise<void>;
  onCancel?: () => void;
}

function blankFlight(runwayId: string): Flight {
  return {
    id: "",
    callsign: "",
    operation: "departure",
    runway_id: runwayId,
    takeoff_time: null,
    landing_time: null,
    enter_offset: 60,
    vacate_offset: 40,
    route: [],
    aircraft_category: "M",
  };
}

export function FlightForm({ runways, initial, onSubmit, onCancel }: Props) {
  const [form, setForm] = useState<Flight>(
    () => initial ?? blankFlight(runways[0]?.id ?? "09L")
  );
  const [error, setError] = useState("");

  const refKey =
    form.operation === "departure" ? "takeoff_time" : "landing_time";

  const update = (patch: Partial<Flight>) =>
    setForm((f) => ({ ...f, ...patch }));

  const updateStep = (idx: number, patch: Partial<RouteStep>) =>
    setForm((f) => ({
      ...f,
      route: f.route.map((s, i) => (i === idx ? { ...s, ...patch } : s)),
    }));

  const addStep = (type: "runway" | "taxiway") =>
    setForm((f) => ({
      ...f,
      route: [
        ...f.route,
        type === "taxiway"
          ? { name: "", type: "taxiway", taxi_seconds: 45 }
          : {
              name: "",
              type: "runway",
              runway_id: runways.find((r) => r.id !== f.runway_id)?.id ?? "",
              primary: false,
              crossing_duration: 30,
              taxi_seconds: 45,
            },
      ],
    }));

  const removeStep = (idx: number) =>
    setForm((f) => ({ ...f, route: f.route.filter((_, i) => i !== idx) }));

  const submit = async () => {
    setError("");
    const refIso = localToUtcIso(
      (document.getElementById("ref-time") as HTMLInputElement)?.value ?? ""
    );
    const payload: Flight = {
      ...form,
      takeoff_time:
        form.operation === "departure" ? refIso : form.takeoff_time ?? null,
      landing_time:
        form.operation === "arrival" ? refIso : form.landing_time ?? null,
    };
    if (!payload.id.trim() || !payload.callsign.trim()) {
      setError("航班号与呼号不能为空");
      return;
    }
    if (!refIso) {
      setError(
        form.operation === "departure"
          ? "请填写起飞时刻"
          : "请填写落地时刻"
      );
      return;
    }
    try {
      await onSubmit(payload);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <div className="panel form-panel" data-testid="flight-form">
      <h3>{initial ? `编辑航班 ${initial.id}` : "新增航班"}</h3>
      <div className="grid-2">
        <label>
          航班号
          <input
            value={form.id}
            disabled={!!initial}
            onChange={(e) => update({ id: e.target.value.toUpperCase() })}
          />
        </label>
        <label>
          呼号
          <input
            value={form.callsign}
            onChange={(e) =>
              update({ callsign: e.target.value.toUpperCase() })
            }
          />
        </label>
        <label>
          运行类型
          <select
            value={form.operation}
            onChange={(e) =>
              update({
                operation: e.target.value as Flight["operation"],
                takeoff_time: null,
                landing_time: null,
              })
            }
          >
            <option value="departure">离场</option>
            <option value="arrival">进场</option>
          </select>
        </label>
        <label>
          使用跑道
          <select
            value={form.runway_id}
            onChange={(e) => update({ runway_id: e.target.value })}
          >
            {runways.map((r) => (
              <option key={r.id} value={r.id}>
                {r.id}（{r.name}）
              </option>
            ))}
          </select>
        </label>
        <label>
          {form.operation === "departure" ? "起飞时刻 (UTC)" : "落地时刻 (UTC)"}
          <input
            id="ref-time"
            type="datetime-local"
            step={1}
            defaultValue={toLocalInput(form[refKey])}
          />
        </label>
        <label>
          机型类别
          <select
            value={form.aircraft_category}
            onChange={(e) =>
              update({ aircraft_category: e.target.value })
            }
          >
            <option value="H">重型 (H)</option>
            <option value="M">中型 (M)</option>
            <option value="L">轻型 (L)</option>
          </select>
        </label>
        <label>
          进入跑道提前量（秒）
          <input
            type="number"
            min={0}
            value={form.enter_offset}
            onChange={(e) => update({ enter_offset: Number(e.target.value) })}
          />
        </label>
        <label>
          脱离跑道延后量（秒）
          <input
            type="number"
            min={0}
            value={form.vacate_offset}
            onChange={(e) => update({ vacate_offset: Number(e.target.value) })}
          />
        </label>
      </div>

      <div className="route-editor">
        <div className="route-head">
          <h4>滑行路线</h4>
          <span>
            <button type="button" onClick={() => addStep("taxiway")}>
              + 滑行道节点
            </button>
            <button type="button" onClick={() => addStep("runway")}>
              + 穿越跑道节点
            </button>
          </span>
        </div>
        {form.route.length === 0 && (
          <p className="hint">
            未配置路线时按使用跑道的进入/脱离窗口计算；主跑道节点用于精确描述路线。
          </p>
        )}
        <ol className="route-list">
          {form.route.map((step, idx) => (
            <li key={idx} className={`route-step ${step.type}`}>
              <span className="step-idx">#{idx + 1}</span>
              <input
                placeholder="节点名称"
                value={step.name}
                onChange={(e) => updateStep(idx, { name: e.target.value })}
              />
              {step.type === "runway" ? (
                <>
                  <select
                    value={step.runway_id ?? ""}
                    onChange={(e) =>
                      updateStep(idx, { runway_id: e.target.value })
                    }
                  >
                    {runways.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.id}
                      </option>
                    ))}
                  </select>
                  <label className="inline">
                    <input
                      type="checkbox"
                      checked={!!step.primary}
                      onChange={(e) =>
                        updateStep(idx, { primary: e.target.checked })
                      }
                    />
                    主跑道
                  </label>
                  <input
                    type="number"
                    title="穿越时长（秒）"
                    placeholder="穿越秒"
                    value={step.crossing_duration ?? 30}
                    onChange={(e) =>
                      updateStep(idx, {
                        crossing_duration: Number(e.target.value),
                      })
                    }
                  />
                </>
              ) : (
                <span className="taxi-tag">滑行道</span>
              )}
              <input
                type="number"
                title="到下一节点滑行秒数"
                placeholder="滑行秒"
                value={step.taxi_seconds ?? 45}
                onChange={(e) =>
                  updateStep(idx, { taxi_seconds: Number(e.target.value) })
                }
              />
              <button
                type="button"
                className="danger"
                onClick={() => removeStep(idx)}
              >
                删除
              </button>
            </li>
          ))}
        </ol>
      </div>

      {error && <div className="error">{error}</div>}
      <div className="form-actions">
        <button type="button" className="primary" onClick={submit}>
          保存航班
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel}>
            取消
          </button>
        )}
      </div>
    </div>
  );
}
