import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix Leaflet's default marker icon paths in bundled environments
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

export default function LocationPickerMap({ latitude, longitude, onLocationSelect }) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markerRef = useRef(null);

  // Default coordinates: New Delhi center (28.6139, 77.2090)
  const defaultLat = latitude || 28.6139;
  const defaultLon = longitude || 77.2090;

  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (!mapInstanceRef.current) {
      const map = L.map(mapContainerRef.current).setView([defaultLat, defaultLon], 13);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 19,
      }).addTo(map);

      mapInstanceRef.current = map;

      // Handle map click
      map.on('click', (e) => {
        const { lat, lng } = e.latlng;
        onLocationSelect(parseFloat(lat.toFixed(6)), parseFloat(lng.toFixed(6)));
      });
    }

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // Update marker position when latitude/longitude props change
  useEffect(() => {
    if (!mapInstanceRef.current) return;

    if (latitude && longitude) {
      if (markerRef.current) {
        markerRef.current.setLatLng([latitude, longitude]);
      } else {
        const marker = L.marker([latitude, longitude], {
          draggable: true,
        }).addTo(mapInstanceRef.current);

        marker.on('dragend', (e) => {
          const { lat, lng } = e.target.getLatLng();
          onLocationSelect(parseFloat(lat.toFixed(6)), parseFloat(lng.toFixed(6)));
        });

        markerRef.current = marker;
      }
      mapInstanceRef.current.panTo([latitude, longitude]);
    } else if (markerRef.current) {
      markerRef.current.remove();
      markerRef.current = null;
    }
  }, [latitude, longitude]);

  return (
    <div className="location-picker-wrapper">
      <div
        ref={mapContainerRef}
        style={{ height: '240px', width: '100%', borderRadius: '8px', zIndex: 1 }}
      />
      <div className="location-hint">
        {latitude && longitude ? (
          <span>📍 Selected: <strong>{latitude.toFixed(5)}, {longitude.toFixed(5)}</strong> (drag pin or click map to change)</span>
        ) : (
          <span>ℹ️ Click anywhere on the map to set incident location</span>
        )}
      </div>
    </div>
  );
}
