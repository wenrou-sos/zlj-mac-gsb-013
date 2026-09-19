import { useEffect, useState } from "react";
import type { SeparationMatrix } from "../lib/types";

interface Props {
  matrix: SeparationMatrix;
  onSave: (m: SeparationMatrix) => Promise<void>;
}

const OPS: { key: "departure" | "arrival"; label: string }[] = [
  { key: "departure", label: "离场" },
  { key: "arrival", label: "进场" },
];

export function SeparationEditor({ matrix, onSave }: Props) {
  const [draft, setDraft] = useState<SeparationMatrix>(matrix);
  const [saved, setSaved] = useState(false);

  useEffect(() => setDraft(matrix), [matrix]);

  const update = (
    leader: "departure" | "arrival",
    follower: "departure" | "arrival",
    value: number
  ) =>
    setDraft((m) => ({
      ...m,
      [leader]: { ...m[leader], [follower]: value },
    }));

  return (
    <div className="panel">
      <h3>安全间隔矩阵（秒）</h3>
      <p className="sub">行 = 前机运行类型，列 = 后机运行类型。</p>
      <table className="sep-table">
        <thead>
          <tr>
            <th>前机 \ 后机</th>
            {OPS.map((o) => (
              <th key={o.key}>{o.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {OPS.map((leader) => (
            <tr key={leader.key}>
              <th>{leader.label}</th>
              {OPS.map((follower) => (
                <td key={follower.key}>
                  <input
                    type="number"
                    min={0}
                    step={5}
                    value={draft[leader.key]?.[follower.key] ?? 90}
                    onChange={(e) =>
                      update(
                        leader.key,
                        follower.key,
                        Number(e.target.value)
                      )
                    }
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <button
        className="primary"
        onClick={async () => {
          await onSave(draft);
          setSaved(true);
          setTimeout(() => setSaved(false), 1500);
        }}
      >
        {saved ? "✓ 已保存" : "保存间隔配置"}
      </button>
    </div>
  );
}
