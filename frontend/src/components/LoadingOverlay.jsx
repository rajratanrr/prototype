import React from 'react'

const steps = [
  { icon: '📡', text: 'Downloading satellite imagery...' },
  { icon: '🔬', text: 'Computing spectral indices (Mn, Fe, Clay)...' },
  { icon: '🌿', text: 'Applying NDVI vegetation mask...' },
  { icon: '📐', text: 'Extracting fault lineaments from SAR...' },
  { icon: '🧠', text: 'Running XGBoost + CNN ensemble...' },
  { icon: '📊', text: 'Computing SHAP explainability...' },
  { icon: '🗺️', text: 'Generating MPI heatmap...' },
  { icon: '📍', text: 'Ranking drill targets...' },
]

export default function LoadingOverlay({ progress }) {
  const currentStep = Math.min(Math.floor(progress / (100 / steps.length)), steps.length - 1)

  return (
    <div className="loading-overlay">
      <div className="loading-spinner" />
      <div className="loading-text">
        {steps[currentStep].icon} {steps[currentStep].text}
      </div>
      <div className="loading-sub">
        Step {currentStep + 1} of {steps.length} — {progress}% complete
      </div>
      <div style={{
        marginTop: 20, width: 200, height: 4,
        background: 'rgba(255,255,255,0.1)', borderRadius: 2
      }}>
        <div style={{
          width: `${progress}%`, height: '100%',
          background: 'linear-gradient(90deg, #1b9aaa, #2ecc71)',
          borderRadius: 2, transition: 'width 0.3s ease'
        }} />
      </div>
    </div>
  )
}
