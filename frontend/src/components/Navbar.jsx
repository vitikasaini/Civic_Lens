import React from 'react';

export default function Navbar({ activeTab, setActiveTab }) {
  return (
    <header className="navbar-container">
      <div className="navbar-content">
        <div className="brand" onClick={() => setActiveTab('citizen')}>
          <div className="brand-logo">🔍</div>
          <div className="brand-text">
            <h1>CivicLens</h1>
            <span>AI-Powered Civic Issue Prioritization</span>
          </div>
        </div>

        <nav className="nav-tabs">
          <button
            type="button"
            className={`nav-tab ${activeTab === 'citizen' ? 'active' : ''}`}
            onClick={() => setActiveTab('citizen')}
          >
            📢 Citizen Report Form
          </button>
          <button
            type="button"
            className={`nav-tab ${activeTab === 'authority' ? 'active' : ''}`}
            onClick={() => setActiveTab('authority')}
          >
            🏛️ Authority Dashboard
          </button>
        </nav>
      </div>
    </header>
  );
}
