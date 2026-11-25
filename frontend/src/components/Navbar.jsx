import React from 'react';
import { useAuth } from '../context/AuthContext';

export default function Navbar({ currentPath, onNavigate }) {
  const { user, logout } = useAuth();

  return (
    <header className="navbar-container">
      <div className="navbar-content">
        <div
          className="brand"
          onClick={() => onNavigate(user ? (user.role === 'authority' ? '/authority' : '/citizen') : '/login')}
          style={{ cursor: 'pointer' }}
        >
          <div className="brand-logo">🔍</div>
          <div className="brand-text">
            <h1>CivicLens</h1>
            <span>AI-Powered Civic Issue Prioritization</span>
          </div>
        </div>

        <nav className="nav-tabs">
          {user ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span
                style={{
                  padding: '4px 8px',
                  borderRadius: '12px',
                  fontSize: '12px',
                  fontWeight: 600,
                  backgroundColor: user.role === 'authority' ? '#fef3c7' : '#dbeafe',
                  color: user.role === 'authority' ? '#92400e' : '#1e40af',
                }}
              >
                {user.role === 'authority' ? '🏛️ Authority' : '👤 Citizen'}
              </span>
              <span style={{ fontSize: '13px', color: '#4b5563' }}>{user.email}</span>
              <button
                type="button"
                className="btn btn-xs btn-outline"
                onClick={logout}
              >
                Logout
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                type="button"
                className={`nav-tab ${currentPath === '/login' ? 'active' : ''}`}
                onClick={() => onNavigate('/login')}
              >
                Sign In
              </button>
              <button
                type="button"
                className={`nav-tab ${currentPath === '/register' ? 'active' : ''}`}
                onClick={() => onNavigate('/register')}
              >
                Register
              </button>
            </div>
          )}
        </nav>
      </div>
    </header>
  );
}
