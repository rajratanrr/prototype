import React, { useEffect, useRef, useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Rectangle, useMap } from 'react-leaflet'
import L from 'leaflet'

// Fix Leaflet default icon issue with bundlers
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

// ── Map tile layer definitions (all 100% free, no API key) ──────────
const TILE_LAYERS = {
  satellite: {
    label: '🛰️ Satellite',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: 'Tiles &copy; Esri &mdash; Source: Esri, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
    maxZoom: 19,
  },
  dark: {
    label: '🌑 Dark',
    url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; <a href="https://carto.com">CARTO</a>',
    maxZoom: 19,
  },
  terrain: {
    label: '⛰️ Terrain',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
    attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ, TomTom, Intermap, iPC, USGS, FAO, NPS, NRCAN, GeoBase, Kadaster NL, Ordnance Survey, Esri Japan, METI, Esri China (Hong Kong), and the GIS User Community',
    maxZoom: 18,
  },
}

// Custom drill target icon
const drillIcon = new L.DivIcon({
  className: '',
  html: `<div style="
    width:28px;height:28px;border-radius:50%;
    background:linear-gradient(135deg,#ff4757,#c0392b);
    border:2.5px solid white;box-shadow:0 2px 10px rgba(255,71,87,0.6);
    display:flex;align-items:center;justify-content:center;
    font-size:13px;
  ">🎯</div>`,
  iconSize: [28, 28],
  iconAnchor: [14, 14],
})

// Known mine icon
const mineIcon = new L.DivIcon({
  className: '',
  html: `<div style="
    width:22px;height:22px;border-radius:50%;
    background:linear-gradient(135deg,#f9ca24,#d4a843);
    border:2px solid white;box-shadow:0 2px 8px rgba(212,168,67,0.5);
    display:flex;align-items:center;justify-content:center;
    font-size:11px;
  ">⛏</div>`,
  iconSize: [22, 22],
  iconAnchor: [11, 11],
})

// ── Heatmap canvas overlay ──────────────────────────────────────────
function HeatmapOverlay({ data, bounds }) {
  const map = useMap()
  const overlayRef = useRef(null)

  useEffect(() => {
    if (!data || data.length === 0) return

    if (overlayRef.current) {
      map.removeLayer(overlayRef.current)
    }

    const canvas = document.createElement('canvas')
    const rows = data.length
    const cols = data[0].length
    canvas.width = cols
    canvas.height = rows
    const ctx = canvas.getContext('2d')

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

    const imageBounds = [
      [bounds.min_lat, bounds.min_lon],
      [bounds.max_lat, bounds.max_lon],
    ]
    const overlay = L.imageOverlay(canvas.toDataURL(), imageBounds, { opacity: 0.65 })
    overlay.addTo(map)
    overlayRef.current = overlay

    map.fitBounds(imageBounds, { padding: [20, 20] })

    return () => {
      if (overlayRef.current) map.removeLayer(overlayRef.current)
    }
  }, [data, bounds, map])

  return null
}

// ── Layer Switcher Control ──────────────────────────────────────────
function LayerSwitcher({ activeLayer, onLayerChange }) {
  return (
    <div style={{
      position: 'absolute',
      top: 12,
      right: 12,
      zIndex: 1000,
      display: 'flex',
      flexDirection: 'column',
      gap: 6,
    }}>
      {Object.entries(TILE_LAYERS).map(([key, layer]) => (
        <button
          key={key}
          onClick={() => onLayerChange(key)}
          style={{
            padding: '7px 12px',
            borderRadius: 8,
            border: activeLayer === key
              ? '2px solid #1b9aaa'
              : '2px solid rgba(255,255,255,0.15)',
            background: activeLayer === key
              ? 'rgba(27,154,170,0.85)'
              : 'rgba(15,15,25,0.80)',
            color: '#fff',
            fontSize: 12,
            fontFamily: 'Inter, sans-serif',
            fontWeight: activeLayer === key ? 700 : 400,
            cursor: 'pointer',
            backdropFilter: 'blur(8px)',
            boxShadow: activeLayer === key
              ? '0 0 12px rgba(27,154,170,0.5)'
              : '0 2px 8px rgba(0,0,0,0.4)',
            transition: 'all 0.2s ease',
            whiteSpace: 'nowrap',
          }}
        >
          {layer.label}
        </button>
      ))}
    </div>
  )
}

// ── Main MapView Component ──────────────────────────────────────────
export default function MapView({ results, mines }) {
  const center = [21.5, 79.5]
  const hasResults = results && results.mpi_heatmap_data
  const [activeLayer, setActiveLayer] = useState('satellite')

  const currentTile = TILE_LAYERS[activeLayer]

  return (
    <div className="map-container" style={{ position: 'relative' }}>
      <MapContainer
        center={center}
        zoom={7}
        style={{ height: '100%', width: '100%' }}
        zoomControl={true}
      >
        <TileLayer
          key={activeLayer}
          attribution={currentTile.attribution}
          url={currentTile.url}
          maxZoom={currentTile.maxZoom}
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

        {/* AOI bounding rectangle */}
        {hasResults && (
          <Rectangle
            bounds={[
              [results.grid_bounds.min_lat, results.grid_bounds.min_lon],
              [results.grid_bounds.max_lat, results.grid_bounds.max_lon],
            ]}
            pathOptions={{ color: '#1b9aaa', weight: 2, fillOpacity: 0, dashArray: '5,5' }}
          />
        )}
      </MapContainer>

      {/* Layer switcher (floating on top of map) */}
      <LayerSwitcher activeLayer={activeLayer} onLayerChange={setActiveLayer} />
    </div>
  )
}
