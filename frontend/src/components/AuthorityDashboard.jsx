import React, { useState, useEffect } from 'react';
import DashboardMap from './DashboardMap';
import ComplaintDetailModal from './ComplaintDetailModal';
import NotificationBell from './NotificationBell';
import { useAuth } from '../context/AuthContext';
import { formatLocationAddress } from '../utils/location';

export default function AuthorityDashboard({ onLogout }) {
  const { authFetch, user } = useAuth();
  const [summary, setSummary] = useState({
    total_complaints: 0,
    high_priority_complaints: 0,
    pending_complaints: 0,
    in_progress_complaints: 0,
    resolved_complaints: 0,
  });

  const [complaints, setComplaints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Filters
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedSeverity, setSelectedSeverity] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [selectedPriority, setSelectedPriority] = useState('');
  const [sortBy, setSortBy] = useState('priority');

  // Selected complaint for modal
  const [selectedComplaintId, setSelectedComplaintId] = useState(null);
  const [modalInitialShowMap, setModalInitialShowMap] = useState(false);

  const fetchSummary = async () => {
    try {
      const res = await authFetch('/api/dashboard/summary');
      if (res.ok) {
        const data = await res.json();
        setSummary(data);
      }
    } catch (err) {
      console.error('Error fetching dashboard summary:', err);
    }
  };

  const fetchComplaints = async () => {
    setLoading(true);
    setError('');
    try {
      const params = new URLSearchParams();
      if (selectedCategory) params.append('category', selectedCategory);
      if (selectedSeverity) params.append('severity', selectedSeverity);
      if (selectedStatus) params.append('status', selectedStatus);
      if (selectedPriority) params.append('priority', selectedPriority);
      if (sortBy) params.append('sort', sortBy);

      const res = await authFetch(`/api/complaints?${params.toString()}`);
      if (!res.ok) throw new Error('Failed to fetch complaints');
      const data = await res.json();
      setComplaints(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const refreshAll = () => {
    fetchSummary();
    fetchComplaints();
  };

  useEffect(() => {
    fetchSummary();
  }, []);

  useEffect(() => {
    fetchComplaints();
  }, [selectedCategory, selectedSeverity, selectedStatus, selectedPriority, sortBy]);

  const handleQuickStatusUpdate = async (id, targetStatus) => {
    try {
      const res = await authFetch(`/api/complaints/${id}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_status: targetStatus }),
      });
      if (res.ok) {
        refreshAll();
      }
    } catch (err) {
      console.error('Status update failed:', err);
    }
  };

  return (
    <div className="dashboard-container">
      {/* Authority top bar */}
      <div className="citizen-topbar">
        <div>
          <span className="topbar-welcome">🏛️ Authority Dashboard</span>
          {user && <span className="role-badge authority">{user.email}</span>}
        </div>
        <div className="topbar-actions">
          <NotificationBell />
          {onLogout && <button className="btn btn-outline" onClick={onLogout}>Logout</button>}
        </div>
      </div>
      {/* 8.1 Summary KPI Cards */}
      <div className="summary-cards-grid">
        <div className="kpi-card">
          <div className="kpi-icon">📋</div>
          <div className="kpi-info">
            <span className="kpi-label">Total Reports</span>
            <span className="kpi-val">{summary.total_complaints}</span>
          </div>
        </div>

        <div className="kpi-card kpi-high">
          <div className="kpi-icon">🚨</div>
          <div className="kpi-info">
            <span className="kpi-label">High Priority</span>
            <span className="kpi-val">{summary.high_priority_complaints}</span>
          </div>
        </div>

        <div className="kpi-card kpi-pending">
          <div className="kpi-icon">⏳</div>
          <div className="kpi-info">
            <span className="kpi-label">Pending / Reported</span>
            <span className="kpi-val">{summary.pending_complaints}</span>
          </div>
        </div>

        <div className="kpi-card kpi-inprogress">
          <div className="kpi-icon">⚙️</div>
          <div className="kpi-info">
            <span className="kpi-label">In Progress</span>
            <span className="kpi-val">{summary.in_progress_complaints}</span>
          </div>
        </div>

        <div className="kpi-card kpi-resolved">
          <div className="kpi-icon">✅</div>
          <div className="kpi-info">
            <span className="kpi-label">Resolved</span>
            <span className="kpi-val">{summary.resolved_complaints}</span>
          </div>
        </div>
      </div>

      {/* 8.5 Interactive Map Overview */}
      <div className="card dashboard-section">
        <div className="section-header">
          <h3>🗺️ Geographic Distribution & Priority Hotspots</h3>
          <span className="count-tag">{complaints.length} complaints mapped</span>
        </div>
        <DashboardMap
          complaints={complaints}
          onSelectComplaint={(id) => setSelectedComplaintId(id)}
        />
      </div>

      {/* 8.3 Filters & Controls Bar */}
      <div className="card dashboard-section">
        <div className="filters-bar">
          <div className="filter-item">
            <label>Category:</label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="filter-select"
            >
              <option value="">All Categories</option>
              <option value="Potholes / Damaged Roads">Potholes / Damaged Roads</option>
              <option value="Garbage Accumulation">Garbage Accumulation</option>
              <option value="Waterlogging / Drainage Problems">Waterlogging / Drainage</option>
              <option value="Streetlight Faults">Streetlight Faults</option>
            </select>
          </div>

          <div className="filter-item">
            <label>Severity:</label>
            <select
              value={selectedSeverity}
              onChange={(e) => setSelectedSeverity(e.target.value)}
              className="filter-select"
            >
              <option value="">All Severities</option>
              <option value="High">High</option>
              <option value="Medium">Medium</option>
              <option value="Low">Low</option>
            </select>
          </div>

          <div className="filter-item">
            <label>Status:</label>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="filter-select"
            >
              <option value="">All Statuses</option>
              <option value="Reported">Reported</option>
              <option value="In Progress">In Progress</option>
              <option value="Resolved">Resolved</option>
            </select>
          </div>

          <div className="filter-item">
            <label>Priority Tier:</label>
            <select
              value={selectedPriority}
              onChange={(e) => setSelectedPriority(e.target.value)}
              className="filter-select"
            >
              <option value="">All Priority Tiers</option>
              <option value="High">High (&ge; 60%)</option>
              <option value="Medium">Medium (35-59%)</option>
              <option value="Low">Low (&lt; 35%)</option>
            </select>
          </div>

          <div className="filter-item">
            <label>Sort By:</label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="filter-select"
            >
              <option value="priority">Priority Score (Highest First)</option>
              <option value="date">Date Reported (Newest First)</option>
            </select>
          </div>

          <button className="btn btn-outline btn-refresh" onClick={refreshAll}>
            🔄 Refresh
          </button>
        </div>

        {/* 8.2 Complaints Table */}
        {error && <div className="alert alert-error">⚠️ {error}</div>}

        {loading ? (
          <div className="loading-spinner-box">
            <span className="spinner"></span>
            <p>Loading complaints...</p>
          </div>
        ) : complaints.length === 0 ? (
          <div className="empty-state">
            <p>No complaints match the current filter criteria.</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="complaint-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Category</th>
                  <th>Description</th>
                  <th>Location</th>
                  <th>Severity</th>
                  <th>Priority Score</th>
                  <th>Similar</th>
                  <th>Status</th>
                  <th>Reported Date</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {complaints.map((c) => {
                  const pScore = c.priority_score ?? 0;
                  const priorityClass =
                    pScore >= 0.6 ? 'priority-high' : pScore >= 0.35 ? 'priority-med' : 'priority-low';

                  const displayAddr = formatLocationAddress(c.address, c.latitude, c.longitude);

                  return (
                    <tr
                      key={c.id}
                      className="complaint-row"
                      onClick={() => {
                        setModalInitialShowMap(false);
                        setSelectedComplaintId(c.id);
                      }}
                    >
                      <td><strong>#{c.id}</strong></td>
                      <td>
                        <span className="category-pill">{c.category || 'Unassigned'}</span>
                      </td>
                      <td className="desc-cell" title={c.description}>
                        {c.description.length > 55 ? `${c.description.substring(0, 55)}...` : c.description}
                      </td>
                      <td className="location-cell" style={{ maxWidth: '200px', fontSize: '12px' }}>
                        <div style={{ fontWeight: 500, color: '#1f2937', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={displayAddr}>
                          {displayAddr}
                        </div>
                        <div>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setModalInitialShowMap(true);
                              setSelectedComplaintId(c.id);
                              if (window.__civicLensFocusLocation) {
                                window.__civicLensFocusLocation(c.latitude, c.longitude);
                              }
                            }}
                            title="Click to open exact location in the map"
                            style={{
                              background: '#eff6ff',
                              border: '1px solid #bfdbfe',
                              borderRadius: '4px',
                              color: '#1d4ed8',
                              cursor: 'pointer',
                              padding: '1px 5px',
                              fontSize: '11px',
                              fontWeight: 600,
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '3px',
                              marginTop: '3px',
                            }}
                          >
                            📍 ({c.latitude.toFixed(4)}, {c.longitude.toFixed(4)})
                          </button>
                        </div>
                      </td>
                      <td>
                        <span className={`badge badge-severity-${(c.severity || c.citizen_severity).toLowerCase()}`}>
                          {c.severity || c.citizen_severity}
                        </span>
                      </td>
                      <td>
                        <span className={`badge ${priorityClass}`}>
                          {c.priority_score !== null ? `${(c.priority_score * 100).toFixed(1)}%` : '—'}
                        </span>
                      </td>
                      <td>
                        {c.similar_count > 0 ? (
                          <span className="badge badge-similar">+{c.similar_count} dupes</span>
                        ) : (
                          <span className="text-muted">0</span>
                        )}
                      </td>
                      <td>
                        <span className={`badge badge-status-${c.status.toLowerCase().replace(' ', '-')}`}>
                          {c.status}
                        </span>
                      </td>
                      <td className="time-cell">
                        {new Date(c.created_at).toLocaleDateString()}
                      </td>
                      <td onClick={(e) => e.stopPropagation()}>
                        <div className="action-buttons">
                          {c.status === 'Reported' && (
                            <button
                              className="btn btn-xs btn-warning"
                              title="Start Work"
                              onClick={() => handleQuickStatusUpdate(c.id, 'In Progress')}
                            >
                              Start
                            </button>
                          )}
                          {c.status === 'In Progress' && (
                            <button
                              className="btn btn-xs btn-success"
                              title="Resolve Issue"
                              onClick={() => handleQuickStatusUpdate(c.id, 'Resolved')}
                            >
                              Resolve
                            </button>
                          )}
                          <button
                            className="btn btn-xs btn-outline"
                            onClick={() => setSelectedComplaintId(c.id)}
                          >
                            Details
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 8.2.3 Complaint Detail Modal */}
      {selectedComplaintId && (
        <ComplaintDetailModal
          complaintId={selectedComplaintId}
          initialShowMap={modalInitialShowMap}
          onClose={() => {
            setSelectedComplaintId(null);
            setModalInitialShowMap(false);
          }}
          onStatusUpdated={refreshAll}
        />
      )}
    </div>
  );
}
