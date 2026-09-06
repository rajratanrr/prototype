import React from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

export default function ResultsPanel({ results, jobId }) {
  if (!results) {
    return (
      <aside className="results-panel">
        <div className="empty-state">
          <div className="icon">📊</div>
          <h3>No Analysis Yet</h3>
          <p>Select an area of interest, choose sensors, and click "Run AI Analysis" to see results here.</p>
        </div>
      </aside>
    )
  }

  const shapData = Object.entries(results.shap_importance)
    .map(([name, value]) => ({ name: name.replace(/_/g, ' '), value: parseFloat(value.toFixed(4)) }))
    .sort((a, b) => b.value - a.value)

  const colors = ['#1b9aaa', '#2ecc71', '#d4a843', '#e74c3c', '#9b59b6', '#3498db', '#e67e22', '#1abc9c']

  const downloadFile = async (fmt) => {
    try {
      const res = await fetch(`/api/download/${jobId}/${fmt}`)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `geomines_${fmt}_${jobId}.${fmt}`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      console.error('Download failed:', e)
    }
  }

  return (
    <aside className="results-panel">
      <h2>📊 Analysis Results</h2>

      {/* Stats Grid */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="value">{results.total_area_sq_km.toFixed(0)}</div>
          <div className="label">Area (sq km)</div>
        </div>
        <div className="stat-card">
          <div className="value">{results.high_mpi_area_percent.toFixed(1)}%</div>
          <div className="label">High MPI Area</div>
        </div>
        <div className="stat-card">
          <div className="value" style={{ color: '#e74c3c' }}>{results.num_drill_targets}</div>
          <div className="label">Drill Targets</div>
        </div>
        <div className="stat-card">
          <div className="value" style={{ color: '#2ecc71' }}>
            {results.drill_targets[0]?.mpi_score.toFixed(2) || '—'}
          </div>
          <div className="label">Top MPI Score</div>
        </div>
      </div>

      {/* SHAP Chart */}
      <div className="shap-container">
        <h3>🧠 SHAP Feature Importance</h3>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={shapData} layout="vertical" margin={{ left: 5, right: 15 }}>
            <XAxis type="number" tick={{ fill: '#8899a6', fontSize: 10 }} />
            <YAxis type="category" dataKey="name" width={90} tick={{ fill: '#e0e6ed', fontSize: 10 }} />
            <Tooltip
              contentStyle={{ background: '#1b2838', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 12 }}
              labelStyle={{ color: '#e0e6ed' }}
            />
            <Bar dataKey="value" radius={[0, 4, 4, 0]}>
              {shapData.map((_, i) => (
                <Cell key={i} fill={colors[i % colors.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Drill Targets */}
      <h2 style={{ marginTop: 4 }}>📍 Top Drill Targets</h2>
      <div className="targets-list">
        {results.drill_targets.slice(0, 8).map(t => (
          <div key={t.rank} className="target-item">
            <div className="target-rank">{t.rank}</div>
            <div className="target-info">
              <div className="coords">{t.latitude}°N, {t.longitude}°E</div>
              <div className="factor">{t.top_shap_factor}</div>
            </div>
            <div className="target-score">{t.mpi_score.toFixed(2)}</div>
          </div>
        ))}
      </div>

      {/* Downloads */}
      <h2 style={{ marginTop: 4 }}>📥 Download Results</h2>
      <div className="download-group">
        <button className="btn-download" onClick={() => downloadFile('csv')}>📄 CSV Targets</button>
        <button className="btn-download" onClick={() => downloadFile('kml')}>🌍 KML (Google Earth)</button>
        <button className="btn-download" onClick={() => downloadFile('json')}>📋 JSON Data</button>
        <button className="btn-download" onClick={() => window.print()}>🖨️ Print Report</button>
      </div>
    </aside>
  )
}
