import React, { useEffect, useRef } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Rectangle, useMap } from 'react-leaflet'
import L from 'leaflet'

// Fix Leaflet default icon issue with bundlers
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

// Custom drill target icon
const drillIcon = new L.DivIcon({
  className: '',
  html: `<div style="
    width:24px;height:24px;border-radius:50%;
    background:linear-gradient(135deg,#e74c3c,#c0392b);
    border:2px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.5);
    display:flex;align-items:center;justify-content:center;
    font-size:12px;color:white;font-weight:bold;
  ">📍</div>`,
  iconSize: [24, 24],
  iconAnchor: [12, 12],
})

// Known mine icon
const mineIcon = new L.DivIcon({
  className: '',
  html: `<div style="
    width:20px;height:20px;border-radius:50%;
    background:linear-gradient(135deg,#d4a843,#b8902e);
    border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.4);
    display:flex;align-items:center;justify-content:center;
    font-size:10px;
  ">⛏</div>`,
  iconSize: [20, 20],
  iconAnchor: [10, 10],
})

// Component to render heatmap overlay using canvas
function HeatmapOverlay({ data, bounds }) {
  const map = useMap()
  const overlayRef = useRef(null)

  useEffect(() => {
    if (!data || data.length === 0) return

    // Remove previous overlay
    if (overlayRef.current) {
      map.removeLayer(overlayRef.current)
    }

    // Create canvas for heatmap
    const canvas = document.createElement('canvas')
    const rows = data.length
    const cols = data[0].length
    canvas.width = cols
    canvas.height = rows
    const ctx = canvas.getContext('2d')

    // Draw pixels
    const imgData = ctx.createImageData(cols, rows)
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const val = data[r][c]
        const idx = (r * cols + c) * 4

        // Color map: green → yellow → red
        if (val < 0.3) {
          imgData.data[idx] = 0
          imgData.data[idx + 1] = Math.floor(val / 0.3 * 200)
          imgData.data[idx + 2] = 0
          imgData.data[idx + 3] = Math.floor(val * 300)
        } else if (val < 0.6) {
          const t = (val - 0.3) / 0.3
          imgData.data[idx] = Math.floor(t * 255)
          imgData.data[idx + 1] = 200
          imgData.data[idx + 2] = 0
          imgData.data[idx + 3] = Math.floor(val * 280)
        } else {
          const t = (val - 0.6) / 0.4
          imgData.data[idx] = 255
          imgData.data[idx + 1] = Math.floor((1 - t) * 150)
          imgData.data[idx + 2] = 0
          imgData.data[idx + 3] = Math.floor(120 + val * 120)
        }
      }
    }
    ctx.putImageData(imgData, 0, 0)

    // Create image overlay
    const imageBounds = [
      [bounds.min_lat, bounds.min_lon],
      [bounds.max_lat, bounds.max_lon]
    ]
    const overlay = L.imageOverlay(canvas.toDataURL(), imageBounds, { opacity: 0.65 })
    overlay.addTo(map)
    overlayRef.current = overlay

    // Fit map to bounds
    map.fitBounds(imageBounds, { padding: [20, 20] })

    return () => {
      if (overlayRef.current) map.removeLayer(overlayRef.current)
    }
  }, [data, bounds, map])

  return null
}

export default function MapView({ results, mines }) {
  const center = [21.5, 79.5]
  const hasResults = results && results.mpi_heatmap_data

  return (
    <div className="map-container">
      <MapContainer
        center={center}
        zoom={7}
        style={{ height: '100%', width: '100%' }}
        zoomControl={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://carto.com">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />

        {/* MPI Heatmap overlay */}
        {hasResults && (
          <HeatmapOverlay
            data={results.mpi_heatmap_data}
            bounds={results.grid_bounds}
          />
        )}

        {/* Known mine markers */}
        {mines && mines.map((mine, i) => (
          <Marker key={`mine-${i}`} position={[mine.lat, mine.lon]} icon={mineIcon}>
            <Popup>
              <div style={{ fontFamily: 'Inter', fontSize: 13 }}>
                <strong>⛏ {mine.name}</strong><br />
                Mineral: {mine.mineral}<br />
                <span style={{ color: '#888' }}>Known MOIL Mine Location</span>
              </div>
            </Popup>
          </Marker>
        ))}

        {/* Drill target markers */}
        {hasResults && results.drill_targets.slice(0, 10).map((target, i) => (
          <Marker
            key={`target-${i}`}
            position={[target.latitude, target.longitude]}
            icon={drillIcon}
          >
            <Popup>
              <div style={{ fontFamily: 'Inter', fontSize: 13, minWidth: 200 }}>
                <strong style={{ color: '#e74c3c' }}>🎯 Drill Target #{target.rank}</strong><br />
                <strong>MPI Score: {target.mpi_score.toFixed(3)}</strong><br />
                Confidence: {target.confidence_percent}%<br />
                Depth: {target.recommended_depth_m}m<br />
                <span style={{ color: '#d4a843', fontSize: 11 }}>
                  {target.top_shap_factor}
                </span>
              </div>
            </Popup>
          </Marker>
        ))}

        {/* AOI rectangle */}
        {hasResults && (
          <Rectangle
            bounds={[
              [results.grid_bounds.min_lat, results.grid_bounds.min_lon],
              [results.grid_bounds.max_lat, results.grid_bounds.max_lon]
            ]}
            pathOptions={{ color: '#1b9aaa', weight: 2, fillOpacity: 0, dashArray: '5,5' }}
          />
        )}
      </MapContainer>
    </div>
  )
}
