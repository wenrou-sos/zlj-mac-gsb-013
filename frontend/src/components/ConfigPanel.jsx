import { useEffect, useState } from 'react'
import { api } from '../api'
import { useStore } from '../store'

const WAKE_PAIRS = ['LL', 'LM', 'LH', 'ML', 'MM', 'MH', 'HL', 'HM', 'HH']

export default function ConfigPanel() {
  const { config, refresh, flash } = useStore()
  const [local, setLocal] = useState(null)
  const [savedAt, setSavedAt] = useState('')

  useEffect(() => {
    if (config) setLocal(structuredClone(config))
  }, [config])

  if (!local) return null

  const setNum = (k) => (e) => setLocal({ ...local, [k]: Number(e.target.value) })
  const setWake = (k) => (e) =>
    setLocal({ ...local, wake_sep: { ...local.wake_sep, [k]: Number(e.target.value) } })

  const save = async () => {
    try {
      await api.updateConfig({
        dep_occupy: local.dep_occupy,
        arr_occupy: local.arr_occupy,
        min_sep: local.min_sep,
        max_delay: local.max_delay,
        wake_sep: local.wake_sep,
      })
      setSavedAt(new Date().toLocaleTimeString())
      await refresh()
    } catch (e) {
      flash(e.message)
    }
  }

  return (
    <div className="panel">
      <h2>
        安全间隔参数
        {savedAt && <span className="saved-hint">已保存 {savedAt}</span>}
      </h2>
      <div className="form-grid compact">
        <label>
          离港跑道占用（秒）
          <input type="number" min="10" max="900" value={local.dep_occupy}
                 onChange={setNum('dep_occupy')} />
        </label>
        <label>
          进港跑道占用（秒）
          <input type="number" min="10" max="900" value={local.arr_occupy}
                 onChange={setNum('arr_occupy')} />
        </label>
        <label>
          基础跑道间隔（秒）
          <input type="number" min="0" max="900" value={local.min_sep}
                 onChange={setNum('min_sep')} />
        </label>
        <label>
          自动调整最大延误（秒）
          <input type="number" min="30" max="14400" value={local.max_delay}
                 onChange={setNum('max_delay')} />
        </label>
      </div>

      <h3>尾流追加间隔（秒，前行×后随：L/M/H）</h3>
      <div className="wake-grid">
        {WAKE_PAIRS.map((p) => (
          <label key={p}>
            <span className="mono">{p[0]}→{p[1]}</span>
            <input type="number" min="0" max="600"
                   value={local.wake_sep[p] ?? 0}
                   onChange={setWake(p)} />
          </label>
        ))}
      </div>
      <button className="btn primary" onClick={save}>保存参数并重演</button>
    </div>
  )
}
