import React from 'react'
import { Link, useLocation } from 'react-router-dom'

export default function Navbar() {
  const location = useLocation()
  return (
    <nav className="navbar">
      <div className="navbar-logo">
        <span className="icon">🛰️</span>
        <span>Geo<span className="highlight">Mines</span>-AI</span>
      </div>
      <div className="navbar-links">
        <Link to="/" className={location.pathname === '/' ? 'active' : ''}>Dashboard</Link>
        <span className="navbar-badge">SIH26009 • DEMO</span>
      </div>
    </nav>
  )
}
