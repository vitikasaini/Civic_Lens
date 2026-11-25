import React, { useState, useEffect, useCallback, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { useAuth } from '../context/AuthContext';
import CitizenSubmission from '../components/CitizenSubmission';
import NotificationBell from '../components/NotificationBell';
import { formatLocationAddress } from '../utils/location';

const STATUS_STEPS = ['Reported', 'In Progress', 'Resolved'];

function StatusTimeline({ history, createdAt }) {
  // Build a map of status -> timestamp from actual StatusHistory
  const timeMap = {};
  if (createdAt) timeMap['Submitted'] = new Date(createdAt);
  (history || []).forEach((h) => {
    timeMap[h.new_status] = new Date(h.changed_at);
  });

  const steps = ['Submitted', ...STATUS_STEPS];
  return (
    <div className="timeline-horizontal">
      {steps.map((step, i) => {
        const reached = step in timeMap || (step === 'Submitted' && createdAt);
        return (
          <div key={step} className={`timeline-h-step ${reached ? 'reached' : ''}`}>
            <div className="timeline-h-dot">{reached ? '✓' : i + 1}</div>
            <div className="timeline-h-label">{step}</div>
            {timeMap[step] && (
              <div className="timeline-h-time">{timeMap[step].toLocaleDateString()}</div>
            )}
            {i < steps.length - 1 && <div className={`timeline-h-line ${reached ? 'reached' : ''}`} />}
          </div>
        );
      })}
    </div>
  );
}

function StatusBadge({ status }) {
  const cls = `badge badge-status-${status.toLowerCase().replace(' ', '-')}`;
  return <span className={cls}>{status}</span>;
}

function ComplaintCard({ complaint, onClick }) {
  const pScore = complaint.priority_score ?? 0;
  const priorityClass = pScore >= 0.6 ? 'priority-high' : pScore >= 0.35 ? 'priority-med' : 'priority-low';
  return (
    <div className="citizen-complaint-card" onClick={onClick} role="button" tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick()}>
      <div className="ccc-top">
        <span className="ccc-id">#{complaint.id}</span>
        <StatusBadge status={complaint.status} />
        {complaint.priority_score !== null && (
          <span className={`badge ${priorityClass}`}>{(pScore * 100).toFixed(0)}% priority</span>
        )}
      </div>
      <div className="ccc-desc">{complaint.description.length > 100
        ? complaint.description.substring(0, 100) + '…'
        : complaint.description}
      </div>
      <div className="ccc-meta">
        {complaint.category && <span className="category-pill">{complaint.category}</span>}
        <span style={{ fontSize: '11px', color: '#4b5563', maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={formatLocationAddress(complaint.address, complaint.latitude, complaint.longitude)}>
          📍 {formatLocationAddress(complaint.address, complaint.latitude, complaint.longitude)}
        </span>
        <span className="ccc-date">{new Date(complaint.created_at).toLocaleDateString()}</span>
      </div>
    </div>
  );
}

function MyComplaintDetail({ complaint, onBack, authFetch }) {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showMap, setShowMap] = useState(false);

  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);

  useEffect(() => {
    authFetch(`/api/complaints/${complaint.id}`)
      .then((r) => r.json())
      .then((d) => setDetail(d))
      .catch(() => setDetail(null))
      .finally(() => setLoading(false));
  }, [complaint.id, authFetch]);

  // Leaflet map setup
  useEffect(() => {
    if (!showMap || !detail || !mapContainerRef.current) return;

    const displayAddr = formatLocationAddress(detail.address, detail.latitude, detail.longitude);

    if (!mapInstanceRef.current) {
      const map = L.map(mapContainerRef.current).setView([detail.latitude, detail.longitude], 16);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 19,
      }).addTo(map);

      const marker = L.marker([detail.latitude, detail.longitude]).addTo(map);
      marker.bindPopup(`
        <strong>Complaint #${detail.id}</strong><br/>
        📍 ${displayAddr}<br/>
        <em>(${detail.latitude.toFixed(5)}, ${detail.longitude.toFixed(5)})</em>
      `).openPopup();

      mapInstanceRef.current = map;
    } else {
      mapInstanceRef.current.setView([detail.latitude, detail.longitude], 16);
      mapInstanceRef.current.invalidateSize();
    }

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [showMap, detail]);

  const handleOpenMap = () => {
    setShowMap(true);
    setTimeout(() => {
      if (mapContainerRef.current) {
        mapContainerRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }, 150);
  };

  if (loading) return (
    <div className="loading-spinner-box"><span className="spinner" /><p>Loading details…</p></div>
  );
  if (!detail) return <div className="alert alert-error">Could not load complaint details.</div>;

  const displayAddr = formatLocationAddress(detail.address, detail.latitude, detail.longitude);

  return (
    <div className="citizen-detail-view">
      <button className="btn btn-outline" onClick={onBack}>← Back to My Complaints</button>
      <h3>Complaint #{detail.id}</h3>
      <StatusTimeline history={detail.status_history} createdAt={detail.created_at} />

      <div className="detail-grid">
        <div className="detail-image-box">
          <img
            src={`/${detail.image_path}`}
            alt="Evidence"
            className="modal-image"
            onError={(e) => { e.target.src = 'https://placehold.co/400x300?text=No+Image'; }}
          />
          <div className="image-meta">
            <button
              type="button"
              onClick={handleOpenMap}
              title="Click to view exact location on map"
              style={{ background: 'none', border: 'none', color: '#2563eb', cursor: 'pointer', padding: 0, fontWeight: 500, fontSize: 'inherit', textDecoration: 'underline' }}
            >
              📍 {detail.latitude.toFixed(5)}, {detail.longitude.toFixed(5)}
            </button>
            <span>🏠 {displayAddr}</span>
          </div>
        </div>
        <div className="detail-meta-box">
          <div className="info-row"><span className="label">Category:</span>
            <span className="value">{detail.category || 'Processing…'}</span></div>
          <div className="info-row"><span className="label">Location Address:</span>
            <span className="value"><strong>{displayAddr}</strong></span></div>
          <div className="info-row"><span className="label">Coordinates:</span>
            <span className="value">
              <button
                type="button"
                onClick={() => {
                  if (!showMap) handleOpenMap();
                  else setShowMap(false);
                }}
                title="Click to open exact location in the map"
                style={{
                  background: '#eff6ff',
                  border: '1px solid #bfdbfe',
                  borderRadius: '4px',
                  color: '#1d4ed8',
                  cursor: 'pointer',
                  padding: '2px 8px',
                  fontSize: '12px',
                  fontWeight: 600,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
              >
                📍 {detail.latitude.toFixed(5)}, {detail.longitude.toFixed(5)}
                <span style={{ textDecoration: 'underline', fontWeight: 400, marginLeft: '3px' }}>
                  ({showMap ? 'Hide Map' : 'View on Map'})
                </span>
              </button>
            </span></div>
          <div className="info-row"><span className="label">Status:</span>
            <StatusBadge status={detail.status} /></div>
          <div className="info-row"><span className="label">Severity:</span>
            <span className="value">{detail.severity || detail.citizen_severity}</span></div>
          {detail.priority_score !== null && (
            <div className="info-row"><span className="label">Priority:</span>
              <span className="value">{(detail.priority_score * 100).toFixed(1)}%</span></div>
          )}
          <div className="info-row"><span className="label">Submitted:</span>
            <span className="value">{new Date(detail.created_at).toLocaleString()}</span></div>
        </div>
      </div>

      {showMap && (
        <div className="section-box" style={{ marginTop: '16px' }}>
          <h4>📍 Incident Location on Map</h4>
          <div
            ref={mapContainerRef}
            style={{ height: '260px', width: '100%', borderRadius: '6px' }}
          />
        </div>
      )}

      <div className="section-box">
        <h4>Description</h4>
        <p className="description-text">{detail.description}</p>
      </div>
    </div>
  );
}

export default function CitizenDashboard({ onLogout }) {
  const { authFetch, user } = useAuth();
  const [view, setView] = useState('home'); // 'home' | 'submit' | 'detail'
  const [complaints, setComplaints] = useState([]);
  const [selectedComplaint, setSelectedComplaint] = useState(null);
  const [loadingComplaints, setLoadingComplaints] = useState(false);
  const [compError, setCompError] = useState('');

  const fetchMyComplaints = useCallback(async () => {
    setLoadingComplaints(true);
    setCompError('');
    try {
      const res = await authFetch('/api/complaints/my');
      if (!res.ok) throw new Error('Failed to load your complaints');
      const data = await res.json();
      setComplaints(data);
    } catch (err) {
      setCompError(err.message);
    } finally {
      setLoadingComplaints(false);
    }
  }, [authFetch]);

  useEffect(() => {
    fetchMyComplaints();
  }, [fetchMyComplaints]);

  // Status summary counts
  const counts = complaints.reduce((acc, c) => {
    acc[c.status] = (acc[c.status] || 0) + 1;
    return acc;
  }, {});

  if (view === 'submit') {
    return (
      <div className="dashboard-container">
        <div className="citizen-topbar">
          <button className="btn btn-outline" onClick={() => setView('home')}>← Back</button>
          <span className="topbar-title">Submit New Complaint</span>
        </div>
        <CitizenSubmission
          onComplaintCreated={() => { fetchMyComplaints(); setView('home'); }}
          authFetch={authFetch}
        />
      </div>
    );
  }

  if (view === 'detail' && selectedComplaint) {
    return (
      <div className="dashboard-container">
        <MyComplaintDetail
          complaint={selectedComplaint}
          onBack={() => { setView('home'); setSelectedComplaint(null); }}
          authFetch={authFetch}
        />
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      {/* Top bar */}
      <div className="citizen-topbar">
        <div>
          <span className="topbar-welcome">👋 Welcome, {user?.email}</span>
          <span className="role-badge citizen">Citizen</span>
        </div>
        <div className="topbar-actions">
          <NotificationBell onSelectComplaint={(id) => { setSelectedComplaint({ id }); setView('detail'); }} />
          <button className="btn btn-outline" onClick={onLogout}>Logout</button>
        </div>
      </div>

      {/* Welcome + Submit */}
      <div className="card citizen-welcome-card">
        <div>
          <h2>Citizen Dashboard</h2>
          <p>Report civic issues in your area and track their resolution progress.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setView('submit')}>
          📢 Submit New Complaint
        </button>
      </div>

      {/* Status summary */}
      <div className="summary-cards-grid">
        <div className="kpi-card"><div className="kpi-icon">📋</div>
          <div className="kpi-info"><span className="kpi-label">Total</span>
            <span className="kpi-val">{complaints.length}</span></div></div>
        <div className="kpi-card kpi-pending"><div className="kpi-icon">⏳</div>
          <div className="kpi-info"><span className="kpi-label">Reported</span>
            <span className="kpi-val">{counts['Reported'] || 0}</span></div></div>
        <div className="kpi-card kpi-inprogress"><div className="kpi-icon">⚙️</div>
          <div className="kpi-info"><span className="kpi-label">In Progress</span>
            <span className="kpi-val">{counts['In Progress'] || 0}</span></div></div>
        <div className="kpi-card kpi-resolved"><div className="kpi-icon">✅</div>
          <div className="kpi-info"><span className="kpi-label">Resolved</span>
            <span className="kpi-val">{counts['Resolved'] || 0}</span></div></div>
      </div>

      {/* My Complaints */}
      <div className="card dashboard-section">
        <div className="section-header">
          <h3>📂 My Complaints</h3>
          <button className="btn btn-outline btn-refresh" onClick={fetchMyComplaints}>🔄 Refresh</button>
        </div>

        {compError && <div className="alert alert-error">⚠️ {compError}</div>}

        {loadingComplaints ? (
          <div className="loading-spinner-box"><span className="spinner" /><p>Loading your complaints…</p></div>
        ) : complaints.length === 0 ? (
          <div className="empty-state">
            <p>You haven't submitted any complaints yet.</p>
            <button className="btn btn-primary" onClick={() => setView('submit')}>Submit your first complaint</button>
          </div>
        ) : (
          <div className="citizen-complaints-grid">
            {complaints.map((c) => (
              <ComplaintCard
                key={c.id}
                complaint={c}
                onClick={() => { setSelectedComplaint(c); setView('detail'); }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
