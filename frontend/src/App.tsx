import React, { useEffect, useMemo, useState } from 'react'
import axios from 'axios'

interface SSLInfo {
  valid: boolean
  issuer?: string
  expires?: string
  days_remaining?: number
  hostname_matches?: boolean
}

interface DNSRecords {
  A: string[]
  AAAA: string[]
  CNAME: string[]
  MX: string[]
  NS: string[]
}

interface CheckResult {
  status_code?: number
  status_text: string
  response_time_ms?: number
  final_url?: string
  redirect_chain: string[]
  ssl?: SSLInfo | null
  dns?: DNSRecords | null
  timestamp: string
}

interface MonitoredURL {
  url: string
  last_status?: string
  last_response_time?: number
  uptime_percentage?: number
}

interface HistoryResponse {
  url: string
  checks: CheckResult[]
}

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
})

const formatDate = (value?: string) => (value ? new Date(value).toLocaleString() : 'N/A')

const Sparkline: React.FC<{ values: number[] }> = ({ values }) => {
  if (!values.length) return <span className="text-sm text-gray-500">No data</span>
  const width = 160
  const height = 60
  const max = Math.max(...values)
  const min = Math.min(...values)
  const scale = max === min ? 1 : max - min
  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1 || 1)) * width
      const y = height - ((v - min) / scale) * height
      return `${x},${y}`
    })
    .join(' ')
  return (
    <svg width={width} height={height} className="text-blue-400">
      <polyline points={points} fill="none" stroke="currentColor" strokeWidth="2" />
    </svg>
  )
}

