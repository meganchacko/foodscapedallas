import { useEffect, useState } from 'react'
import './App.css'

// Matches HealthResponse in backend/app/schemas/health.py
type Status = 'ok' | 'error'

type Health = {
  api: Status
  db: Status
  cache: Status
}

function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [apiUnreachable, setApiUnreachable] = useState(false)

  useEffect(() => {
    // "/api" is forwarded to the backend by the Vite dev server proxy (see vite.config.ts)
    fetch('/api/health')
      // a 503 still has a JSON body saying which service is down, so parse it either way
      .then((response) => response.json())
      .then((data: Health) => setHealth(data))
      // the backend didn't answer at all (not running, or the proxy couldn't reach it)
      .catch(() => setApiUnreachable(true))
  }, [])

  return (
    <main className="app">
      <h1>FoodScape Dallas</h1>
      <h2>System status</h2>
      {apiUnreachable && <p className="error">API unreachable</p>}
      {!apiUnreachable && !health && <p>Checking...</p>}
      {health && (
        <ul className="status-list">
          <StatusRow label="API" status={health.api} />
          <StatusRow label="DB" status={health.db} />
          <StatusRow label="Cache" status={health.cache} />
        </ul>
      )}
    </main>
  )
}

function StatusRow({ label, status }: { label: string; status: Status }) {
  return (
    <li>
      <span>{label}</span>
      <span className={status}>{status}</span>
    </li>
  )
}

export default App
