import React from 'react'

export default function Sidebar({ onAnalyze, loading, sensors, setSensors, aoi, setAoi }) {
  const aois = [
    { name: 'Nagpur-Balaghat Belt', lat: 21.5, lon: 79.5 },
    { name: 'Dharwar Belt (Karnataka)', lat: 15.3, lon: 75.7 },
    { name: 'Iron Ore Group (Odisha)', lat: 22.0, lon: 85.5 },
    { name: 'Singhbhum Belt (Jharkhand)', lat: 22.4, lon: 86.2 },
  ]

  const sensorList = [
    { id: 'sentinel2', label: 'Sentinel-2 (Optical/SWIR)', icon: '🌍' },
    { id: 'aster', label: 'ASTER (Thermal IR)', icon: '🔥' },
    { id: 'sar', label: 'Sentinel-1 SAR (Radar)', icon: '📡' },
    { id: 'dem', label: 'Cartosat DEM (Elevation)', icon: '⛰️' },
  ]

  const toggleSensor = (id) => {
    setSensors(prev =>
      prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]
    )
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-section">
        <h3>🗺️ Area of Interest</h3>
        <select
          value={aoi.name}
          onChange={(e) => {
            const selected = aois.find(a => a.name === e.target.value)
            if (selected) setAoi(selected)
          }}
        >
          {aois.map(a => (
            <option key={a.name} value={a.name}>{a.name}</option>
          ))}
        </select>
        <div style={{ marginTop: 10, fontSize: 12, color: 'var(--text-secondary)' }}>
          📍 Center: {aoi.lat}°N, {aoi.lon}°E
        </div>
      </div>

      <div className="sidebar-section">
        <h3>📡 Sensor Selection</h3>
        <div className="checkbox-group">
          {sensorList.map(s => (
            <label key={s.id}>
              <input
                type="checkbox"
                checked={sensors.includes(s.id)}
                onChange={() => toggleSensor(s.id)}
              />
              {s.icon} {s.label}
            </label>
          ))}
        </div>
      </div>

      <div className="sidebar-section">
        <h3>⚙️ Parameters</h3>
        <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
          Analysis Radius (km)
        </label>
        <input type="number" defaultValue={30} min={5} max={200} />
        <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginTop: 12, marginBottom: 6 }}>
          MPI Threshold
        </label>
        <input type="number" defaultValue={0.7} min={0} max={1} step={0.05} />
      </div>

      <button
        className="btn-analyze"
        onClick={onAnalyze}
        disabled={loading || sensors.length === 0}
      >
        {loading ? '⏳ Processing...' : '🚀 Run AI Analysis'}
      </button>

      <div style={{ fontSize: 11, color: 'var(--text-secondary)', textAlign: 'center', lineHeight: 1.5 }}>
        Powered by XGBoost + CNN + SHAP<br />
        Ministry of Steel, Govt. of India
      </div>
    </aside>
  )
}
