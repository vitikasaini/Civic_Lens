import React, { useState } from 'react';
import LocationPickerMap from './LocationPickerMap';

export default function CitizenSubmission({ onComplaintCreated }) {
  const [description, setDescription] = useState('');
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [citizenSeverity, setCitizenSeverity] = useState('Moderate');
  const [latitude, setLatitude] = useState(28.6139);
  const [longitude, setLongitude] = useState(77.2090);

  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successData, setSuccessData] = useState(null);

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/bmp'];
    if (!allowedTypes.includes(file.type)) {
      setErrorMessage('Please select a valid image file (JPEG, PNG, WEBP).');
      return;
    }

    setErrorMessage('');
    setImageFile(file);
    const reader = new FileReader();
    reader.onload = () => setImagePreview(reader.result);
    reader.readAsDataURL(file);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');
    setSuccessData(null);

    // Client-side validations
    if (!imageFile) {
      setErrorMessage('Please upload a photo of the civic issue.');
      return;
    }
    if (!description.trim() || description.trim().length < 10) {
      setErrorMessage('Please provide a detailed description (minimum 10 characters).');
      return;
    }
    if (latitude === null || longitude === null || isNaN(latitude) || isNaN(longitude)) {
      setErrorMessage('Please pick a valid geographic location on the map.');
      return;
    }

    setLoading(true);

    try {
      const formData = new FormData();
      formData.append('image', imageFile);
      formData.append('description', description.trim());
      formData.append('latitude', latitude.toString());
      formData.append('longitude', longitude.toString());
      formData.append('citizen_severity', citizenSeverity);

      const response = await fetch('/api/complaints', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server returned error ${response.status}`);
      }

      const created = await response.json();

      // Fetch the full detail to show ML results
      const detailRes = await fetch(`/api/complaints/${created.id}`);
      const detail = detailRes.ok ? await detailRes.json() : null;

      setSuccessData({
        id: created.id,
        status: created.status,
        image_path: created.image_path,
        category: detail?.category || 'Analyzing...',
        severity: detail?.severity || 'Assessing...',
        priority_score: detail?.priority_score,
      });

      // Clear form
      setDescription('');
      setImageFile(null);
      setImagePreview(null);
      if (onComplaintCreated) onComplaintCreated(created.id);
    } catch (err) {
      setErrorMessage(err.message || 'Failed to submit complaint. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setSuccessData(null);
    setDescription('');
    setImageFile(null);
    setImagePreview(null);
    setErrorMessage('');
  };

  return (
    <div className="submission-container">
      <div className="submission-card">
        <div className="card-header">
          <h2>📢 Report a Civic Issue</h2>
          <p>
            Submit an issue with a photo and description. CivicLens AI automatically classifies the category,
            estimates severity, and prioritizes municipal dispatch.
          </p>
        </div>

        {errorMessage && (
          <div className="alert alert-error">
            <span>⚠️ {errorMessage}</span>
          </div>
        )}

        {successData ? (
          <div className="alert alert-success">
            <div className="success-header">
              <span className="success-icon">✅</span>
              <div>
                <h3>Complaint #{successData.id} Submitted Successfully!</h3>
                <p>Status: <span className="badge badge-reported">{successData.status}</span></p>
              </div>
            </div>

            <div className="success-details">
              <div className="detail-item">
                <span className="label">Detected Category:</span>
                <span className="value"><strong>{successData.category}</strong></span>
              </div>
              <div className="detail-item">
                <span className="label">Assessed Severity:</span>
                <span className="value">
                  <span className={`badge badge-severity-${successData.severity?.toLowerCase()}`}>
                    {successData.severity}
                  </span>
                </span>
              </div>
              {successData.priority_score !== undefined && (
                <div className="detail-item">
                  <span className="label">Priority Score:</span>
                  <span className="value">
                    <strong style={{ color: successData.priority_score > 0.6 ? '#dc2626' : '#2563eb' }}>
                      {(successData.priority_score * 100).toFixed(1)}%
                    </strong>
                  </span>
                </div>
              )}
            </div>

            <div className="success-actions">
              <button type="button" className="btn btn-primary" onClick={resetForm}>
                Report Another Issue
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="complaint-form">
            {/* Image Upload */}
            <div className="form-group">
              <label htmlFor="image-input" className="form-label">
                📷 Photo Evidence <span className="required">*</span>
              </label>
              <div className="image-drop-area">
                <input
                  id="image-input"
                  type="file"
                  accept="image/jpeg,image/png,image/webp,image/bmp"
                  onChange={handleImageChange}
                  className="file-input"
                  disabled={loading}
                />
                {!imagePreview ? (
                  <div className="upload-placeholder">
                    <span className="upload-icon">📁</span>
                    <span>Click or drag image here to upload</span>
                    <small>Supports JPG, PNG, WEBP</small>
                  </div>
                ) : (
                  <div className="preview-wrapper">
                    <img src={imagePreview} alt="Preview" className="image-preview" />
                    <button
                      type="button"
                      className="btn-remove-image"
                      onClick={() => {
                        setImageFile(null);
                        setImagePreview(null);
                      }}
                      disabled={loading}
                    >
                      ✕ Change Image
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Description */}
            <div className="form-group">
              <label htmlFor="description-input" className="form-label">
                📝 Description <span className="required">*</span>
              </label>
              <textarea
                id="description-input"
                rows="4"
                className="form-textarea"
                placeholder="Describe the issue in detail (e.g., Deep pothole near intersection causing vehicle damage, waterlogging for 3 days)..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                disabled={loading}
                minLength="10"
                required
              />
              <div className="char-count">
                {description.length} characters (min 10)
              </div>
            </div>

            {/* Citizen Severity */}
            <div className="form-group">
              <label htmlFor="severity-select" className="form-label">
                ⚡ Your Severity Rating <span className="required">*</span>
              </label>
              <select
                id="severity-select"
                className="form-select"
                value={citizenSeverity}
                onChange={(e) => setCitizenSeverity(e.target.value)}
                disabled={loading}
              >
                <option value="Minor">Minor (Small inconvenience, no immediate danger)</option>
                <option value="Moderate">Moderate (Noticeable disruption or recurring issue)</option>
                <option value="Severe">Severe (Urgent hazard, blocked transit, accident risk)</option>
              </select>
            </div>

            {/* Location Map Picker */}
            <div className="form-group">
              <label className="form-label">
                📍 Incident Location <span className="required">*</span>
              </label>
              <LocationPickerMap
                latitude={latitude}
                longitude={longitude}
                onLocationSelect={(lat, lon) => {
                  setLatitude(lat);
                  setLongitude(lon);
                }}
              />
              <div className="coords-display">
                <span>Lat: {latitude}</span>
                <span>Lng: {longitude}</span>
              </div>
            </div>

            {/* Submit Button & Loading State */}
            <div className="form-actions">
              <button
                type="submit"
                className="btn btn-primary btn-submit"
                disabled={loading}
              >
                {loading ? (
                  <span className="spinner-wrapper">
                    <span className="spinner"></span>
                    <span>AI Analyzing & Submitting Complaint...</span>
                  </span>
                ) : (
                  '🚀 Submit Complaint'
                )}
              </button>
            </div>

            {loading && (
              <div className="loading-steps">
                <p>⚙️ Executing AI Classification & Multimodal Severity Assessment...</p>
              </div>
            )}
          </form>
        )}
      </div>
    </div>
  );
}
