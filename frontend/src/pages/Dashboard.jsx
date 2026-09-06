import React, { useState, useEffect, useCallback } from 'react'
import Sidebar from '../components/Sidebar'
import MapView from '../components/MapView'
import ResultsPanel from '../components/ResultsPanel'
import LoadingOverlay from '../components/LoadingOverlay'
import { apiStartAnalysis, apiGetResults, apiGetMines } from '../api/client'

export default function Dashboard() {
  const [sensors, setSensors] = useState(['sentinel2', 'sar', 'dem'])
  const [aoi, setAoi] = useState({ name: 'Nagpur-Balaghat Belt', lat: 21.5, lon: 79.5 })
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [results, setResults] = useState(null)
  const [jobId, setJobId] = useState(null)
  const [mines, setMines] = useState([])

  // Fetch known mine locations on mount
  useEffect(() => {
    apiGetMines()
      .then(res => setMines(res.data))
      .catch(err => {
        console.warn('Could not load mines:', err)
        // Fallback data
        setMines([
          { name: 'Dongri Buzurg', lat: 21.68, lon: 80.22, mineral: 'Braunite' },
          { name: 'Balaghat', lat: 21.81, lon: 80.19, mineral: 'Braunite + Pyrolusite' },
          { name: 'Gumgaon', lat: 21.14, lon: 79.06, mineral: 'Pyrolusite' },
          { name: 'Kandri', lat: 21.42, lon: 79.28, mineral: 'Braunite' },
          { name: 'Chikla', lat: 21.53, lon: 79.38, mineral: 'Braunite' },
          { name: 'Tirodi', lat: 21.72, lon: 79.72, mineral: 'Braunite' },
        ])
      })
  }, [])

  // Simulate progressive loading animation
  const simulateProgress = useCallback(() => {
    return new Promise(resolve => {
      let p = 0
      const interval = setInterval(() => {
        p += Math.random() * 15 + 5
        if (p >= 100) {
          p = 100
          clearInterval(interval)
          resolve()
        }
        setProgress(Math.min(Math.floor(p), 100))
      }, 400)
    })
  }, [])

  const handleAnalyze = async () => {
    setLoading(true)
    setProgress(0)
    setResults(null)

    try {
      // Start loading animation
      const progressPromise = simulateProgress()

      // Call backend
      const analyzeRes = await apiStartAnalysis({
        aoi_name: aoi.name,
        center_lat: aoi.lat,
        center_lon: aoi.lon,
        radius_km: 30,
        sensors: sensors,
      })

      const jid = analyzeRes.data.job_id
      setJobId(jid)

      // Wait for loading animation to finish
      await progressPromise

      // Fetch results
      const resultsRes = await apiGetResults(jid)
      setResults(resultsRes.data)
    } catch (err) {
      console.error('Analysis failed:', err)
      const errorMsg = err.response?.data?.detail
        ? (typeof err.response.data.detail === 'string' ? err.response.data.detail : JSON.stringify(err.response.data.detail))
        : (err.message || 'Network error')
      alert(`Analysis failed: ${errorMsg}\n\nCheck that the backend service is running and reachable.`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="dashboard">
      <Sidebar
        onAnalyze={handleAnalyze}
        loading={loading}
        sensors={sensors}
        setSensors={setSensors}
        aoi={aoi}
        setAoi={setAoi}
      />

      <div style={{ position: 'relative' }}>
        {loading && <LoadingOverlay progress={progress} />}
        <MapView results={results} mines={mines} />
      </div>

      <ResultsPanel results={results} jobId={jobId} />
    </div>
  )
}
