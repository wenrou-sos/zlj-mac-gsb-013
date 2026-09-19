import { useState } from "react";
import type { Closure, Runway } from "../lib/types";
import { fmtClock, localToUtcIso } from "../lib/time";

interface Props {
  closures: Closure[];
  runways: Runway[];
  onCreate: (c: Closure) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}

export function ClosurePanel({ closures, runways, onCreate, onDelete }: Props) {
  const [id, setId] = useState("");
  const [runwayId, setRunwayId] = useState(runways[0]?.id ?? "09L");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");

  const submit = async () => {
    setError("");
    const s = localToUtcIso(start);
    const e = localToUtcIso(end);
    if (!id.trim() || !s || !e) {
      setError("请填写编号与起止时间");
      return;
    }
    if (new Date(e) <= new Date(s)) {
      setError("结束时间必须晚于开始时间");
      return;
    }
    try {
      await onCreate({
        id: id.trim().toUpperCase(),
        runway_id: runwayId,
        start_time: s,
        end_time: e,
        reason,
      });
      setId("");
      setReason("");
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div className="panel">
      <h3>
        跑道关闭区间
        <span className="badge">{closures.length}</span>
      </h3>
      <ul className="closure-list">
        {closures.map((c) => (
          <li key={c.id}>
            <div>
              <strong>{c.id}</strong> · 跑道 {c.runway_id}
              {c.reason ? ` · ${c.reason}` : ""}
            </div>
            <div className="sub">
              {fmtClock(c.start_time)} ~ {fmtClock(c.end_time)}
            </div>
            <button className="danger small" onClick={() => onDelete(c.id)}>
              删除
            </button>
          </li>
        ))}
        {closures.length === 0 && (
          <li className="empty-hint">暂无关闭区间</li>
        )}
      </ul>

      <div className="closure-form">
        <div className="grid-2">
          <label>
            编号
            <input value={id} onChange={(e) => setId(e.target.value)} />
          </label>
          <label>
            跑道
            <select
              value={runwayId}
              onChange={(e) => setRunwayId(e.target.value)}
            >
              {runways.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.id}
                </option>
              ))}
            </select>
          </label>
          <label>
            开始 (UTC)
            <input
              type="datetime-local"
              step={1}
              value={start}
              onChange={(e) => setStart(e.target.value)}
            />
          </label>
          <label>
            结束 (UTC)
            <input
              type="datetime-local"
              step={1}
              value={end}
              onChange={(e) => setEnd(e.target.value)}
            />
          </label>
          <label className="span-2">
            原因
            <input
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </label>
        </div>
        {error && <div className="error">{error}</div>}
        <button className="primary" onClick={submit}>
          添加关闭区间
        </button>
      </div>
    </div>
  );
}
