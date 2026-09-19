import { StoreProvider, useStore } from './store'
import Toolbar from './components/Toolbar'
import Timeline from './components/Timeline'
import ConflictList from './components/ConflictList'
import FlightPanel from './components/FlightPanel'
import ClosurePanel from './components/ClosurePanel'
import ConfigPanel from './components/ConfigPanel'

function Dashboard() {
  const { rehearsal, loading, error } = useStore()

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>机场跑道占用冲突预演平台</h1>
          <p className="subtitle">
            配置进离场时刻 · 滑行路线 · 跑道关闭区间 · 安全间隔，自动识别冲突并给出调整方案
          </p>
        </div>
        <div className={`health ${loading ? 'loading' : ''}`}>
          <span className="dot" /> {loading ? '演算中' : '引擎就绪'}
        </div>
      </header>

      {error && <div className="toast-error">{error}</div>}

      <Toolbar />

      <section className="panel">
        <h2>跑道占用时间线</h2>
        {rehearsal && (
          <Timeline
            windows={rehearsal.windows}
            closures={rehearsal.closures}
            conflicts={rehearsal.conflicts}
          />
        )}
      </section>

      <div className="grid-two">
        <ConflictList />
        <ConfigPanel />
      </div>

      <FlightPanel />
      <ClosurePanel />

      <footer className="app-footer">
        Runway Conflict Rehearsal · React + FastAPI + PostgreSQL
      </footer>
    </div>
  )
}

export default function App() {
  return (
    <StoreProvider>
      <Dashboard />
    </StoreProvider>
  )
}
