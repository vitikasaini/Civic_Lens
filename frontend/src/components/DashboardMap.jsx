import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Custom colored SVG icons for priority levels
function createPriorityIcon(color) {
  return L.divIcon({
    className: 'custom-map-marker',
    html: `<div style="
      background-color: ${color};
      width: 24px;
      height: 24px;
      border-radius: 50%;
      border: 3px solid white;
      box-shadow: 0 2px 5px rgba(0,0,0,0.4);
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-weight: bold;
      font-size: 11px;
    "></div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -12],
  });
}

const ICONS = {
  high: createPriorityIcon('#ef4444'),    // Red
  medium: createPriorityIcon('#f59e0b'),  // Amber
  low: createPriorityIcon('#10b981'),     // Green
  default: createPriorityIcon('#6b7280'), // Gray
};

export default function DashboardMap({ complaints, onSelectComplaint }) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersLayerRef = useRef(null);

  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (!mapInstanceRef.current) {
      const map = L.map(mapContainerRef.current).setView([28.6139, 77.2090], 12);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 19,
      }).addTo(map);

      markersLayerRef.current = L.layerGroup().addTo(map);
      mapInstanceRef.current = map;
    }

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // Sync markers whenever complaints list changes
  useEffect(() => {
    if (!mapInstanceRef.current || !markersLayerRef.current) return;

    markersLayerRef.current.clearLayers();

    if (!complaints || complaints.length === 0) return;

    const bounds = L.latLngBounds();

    complaints.forEach((c) => {
      if (typeof c.latitude !== 'number' || typeof c.longitude !== 'number') return;

      const priority = c.priority_score ?? 0;
      let icon = ICONS.low;
      if (priority >= 0.60) icon = ICONS.high;
      else if (priority >= 0.35) icon = ICONS.medium;

      const marker = L.marker([c.latitude, c.longitude], { icon });

      const popupContent = `
        <div style="min-width: 160px; font-family: sans-serif; font-size: 13px;">
          <div style="font-weight: bold; margin-bottom: 4px;">#${c.id} · ${c.category || 'Unclassified'}</div>
          <div>Severity: <strong>${c.severity || c.citizen_severity}</strong></div>
          <div>Priority: <strong style="color: ${priority >= 0.6 ? '#dc2626' : '#2563eb'}">${(priority * 100).toFixed(1)}%</strong></div>
          <div style="margin-top: 4px;">Status: <span>${c.status}</span></div>
        </div>
      `;

      marker.bindPopup(popupContent);
      marker.on('popupopen', () => {
        // Can trigger select on click
      });
      marker.on('click', () => {
        if (onSelectComplaint) onSelectComplaint(c.id);
      });

      markersLayerRef.current.addLayer(marker);
      bounds.extend([c.latitude, c.longitude]);
    });

    if (complaints.length > 0 && bounds.isValid()) {
      mapInstanceRef.current.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
    }
  }, [complaints]);

  return (
    <div className="dashboard-map-container">
      <div className="map-legend">
        <span><span className="dot dot-high"></span> High Priority (≥60%)</span>
        <span><span className="dot dot-med"></span> Medium (35-59%)</span>
        <span><span className="dot dot-low"></span> Low (&lt;35%)</span>
      </div>
      <div
        ref={mapContainerRef}
        style={{ height: '320px', width: '100%', borderRadius: '8px' }}
      />
    </div>
  );
}
