import React, { useState, useEffect } from 'react';
import { LogOut, Zap } from 'lucide-react';
import './App.css';
import { authService } from './services/authService';
import { LoginRegisterPage } from './components/LoginRegisterPage';
import { DashboardPage } from './components/DashboardPage';
import { ResumeUploadPage } from './components/ResumeUploadPage';
import { InterviewPage } from './components/InterviewPage';
import { FeedbackPage } from './components/FeedbackPage';
import { ForgotPasswordPage } from './components/ForgotPasswordPage';
import { ResetPasswordPage } from './components/ResetPasswordPage';

function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [loading, setLoading] = useState(true);
  const [dashboardRefresh, setDashboardRefresh] = useState(0);
  const [selectedResumeId, setSelectedResumeId] = useState(null);
  const [selectedSessionId, setSelectedSessionId] = useState(null);

  useEffect(() => {
    const pathname = window.location.pathname.toLowerCase();
    const requestedAuthPage = pathname.includes('reset-password')
      ? 'reset-password'
      : pathname.includes('forgot-password')
      ? 'forgot-password'
      : pathname.includes('login')
      ? 'login'
      : null;

    const token = localStorage.getItem('access_token');
    if (token) {
      authService.getMe(token).then((result) => {
        if (result.success) {
          setCurrentUser(result.data);
          setCurrentPage('dashboard');
        } else {
          localStorage.removeItem('access_token');
          setCurrentPage('login');
        }
        setLoading(false);
      });
    } else {
      setCurrentPage(requestedAuthPage || 'login');
      setLoading(false);
    }
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    setCurrentUser(null);
    setCurrentPage('login');
  };

  const handleLoginSuccess = (data) => {
    localStorage.setItem('access_token', data.access_token);
    setCurrentUser(data.user);
    setCurrentPage('dashboard');
  };

  const handleNavigate = (page, resumeId, sessionId) => {
    if (typeof resumeId === 'number') {
      setSelectedResumeId(resumeId);
    }
    if (typeof sessionId === 'number') {
      setSelectedSessionId(sessionId);
    }

    if (!currentUser) {
      if (page === 'forgot-password') {
        window.history.replaceState({}, '', '/forgot-password');
      } else if (page === 'reset-password') {
        const qs = window.location.search || '';
        window.history.replaceState({}, '', `/reset-password${qs}`);
      } else if (page === 'login' || page === 'register') {
        window.history.replaceState({}, '', '/login');
      }
    }

    setCurrentPage(page);
  };

  if (loading) {
    return <div className="flex items-center justify-center h-screen text-white">Loading...</div>;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {currentUser && (
        <header className="border-b border-slate-700 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
            <div
              className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition"
              onClick={() => handleNavigate('dashboard')}
            >
              <Zap className="text-blue-400" size={28} />
              <div>
                <h1 className="text-2xl font-bold text-white">LetsTrain.ai</h1>
                <p className="text-xs text-slate-400">Master Interview Skills</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-slate-300 text-sm">Welcome, <span className="font-medium text-blue-400">{currentUser.name}</span></span>
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition"
              >
                <LogOut size={18} />
                Logout
              </button>
            </div>
          </div>
        </header>
      )}

      <main className="max-w-7xl mx-auto px-4 py-8">
        {!currentUser ? (
          currentPage === 'login' || currentPage === 'register' ? (
            <LoginRegisterPage 
              onLoginSuccess={handleLoginSuccess}
              onNavigate={handleNavigate}
            />
          ) : currentPage === 'forgot-password' ? (
            <ForgotPasswordPage onNavigate={handleNavigate} />
          ) : currentPage === 'reset-password' ? (
            <ResetPasswordPage onNavigate={handleNavigate} />
          ) : null
        ) : currentPage === 'dashboard' ? (
          <DashboardPage
            onNavigate={handleNavigate}
            refreshKey={dashboardRefresh}
            selectedResumeId={selectedResumeId}
            onResumeSelect={setSelectedResumeId}
          />
        ) : currentPage === 'upload' ? (
          <ResumeUploadPage
            onBack={() => handleNavigate('dashboard')}
            onSuccess={(resumeId, targetPage = 'dashboard') => handleNavigate(targetPage, resumeId)}
          />
        ) : currentPage === 'interview' ? (
          <InterviewPage
            resumeId={selectedResumeId}
            onBack={() => handleNavigate('dashboard')}
            onSessionComplete={() => setDashboardRefresh(d => d + 1)}
          />
        ) : currentPage === 'feedback' ? (
          <FeedbackPage
            sessionId={selectedSessionId}
            onNavigate={handleNavigate}
          />
        ) : null}
      </main>
    </div>
  );
}

export default App;
