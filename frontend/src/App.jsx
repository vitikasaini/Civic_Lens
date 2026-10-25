import { useState } from 'react';
import Navbar from './components/Navbar';
import CitizenSubmission from './components/CitizenSubmission';
import AuthorityDashboard from './components/AuthorityDashboard';
import './App.css';

export default function App() {
  const [activeTab, setActiveTab] = useState('citizen');

  return (
    <div className="app-shell">
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="main-content">
        {activeTab === 'citizen' ? (
          <CitizenSubmission
            onComplaintCreated={() => {
              // Option to notify or redirect
            }}
          />
        ) : (
          <AuthorityDashboard />
        )}
      </main>

      <footer className="app-footer">
        <p>
          CivicLens V1.0 &copy; 2026 &middot; Multimodal AI Issue Classification &middot; Explainable Priority Engine
        </p>
      </footer>
    </div>
  );
}
