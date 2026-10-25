import React, { useState, useEffect } from 'react';

export default function ComplaintDetailModal({ complaintId, onClose, onStatusUpdated }) {
  const [complaint, setComplaint] = useState(null);
  const [similarComplaints, setSimilarComplaints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [updatingStatus, setUpdatingStatus] = useState(false);
  const [error, setError] = useState('');

  const fetchDetail = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/complaints/${complaintId}`);
      if (!res.ok) throw new Error('Complaint not found');
      const data = await res.json();
      setComplaint(data);

      // Fetch similar complaints if grouped
      if (data.group_id) {
        const simRes = await fetch(`/api/complaints/${complaintId}/similar`);
        if (simRes.ok) {
          const simData = await simRes.json();
          setSimilarComplaints(simData);
        }
      } else {
        setSimilarComplaints([]);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (complaintId) fetchDetail();
  }, [complaintId]);

  const handleStatusChange = async (targetStatus) => {
    setUpdatingStatus(true);
    setError('');
    try {
      const res = await fetch(`/api/complaints/${complaintId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_status: targetStatus }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || 'Failed to update status');
      }

      await fetchDetail();
      if (onStatusUpdated) onStatusUpdated();
    } catch (err) {
      setError(err.message);
    } finally {
      setUpdatingStatus(false);
    }
  };

  if (!complaintId) return null;

  const factors = complaint?.priority_factors || {};
  const pb = factors.priority_breakdown || {};
  const sb = factors.severity_breakdown || {};
  const rd = factors.resolution_data || {};

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h3>Complaint #{complaintId} Details</h3>
            <span className={`badge badge-status-${complaint?.status?.toLowerCase().replace(' ', '-')}`}>
              {complaint?.status}
            </span>
          </div>
          <button className="btn-close" onClick={onClose}>✕</button>
        </div>

        <div className="modal-body">
          {loading ? (
            <div className="loading-spinner-box">
              <span className="spinner"></span>
              <p>Loading complaint details...</p>
            </div>
          ) : error ? (
            <div className="alert alert-error">⚠️ {error}</div>
          ) : (
            <>
              {/* Top Summary Grid */}
              <div className="detail-grid">
                <div className="detail-image-box">
                  <img
                    src={`/${complaint.image_path}`}
                    alt="Complaint Evidence"
                    className="modal-image"
                    onError={(e) => { e.target.src = 'https://placehold.co/400x300?text=No+Image'; }}
                  />
                  <div className="image-meta">
                    <span>GPS: {complaint.latitude.toFixed(5)}, {complaint.longitude.toFixed(5)}</span>
                    <span>Reported: {new Date(complaint.created_at).toLocaleString()}</span>
                  </div>
                </div>

                <div className="detail-meta-box">
                  <h4>Category & Status</h4>
                  <div className="info-row">
                    <span className="label">Category:</span>
                    <span className="value"><strong>{complaint.category || 'Unassigned'}</strong></span>
                  </div>
                  <div className="info-row">
                    <span className="label">Citizen Severity:</span>
                    <span className="value">{complaint.citizen_severity}</span>
                  </div>
                  <div className="info-row">
                    <span className="label">Assessed Severity:</span>
                    <span className={`badge badge-severity-${complaint.severity?.toLowerCase()}`}>
                      {complaint.severity} ({complaint.severity_points || 0} pts)
                    </span>
                  </div>
                  <div className="info-row">
                    <span className="label">Priority Score:</span>
                    <span className="value">
                      <strong style={{ fontSize: '1.2rem', color: (complaint.priority_score || 0) > 0.6 ? '#dc2626' : '#2563eb' }}>
                        {complaint.priority_score !== null ? `${(complaint.priority_score * 100).toFixed(1)}%` : 'N/A'}
                      </strong>
                    </span>
                  </div>
                  <div className="info-row">
                    <span className="label">Group / Duplicates:</span>
                    <span className="value">
                      {complaint.group_id ? `Group #${complaint.group_id} (${complaint.similar_count} similar)` : 'None (Standalone)'}
                    </span>
                  </div>

                  {/* Status Transition Action */}
                  <div className="status-transition-box">
                    <h5>Update Status:</h5>
                    <div className="btn-group">
                      {complaint.status === 'Reported' && (
                        <button
                          className="btn btn-warning"
                          disabled={updatingStatus}
                          onClick={() => handleStatusChange('In Progress')}
                        >
                          Mark In Progress ⚙️
                        </button>
                      )}
                      {complaint.status === 'In Progress' && (
                        <button
                          className="btn btn-success"
                          disabled={updatingStatus}
                          onClick={() => handleStatusChange('Resolved')}
                        >
                          Mark Resolved ✅
                        </button>
                      )}
                      {complaint.status === 'Resolved' && (
                        <span className="badge badge-resolved">Resolved (Workflow Completed)</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Description */}
              <div className="section-box">
                <h4>Description</h4>
                <p className="description-text">{complaint.description}</p>
              </div>

              {/* Explainable Priority Breakdown */}
              <div className="section-box">
                <h4>📊 Explainable Priority Factor Breakdown</h4>
                <div className="priority-table-wrapper">
                  <table className="factor-table">
                    <thead>
                      <tr>
                        <th>Contributing Factor</th>
                        <th>Raw Value</th>
                        <th>Normalized (0-1)</th>
                        <th>Weight</th>
                        <th>Contribution</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td><strong>Severity</strong></td>
                        <td>{pb.severity?.value || complaint.severity}</td>
                        <td>{pb.severity?.normalized ?? '—'}</td>
                        <td>40%</td>
                        <td><strong>+{pb.severity?.contribution ?? '—'}</strong></td>
                      </tr>
                      <tr>
                        <td><strong>Similar Complaints</strong></td>
                        <td>{complaint.similar_count} reports</td>
                        <td>{pb.similar?.normalized ?? '—'}</td>
                        <td>25%</td>
                        <td><strong>+{pb.similar?.contribution ?? '—'}</strong></td>
                      </tr>
                      <tr>
                        <td><strong>Location Importance</strong></td>
                        <td>{pb.location?.value || 'Standard'} {pb.location?.matched_location ? `(${pb.location.matched_location})` : ''}</td>
                        <td>{pb.location?.normalized ?? '—'}</td>
                        <td>20%</td>
                        <td><strong>+{pb.location?.contribution ?? '—'}</strong></td>
                      </tr>
                      <tr>
                        <td><strong>Time Since Reporting</strong></td>
                        <td>{pb.time?.value || '0.0 days'}</td>
                        <td>{pb.time?.normalized ?? '—'}</td>
                        <td>15%</td>
                        <td><strong>+{pb.time?.contribution ?? '—'}</strong></td>
                      </tr>
                      <tr className="total-row">
                        <td colSpan="4"><strong>Final Priority Score</strong></td>
                        <td>
                          <strong>
                            {complaint.priority_score !== null ? `${(complaint.priority_score * 100).toFixed(1)}%` : '—'}
                          </strong>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Severity & Multimodal Resolution Breakdown */}
              <div className="section-box">
                <h4>🔍 AI Decision & Severity Details</h4>
                <div className="grid-2-col">
                  <div className="mini-card">
                    <h5>Severity Scoring Breakdown:</h5>
                    <ul>
                      <li>Text Cue Score: <strong>+{sb.text_cue || 0}</strong> {sb.text_matched_cues?.length ? `(${sb.text_matched_cues.join(', ')})` : ''}</li>
                      <li>Citizen Rating Points: <strong>+{sb.citizen || 0}</strong> ({complaint.citizen_severity})</li>
                      <li>Image Area Heuristic: <strong>+{sb.image_cue || 0}</strong> {sb.image_area_ratio ? `(${(sb.image_area_ratio * 100).toFixed(1)}% area)` : ''}</li>
                      <li>Total Points: <strong>{sb.points || 0}</strong> → {complaint.severity}</li>
                    </ul>
                  </div>

                  <div className="mini-card">
                    <h5>Multimodal Resolution:</h5>
                    <ul>
                      <li>Image Model: <strong>{rd.image_category || 'N/A'}</strong> ({(rd.image_confidence * 100 || 0).toFixed(1)}%)</li>
                      <li>Text Model: <strong>{rd.text_category || 'N/A'}</strong> ({(rd.text_confidence * 100 || 0).toFixed(1)}%)</li>
                      <li>Conflict Resolution: <em>{rd.decision_reason || 'N/A'}</em></li>
                    </ul>
                  </div>
                </div>
              </div>

              {/* Similar Complaints List */}
              {similarComplaints.length > 0 && (
                <div className="section-box">
                  <h4>🔗 Similar / Duplicate Complaints in Group #{complaint.group_id}</h4>
                  <div className="similar-list">
                    {similarComplaints.map((sim) => (
                      <div key={sim.id} className="similar-item">
                        <span className="badge badge-reported">#{sim.id}</span>
                        <span className="similar-desc">{sim.description}</span>
                        <span className="similar-status">Status: {sim.status}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Status History Timeline */}
              {complaint.status_history && complaint.status_history.length > 0 && (
                <div className="section-box">
                  <h4>📜 Status Transition History</h4>
                  <div className="timeline">
                    {complaint.status_history.map((hist) => (
                      <div key={hist.id} className="timeline-item">
                        <div className="timeline-dot"></div>
                        <div className="timeline-content">
                          <strong>{hist.new_status}</strong> {hist.old_status ? `(from ${hist.old_status})` : '(Initial Submission)'}
                          <div className="timeline-time">{new Date(hist.changed_at).toLocaleString()}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}
