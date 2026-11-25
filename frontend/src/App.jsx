import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import Navbar from './components/Navbar';
import CitizenDashboard from './pages/CitizenDashboard';
import AuthorityDashboard from './components/AuthorityDashboard';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import './App.css';

function AppContent() {
  const { user, role, logout } = useAuth();
  const [currentPath, setCurrentPath] = useState(() => window.location.pathname || '/login');

  const navigate = (path) => {
    window.history.pushState({}, '', path);
    setCurrentPath(path);
  };

  useEffect(() => {
    const handlePopState = () => {
      setCurrentPath(window.location.pathname || '/');
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // Handle role-based redirects and route protection
  useEffect(() => {
    if (!user) {
      if (currentPath === '/register') {
        // Allow register page
      } else if (currentPath !== '/login') {
        navigate('/login');
      }
    } else {
      // User is logged in
      if (role === 'citizen') {
        if (currentPath === '/login' || currentPath === '/register' || currentPath === '/' || currentPath.startsWith('/authority')) {
          navigate('/citizen');
        }
      } else if (role === 'authority') {
        if (currentPath === '/login' || currentPath === '/register' || currentPath === '/' || currentPath.startsWith('/citizen')) {
          navigate('/authority');
        }
      }
    }
  }, [user, role, currentPath]);

  const renderContent = () => {
    if (!user) {
      if (currentPath === '/register') {
        return <RegisterPage onSwitchToLogin={() => navigate('/login')} />;
      }
      return <LoginPage onSwitchToRegister={() => navigate('/register')} />;
    }

    if (role === 'citizen') {
      return <CitizenDashboard onLogout={logout} />;
    }

    if (role === 'authority') {
      return <AuthorityDashboard onLogout={logout} />;
    }

    return <div className="alert alert-error">Unknown user role: {role}</div>;
  };

  return (
    <div className="app-shell">
      <Navbar currentPath={currentPath} onNavigate={navigate} />

      <main className="main-content">
        {renderContent()}
      </main>

      <footer className="app-footer">
        <p>
          CivicLens V1.0 &copy; 2026 &middot; Multimodal AI Issue Classification &middot; Explainable Priority Engine
        </p>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
