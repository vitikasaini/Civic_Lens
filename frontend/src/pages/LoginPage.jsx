import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';

export default function LoginPage({ onSwitchToRegister }) {
  const { login } = useAuth();
  const [mode, setMode] = useState('citizen'); // 'citizen' | 'authority'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleModeToggle = (newMode) => {
    if (newMode !== mode) {
      setMode(newMode);
      setEmail('');
      setPassword('');
      setError('');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, role: mode }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || 'Login failed');
        return;
      }
      // Decode role from JWT payload (base64)
      const [, payloadB64] = data.access_token.split('.');
      const payload = JSON.parse(atob(payloadB64 + '=='.slice((payloadB64.length % 4) || 4)));
      login({ token: data.access_token, role: payload.role, email });
    } catch {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const isCitizen = mode === 'citizen';

  return (
    <div className="auth-page">
      <div className={`auth-card mode-${mode}`}>
        {/* Citizen / Authority Mode Toggle */}
        <div className="auth-role-toggle">
          <button
            type="button"
            className={`role-toggle-btn ${isCitizen ? 'active citizen' : ''}`}
            onClick={() => handleModeToggle('citizen')}
          >
            👤 Citizen Login
          </button>
          <button
            type="button"
            className={`role-toggle-btn ${!isCitizen ? 'active authority' : ''}`}
            onClick={() => handleModeToggle('authority')}
          >
            🏛️ Authority Login
          </button>
        </div>

        <div className="auth-header">
          <div className="brand-logo">{isCitizen ? '👤' : '🏛️'}</div>
          <h2>{isCitizen ? 'Citizen Portal' : 'Authority Portal'}</h2>
          <p>
            {isCitizen
              ? 'Sign in to report and track civic issues'
              : 'Municipal administration & decision support'}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          {error && <div className="alert alert-error">⚠️ {error}</div>}
          <div className="form-group">
            <label>Email address</label>
            <input
              type="email"
              className="form-input"
              placeholder={isCitizen ? 'citizen@example.com' : 'authority@civiclens.local'}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              className="form-input"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </div>
          <button
            type="submit"
            className={`btn btn-full ${isCitizen ? 'btn-primary' : 'btn-authority'}`}
            disabled={loading}
          >
            {loading ? 'Signing in…' : isCitizen ? 'Sign In as Citizen' : 'Sign In as Authority'}
          </button>
        </form>

        <div className="auth-footer">
          {isCitizen ? (
            <p>
              New citizen?{' '}
              <button type="button" className="link-btn" onClick={onSwitchToRegister}>
                Create an account
              </button>
            </p>
          ) : (
            <p className="auth-note">
              ℹ️ Authority accounts are created by the administrator.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