const App: React.FC = () => {
  const [url, setUrl] = useState('https://example.com')
  const [result, setResult] = useState<CheckResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [monitored, setMonitored] = useState<MonitoredURL[]>([])
  const [history, setHistory] = useState<HistoryResponse | null>(null)
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    return (localStorage.getItem('theme') as 'light' | 'dark') || 'dark'
  })

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    localStorage.setItem('theme', theme)
  }, [theme])

  const fetchMonitored = async () => {
    const { data } = await api.get<MonitoredURL[]>('/monitor/list')
    setMonitored(data)
  }

  const runCheck = async () => {
    try {
      setError(null)
      setLoading(true)
      const { data } = await api.get<CheckResult>('/check', { params: { url } })
      setResult(data)
    } catch (err) {
      setError('Unable to reach backend or invalid URL')
    } finally {
      setLoading(false)
    }
  }

  const addMonitor = async () => {
    try {
      await api.post('/monitor/add', null, { params: { url } })
      await fetchMonitored()
    } catch {
      setError('Failed to add URL to monitor')
    }
  }

  const removeMonitor = async (target: string) => {
    await api.delete('/monitor/remove', { params: { url: target } })
    await fetchMonitored()
  }

  const fetchHistory = async (target: string) => {
    const { data } = await api.get<HistoryResponse>('/monitor/history', { params: { url: target } })
    setHistory(data)
  }

  useEffect(() => {
    fetchMonitored().catch(() => setMonitored([]))
  }, [])

  const uptimeEvents = useMemo(() => {
    if (!history) return []
    const events: { status: string; timestamp: string }[] = []
    history.checks.forEach((check, idx) => {
      if (idx === 0 || history.checks[idx - 1].status_text !== check.status_text) {
        events.push({ status: check.status_text, timestamp: check.timestamp })
      }
    })
    return events
  }, [history])

  return (
    <div className={`min-h-screen ${theme === 'dark' ? 'bg-gray-900 text-gray-100' : 'bg-gray-100 text-gray-900'}`}>
      <div className="max-w-6xl mx-auto p-6 space-y-6">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Website Uptime Checker</h1>
            <p className="text-sm text-gray-400">Check status, SSL, DNS, and track uptime.</p>
          </div>
          <button
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            className="px-3 py-2 rounded-md border border-gray-600 hover:border-blue-400 transition"
          >
            Toggle {theme === 'dark' ? 'Light' : 'Dark'}
          </button>
        </header>

        <section className="bg-gray-800/60 dark:bg-gray-800 rounded-xl p-6 shadow">
          <div className="flex flex-col md:flex-row md:items-end gap-4">
            <div className="flex-1">
              <label className="block text-sm mb-1">Website URL</label>
              <input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                className="w-full px-4 py-2 rounded-md bg-gray-900 border border-gray-700"
                placeholder="https://example.com"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={runCheck}
                className="px-4 py-2 rounded-md bg-blue-600 hover:bg-blue-500 text-white"
                disabled={loading}
              >
                {loading ? 'Checking...' : 'Check Uptime Now'}
              </button>
              <button
                onClick={addMonitor}
                className="px-4 py-2 rounded-md bg-emerald-600 hover:bg-emerald-500 text-white"
              >
                Add to Monitor
              </button>
            </div>
          </div>
          {error && <p className="text-red-400 mt-3">{error}</p>}
        </section>

        {result && (
          <section className="grid md:grid-cols-2 gap-4">
            <div className="bg-gray-800 rounded-xl p-4 space-y-2">
              <h2 className="text-xl font-semibold">HTTP & Timing</h2>
              <p>Status: <span className="font-mono">{result.status_text}</span> ({result.status_code ?? 'n/a'})</p>
              <p>Response: {result.response_time_ms} ms</p>
              <p>Final URL: {result.final_url}</p>
              <p>Timestamp: {formatDate(result.timestamp)}</p>
              <div>
                <h3 className="font-semibold">Redirects</h3>
                <ul className="list-disc ml-5 text-sm text-gray-300">
                  {result.redirect_chain.map((r) => (<li key={r}>{r}</li>))}
                </ul>
              </div>
            </div>
            <div className="bg-gray-800 rounded-xl p-4 space-y-2">
              <h2 className="text-xl font-semibold">SSL</h2>
              {result.ssl ? (
                <>
                  <p>Valid: {result.ssl.valid ? 'Yes' : 'No'}</p>
                  <p>Issuer: {result.ssl.issuer ?? 'Unknown'}</p>
                  <p>Expires: {formatDate(result.ssl.expires)}</p>
                  <p>Days remaining: {result.ssl.days_remaining ?? 'n/a'}</p>
                  <p>Hostname matches: {String(result.ssl.hostname_matches)}</p>
                </>
              ) : (
                <p>No SSL data</p>
              )}
              <div>
                <h2 className="text-xl font-semibold mt-2">DNS</h2>
                {result.dns ? (
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    {Object.entries(result.dns).map(([key, values]) => (
                      <div key={key}>
                        <p className="font-semibold">{key}</p>
                        <ul className="text-gray-300 list-disc ml-4">
                          {(values as string[]).length ? (values as string[]).map((v) => <li key={v}>{v}</li>) : <li>None</li>}
                        </ul>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p>No DNS data</p>
                )}
              </div>
            </div>
          </section>
        )}

        <section className="bg-gray-800 rounded-xl p-4 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">Monitoring</h2>
            <button onClick={fetchMonitored} className="text-sm px-3 py-1 border border-gray-600 rounded">Refresh</button>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-gray-400">
                  <th className="py-2">Domain</th>
                  <th>Last Status</th>
                  <th>Response</th>
                  <th>Uptime %</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {monitored.map((item) => (
                  <tr key={item.url} className="border-t border-gray-700">
                    <td className="py-2">{item.url}</td>
                    <td>{item.last_status ?? '-'}</td>
                    <td>{item.last_response_time ?? '-'} ms</td>
                    <td>{item.uptime_percentage ?? '-'}%</td>
                    <td className="space-x-2 text-right">
                      <button className="text-blue-400" onClick={() => fetchHistory(item.url)}>View</button>
                      <button className="text-red-400" onClick={() => removeMonitor(item.url)}>Remove</button>
                    </td>
                  </tr>
                ))}
                {!monitored.length && (
                  <tr>
                    <td colSpan={5} className="py-4 text-center text-gray-500">No monitored URLs yet</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {history && (
            <div className="bg-gray-900 rounded-lg p-4 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold">History for {history.url}</h3>
                  <p className="text-gray-400 text-sm">Last {history.checks.length} checks</p>
                </div>
                <Sparkline values={history.checks.map((c) => c.response_time_ms || 0)} />
              </div>
              <div className="grid md:grid-cols-2 gap-3">
                <div>
                  <h4 className="font-semibold">Events</h4>
                  <ul className="text-sm text-gray-300 list-disc ml-4">
                    {uptimeEvents.map((event) => (
                      <li key={event.timestamp}>{event.status} at {formatDate(event.timestamp)}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h4 className="font-semibold">Recent Checks</h4>
                  <ul className="text-sm text-gray-300 space-y-1">
                    {history.checks.map((check) => (
                      <li key={check.timestamp} className="flex justify-between border-b border-gray-800 pb-1">
                        <span>{formatDate(check.timestamp)}</span>
                        <span className="font-mono">{check.status_text}</span>
                        <span>{check.response_time_ms} ms</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

export default App
