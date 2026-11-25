import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';

export default function NotificationBell({ onSelectComplaint }) {
  const { authFetch } = useAuth();
  const [unread, setUnread] = useState(0);
  const [notifications, setNotifications] = useState([]);
  const [open, setOpen] = useState(false);

  const fetchNotifications = useCallback(async () => {
    try {
      const res = await authFetch('/api/notifications');
      if (res.ok) {
        const data = await res.json();
        setNotifications(data.notifications || []);
        setUnread(data.unread_count || 0);
      }
    } catch {
      // silent
    }
  }, [authFetch]);

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, [fetchNotifications]);

  const markRead = async (id) => {
    try {
      await authFetch(`/api/notifications/${id}/read`, { method: 'PATCH' });
      fetchNotifications();
    } catch { /* silent */ }
  };

  const markAllRead = async () => {
    try {
      await authFetch('/api/notifications/read-all', { method: 'PATCH' });
      fetchNotifications();
    } catch { /* silent */ }
  };

  const handleItemClick = (n) => {
    if (!n.is_read) {
      markRead(n.id);
    }
    if (n.complaint_id && onSelectComplaint) {
      onSelectComplaint(n.complaint_id);
      setOpen(false);
    }
  };

  return (
    <div className="notification-bell-wrap" style={{ position: 'relative', display: 'inline-block' }}>
      <button
        className="bell-btn"
        onClick={() => { setOpen((o) => !o); if (!open) fetchNotifications(); }}
        aria-label="Notifications"
        style={{
          background: 'none',
          border: '1px solid #d1d5db',
          borderRadius: '50%',
          padding: '8px 10px',
          cursor: 'pointer',
          fontSize: '16px',
          position: 'relative'
        }}
      >
        🔔
        {unread > 0 && (
          <span
            className="bell-badge"
            style={{
              position: 'absolute',
              top: '-4px',
              right: '-4px',
              backgroundColor: '#ef4444',
              color: 'white',
              fontSize: '11px',
              fontWeight: 'bold',
              borderRadius: '9999px',
              padding: '1px 5px',
            }}
          >
            {unread > 99 ? '99+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div
          className="notif-dropdown"
          style={{
            position: 'absolute',
            right: 0,
            top: '40px',
            width: '320px',
            backgroundColor: 'white',
            borderRadius: '8px',
            boxShadow: '0 4px 15px rgba(0,0,0,0.15)',
            border: '1px solid #e5e7eb',
            zIndex: 1000,
            overflow: 'hidden',
          }}
        >
          <div
            className="notif-dropdown-header"
            style={{
              padding: '10px 14px',
              borderBottom: '1px solid #f3f4f6',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              backgroundColor: '#f9fafb',
            }}
          >
            <strong>Notifications</strong>
            {unread > 0 && (
              <button
                className="link-btn small"
                onClick={markAllRead}
                style={{ background: 'none', border: 'none', color: '#2563eb', cursor: 'pointer', fontSize: '12px' }}
              >
                Mark all read
              </button>
            )}
          </div>

          {notifications.length === 0 ? (
            <div className="notif-empty" style={{ padding: '20px', textAlign: 'center', color: '#6b7280', fontSize: '13px' }}>
              No notifications yet
            </div>
          ) : (
            <ul className="notif-list" style={{ listStyle: 'none', margin: 0, padding: 0, maxHeight: '340px', overflowY: 'auto' }}>
              {notifications.map((n) => (
                <li
                  key={n.id}
                  className={`notif-item ${!n.is_read ? 'notif-unread' : ''}`}
                  onClick={() => handleItemClick(n)}
                  style={{
                    padding: '10px 14px',
                    borderBottom: '1px solid #f3f4f6',
                    cursor: 'pointer',
                    backgroundColor: !n.is_read ? '#eff6ff' : 'white',
                  }}
                >
                  <div className="notif-msg" style={{ fontSize: '13px', color: '#1f2937', marginBottom: '4px' }}>
                    {n.message}
                  </div>
                  <div
                    className="notif-meta"
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      fontSize: '11px',
                      color: '#6b7280',
                    }}
                  >
                    {n.complaint_id && (
                      <span className="notif-id" style={{ fontWeight: 'bold', color: '#3b82f6' }}>
                        #{n.complaint_id}
                      </span>
                    )}
                    <span className="notif-time">{new Date(n.created_at).toLocaleString()}</span>
                    {!n.is_read && (
                      <span className="notif-dot" style={{ color: '#ef4444', fontSize: '10px' }}>
                        ● New
                      </span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
