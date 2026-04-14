import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Plus, TrendingUp, BarChart3, Award, Trash2, Eye } from 'lucide-react';
import { ConfirmDialog } from './ConfirmDialog';
import { Toast } from './Toast';
import { sessionService } from '../services/sessionService';
import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
} from 'chart.js';
import { Radar, Line } from 'react-chartjs-2';

ChartJS.register(
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale
);

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function DashboardPage({ onNavigate, refreshKey, selectedResumeId, onResumeSelect }) {
  const [resumes, setResumes] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [switchingResume, setSwitchingResume] = useState(false);
  const requestAbortRef = useRef(null);

  // Delete session state ─────────────────────────────────────────────────
  const [confirmDialog, setConfirmDialog] = useState({
    isOpen: false,
    sessionId: null,
    sessionDate: null,
  });
  const [deletingId, setDeletingId] = useState(null);
  const [toast, setToast] = useState({
    message: '',
    type: 'success', // 'success' | 'error'
  });

  useEffect(() => {
    loadResumesAndDashboard();
  }, [refreshKey]);

  const loadResumesAndDashboard = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const headers = { 'Authorization': `Bearer ${token}` };
      const resumesRes = await axios.get(`${API_URL}/resumes`, { headers });
      setResumes(resumesRes.data);

      if (resumesRes.data.length === 0) {
        setDashboard({ session_summary: [], progress_trend: [], skill_breakdown_average: {}, total_completed: 0 });
        setAnalytics({ total_sessions: 0, average_overall: 0, best_session: 0, improvement_rate: 0 });
        return;
      }

      const defaultResumeId = typeof selectedResumeId === 'number'
        ? selectedResumeId
        : resumesRes.data[0].id;

      if (typeof selectedResumeId !== 'number' && onResumeSelect) {
        onResumeSelect(defaultResumeId);
      }

      await fetchDashboardForResume(defaultResumeId, false);
    } catch (err) {
      console.error('Failed to load data:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchDashboardForResume = async (resumeId, isSwitch = false) => {
    if (!resumeId) return;

    if (requestAbortRef.current) {
      requestAbortRef.current.abort();
    }

    const controller = new AbortController();
    requestAbortRef.current = controller;

    if (isSwitch) {
      setSwitchingResume(true);
      setDashboard(null);
      setAnalytics(null);
    }

    try {
      const token = localStorage.getItem('access_token');
      const headers = { 'Authorization': `Bearer ${token}` };
      const [dashRes, analyticsRes] = await Promise.all([
        axios.get(`${API_URL}/dashboard?resume_id=${resumeId}`, { headers, signal: controller.signal }),
        axios.get(`${API_URL}/analytics/summary?resume_id=${resumeId}`, { headers, signal: controller.signal }),
      ]);

      setDashboard(dashRes.data);
      setAnalytics(analyticsRes.data);
    } catch (err) {
      if (err.name === 'CanceledError' || axios.isCancel?.(err)) {
        return;
      }
      console.error('Failed to load dashboard for resume:', err);
    } finally {
      setSwitchingResume(false);
    }
  };

  const handleResumeChange = async (e) => {
    const nextResumeId = Number(e.target.value);
    if (!nextResumeId || nextResumeId === selectedResumeId) return;
    onResumeSelect?.(nextResumeId);
    await fetchDashboardForResume(nextResumeId, true);
  };

  // ─ DELETE SESSION HANDLERS ─────────────────────────────────────────────
  const handleDeleteClick = (sessionId, sessionDate) => {
    setConfirmDialog({
      isOpen: true,
      sessionId,
      sessionDate,
    });
  };

  const handleCancelDelete = () => {
    setConfirmDialog({ isOpen: false, sessionId: null, sessionDate: null });
  };

  const handleConfirmDelete = async () => {
    const { sessionId } = confirmDialog;
    if (!sessionId) return;

    setDeletingId(sessionId);

    try {
      const result = await sessionService.deleteSession(sessionId);

      if (result.success) {
        // ✅ SAFE STATE UPDATE: Only remove from UI AFTER confirmed success
        setDashboard((prev) => ({
          ...prev,
          session_summary: prev.session_summary.filter((s) => s.session_id !== sessionId),
          total_completed: Math.max(0, (prev.total_completed || 0) - 1),
        }));

        // Show success message
        setToast({
          message: `Session deleted successfully (${result.data.deleted_records.answers} answers removed)`,
          type: 'success',
        });

        // Refetch analytics to update summary stats
        if (selectedResumeId) {
          try {
            const token = localStorage.getItem('access_token');
            const headers = { Authorization: `Bearer ${token}` };
            const analyticsRes = await axios.get(
              `${API_URL}/analytics/summary?resume_id=${selectedResumeId}`,
              { headers }
            );
            setAnalytics(analyticsRes.data);
          } catch (err) {
            console.error('Failed to refresh analytics:', err);
          }
        }

        // Close dialog only on success
        setConfirmDialog({ isOpen: false, sessionId: null, sessionDate: null });
      } else {
        // ✅ RETRY HANDLING: Keep dialog open for retry (except on auth failures)
        const isAuthError = !result.isRetryable || result.statusCode === 401 || result.statusCode === 400;

        // Show error message
        setToast({
          message: result.message,
          type: 'error',
        });

        // Close dialog only on non-retryable errors (auth, validation)
        if (isAuthError) {
          setDeletingId(null);
          setConfirmDialog({ isOpen: false, sessionId: null, sessionDate: null });
        } else {
          // ✅ 409 CONFLICT HANDLING: Keep dialog and loading state for retry
          // User can click "Delete" again to retry after processing completes
          setDeletingId(null);
          // Dialog stays open
        }
      }
    } catch (error) {
      console.error('Unexpected error during delete:', error);
      setToast({
        message: 'An unexpected error occurred. Please try again.',
        type: 'error',
      });
      setDeletingId(null);
      // Keep dialog open for retry on unexpected errors
    }
  };

  useEffect(() => {
    return () => {
      if (requestAbortRef.current) {
        requestAbortRef.current.abort();
      }
    };
  }, []);

  if (loading || switchingResume) {
    return <div className="text-white text-center py-12">Loading dashboard...</div>;
  }

  const skillAvg = dashboard?.skill_breakdown_average || {};
  const hasSkillData = skillAvg.correctness > 0 || skillAvg.clarity > 0 || skillAvg.confidence > 0;
  const progressTrend = dashboard?.progress_trend || [];

  // Radar chart data
  const radarData = {
    labels: ['Correctness', 'Clarity', 'Confidence'],
    datasets: [
      {
        label: 'Average Skills',
        data: [
          skillAvg.correctness || 0,
          skillAvg.clarity || 0,
          skillAvg.confidence || 0,
        ],
        backgroundColor: 'rgba(59, 130, 246, 0.2)',
        borderColor: 'rgba(59, 130, 246, 1)',
        borderWidth: 2,
        pointBackgroundColor: 'rgba(59, 130, 246, 1)',
        pointBorderColor: '#fff',
        pointRadius: 4,
      },
    ],
  };

  const radarOptions = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      r: {
        min: 0,
        max: 100,
        ticks: {
          stepSize: 20,
          color: '#94a3b8',
          backdropColor: 'transparent',
        },
        grid: { color: 'rgba(148, 163, 184, 0.15)' },
        angleLines: { color: 'rgba(148, 163, 184, 0.15)' },
        pointLabels: { color: '#e2e8f0', font: { size: 13 } },
      },
    },
    plugins: {
      legend: { display: false },
    },
  };

  // Line chart for progress trends
  const trendData = {
    labels: progressTrend.map((s, i) => `Session ${i + 1}`),
    datasets: [
      {
        label: 'Overall Score',
        data: progressTrend.map((s) => s.overall_score),
        borderColor: 'rgba(59, 130, 246, 1)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        fill: true,
        tension: 0.3,
        pointRadius: 4,
        pointBackgroundColor: 'rgba(59, 130, 246, 1)',
      },
    ],
  };

  const trendOptions = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      y: {
        min: 0,
        max: 100,
        ticks: { color: '#94a3b8' },
        grid: { color: 'rgba(148, 163, 184, 0.1)' },
      },
      x: {
        ticks: { color: '#94a3b8' },
        grid: { color: 'rgba(148, 163, 184, 0.05)' },
      },
    },
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          afterLabel: (ctx) => {
            const item = progressTrend[ctx.dataIndex];
            return item?.job_role ? `Role: ${item.job_role}` : '';
          },
        },
      },
    },
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-3xl font-bold text-white">Dashboard</h2>
        <div className="flex gap-3 items-center">
          {resumes.length > 0 && (
            <select
              value={selectedResumeId || resumes[0]?.id || ''}
              onChange={handleResumeChange}
              className="px-3 py-2 bg-slate-800 border border-slate-600 text-white rounded-lg"
            >
              {resumes.map((resume) => (
                <option key={resume.id} value={resume.id}>
                  {resume.job_role} ({resume.filename})
                </option>
              ))}
            </select>
          )}
          <button
            onClick={() => onNavigate('interview', selectedResumeId || resumes[0]?.id)}
            className="flex items-center gap-2 px-6 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition"
          >
            Practice Interview
          </button>
          <button
            onClick={() => onNavigate('upload')}
            className="flex items-center gap-2 px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition"
          >
            <Plus size={20} />
            Upload Resume
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-slate-800 p-5 rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-slate-400 text-sm font-medium">Sessions</h3>
              <p className="text-3xl font-bold text-white mt-1">{dashboard?.total_completed || 0}</p>
            </div>
            <BarChart3 className="text-blue-400" size={28} />
          </div>
        </div>

        <div className="bg-slate-800 p-5 rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-slate-400 text-sm font-medium">Avg Score</h3>
              <p className="text-3xl font-bold text-white mt-1">
                {analytics?.average_overall ? analytics.average_overall.toFixed(1) : '--'}
              </p>
            </div>
            <TrendingUp className="text-green-400" size={28} />
          </div>
        </div>

        <div className="bg-slate-800 p-5 rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-slate-400 text-sm font-medium">Best Score</h3>
              <p className="text-3xl font-bold text-white mt-1">
                {analytics?.best_session ? analytics.best_session.toFixed(1) : '--'}
              </p>
            </div>
            <Award className="text-yellow-400" size={28} />
          </div>
        </div>

        <div className="bg-slate-800 p-5 rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-slate-400 text-sm font-medium">Improvement</h3>
              <p className={`text-3xl font-bold mt-1 ${(analytics?.improvement_rate || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {analytics?.improvement_rate != null ? `${analytics.improvement_rate >= 0 ? '+' : ''}${analytics.improvement_rate.toFixed(1)}` : '--'}
              </p>
            </div>
            <TrendingUp className={`${(analytics?.improvement_rate || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`} size={28} />
          </div>
        </div>
      </div>

      {/* Charts */}
      {hasSkillData && (
        <div className="grid grid-cols-2 gap-6">
          {/* Radar Chart */}
          <div className="bg-slate-800 p-6 rounded-lg">
            <h3 className="text-lg font-semibold text-white mb-4">Skill Breakdown</h3>
            <div style={{ height: '280px' }}>
              <Radar data={radarData} options={radarOptions} />
            </div>
            <div className="mt-4 grid grid-cols-3 gap-2 text-center">
              <div>
                <p className="text-slate-400 text-xs">Correctness</p>
                <p className="text-white font-bold">{(skillAvg.correctness || 0).toFixed(1)}</p>
              </div>
              <div>
                <p className="text-slate-400 text-xs">Clarity</p>
                <p className="text-white font-bold">{(skillAvg.clarity || 0).toFixed(1)}</p>
              </div>
              <div>
                <p className="text-slate-400 text-xs">Confidence</p>
                <p className="text-white font-bold">{(skillAvg.confidence || 0).toFixed(1)}</p>
              </div>
            </div>
          </div>

          {/* Trend Chart */}
          <div className="bg-slate-800 p-6 rounded-lg">
            <h3 className="text-lg font-semibold text-white mb-4">Performance Trend</h3>
            {progressTrend.length >= 2 ? (
              <div style={{ height: '280px' }}>
                <Line data={trendData} options={trendOptions} />
              </div>
            ) : (
              <div className="flex items-center justify-center h-64 text-slate-500">
                Complete 2+ sessions to see your progress trend
              </div>
            )}
            {analytics?.performance_label && (
              <div className="mt-4 p-3 bg-slate-700/50 rounded-lg">
                <p className="text-sm text-slate-300">
                  <span className="font-medium text-blue-400">{analytics.performance_label}</span>
                  {analytics.primary_weakness && analytics.primary_weakness !== 'N/A' && (
                    <span> — Focus area: {analytics.primary_weakness}</span>
                  )}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Coach Message */}
      {analytics?.coach_message && analytics.total_sessions > 0 && (
        <div className="bg-slate-800 p-6 rounded-lg border-l-4 border-blue-500">
          <h3 className="text-white font-semibold mb-2">Coach Recommendation</h3>
          <p className="text-slate-300">{analytics.coach_message}</p>
        </div>
      )}

      {/* Session History */}
      {dashboard?.session_summary?.length > 0 && (
        <div className="bg-slate-800 rounded-lg overflow-hidden">
          <div className="p-6 border-b border-slate-700">
            <h3 className="text-lg font-semibold text-white">Session History</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-700/50">
                <tr>
                  <th className="text-left p-3 text-slate-400 font-medium">Date</th>
                  <th className="text-left p-3 text-slate-400 font-medium">Role</th>
                  <th className="text-center p-3 text-slate-400 font-medium">Questions</th>
                  <th className="text-center p-3 text-slate-400 font-medium">Score Breakdown</th>
                  <th className="text-center p-3 text-slate-400 font-medium">Behavior</th>
                  <th className="text-center p-3 text-slate-400 font-medium">Label</th>
                  <th className="text-center p-3 text-slate-400 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700">
                {dashboard.session_summary.slice().reverse().map((s) => (
                  <tr key={s.session_id} className="hover:bg-slate-700/30">
                    <td className="p-3 text-slate-300">
                      {s.created_at ? new Date(s.created_at).toLocaleDateString() : '--'}
                    </td>
                    <td className="p-3 text-white">{s.job_role}</td>
                    <td className="p-3 text-center text-slate-300">{s.questions_answered}</td>
                    <td className="p-3 text-center">
                      <div className="text-white font-semibold">{s.overall_score.toFixed(0)}</div>
                      <div className="text-xs text-slate-400 mt-1">
                        C:{s.correctness_score.toFixed(0)} | 
                        Cl:{s.clarity_score.toFixed(0)} | 
                        Cf:{s.confidence_score.toFixed(0)}
                      </div>
                    </td>
                    <td className="p-3 text-center">
                      <span className="text-xs px-2 py-1 inline-block">
                        ✅ No issues
                      </span>
                    </td>
                    <td className="p-3 text-center">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        s.overall_score >= 85 ? 'bg-green-600/20 text-green-400' :
                        s.overall_score >= 70 ? 'bg-blue-600/20 text-blue-400' :
                        s.overall_score >= 50 ? 'bg-yellow-600/20 text-yellow-400' :
                        'bg-red-600/20 text-red-400'
                      }`}>
                        {s.performance_label || '--'}
                      </span>
                    </td>
                    <td className="p-3 text-center">
                      <div className="flex gap-2 justify-center">
                        <button
                          onClick={() => onNavigate('feedback', null, s.session_id)}
                          className="px-3 py-1 text-sm text-blue-400 hover:bg-blue-900/20 rounded transition focus:outline-none focus:ring-2 focus:ring-blue-600"
                          title="View AI Analysis for this session"
                          aria-label="View AI Analysis"
                        >
                          View AI Analysis
                        </button>
                        <button
                          onClick={() => handleDeleteClick(s.session_id, s.created_at)}
                          disabled={deletingId === s.session_id}
                          className="p-2 text-red-400 hover:bg-red-900/20 rounded transition disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-red-600"
                          title="Delete session"
                          aria-label={`Delete session from ${s.created_at ? new Date(s.created_at).toLocaleDateString() : 'unknown date'}`}
                        >
                          <Trash2 size={18} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Resumes List */}
      {resumes.length > 0 && (
        <div className="bg-slate-800 rounded-lg overflow-hidden">
          <div className="p-6 border-b border-slate-700">
            <h3 className="text-lg font-semibold text-white">Your Resumes</h3>
          </div>
          <div className="divide-y divide-slate-700">
            {resumes.map((resume) => (
              <div key={resume.id} className="p-6 hover:bg-slate-700/50 transition">
                <div className="flex justify-between items-start">
                  <div>
                    <h4 className="text-white font-medium">{resume.job_role}</h4>
                    <p className="text-slate-400 text-sm mt-1">{resume.filename}</p>
                    <p className="text-slate-500 text-xs mt-2">
                      Uploaded: {new Date(resume.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-4">
                    {resume.analysis_score && (
                      <div className="text-right">
                        <p className="text-2xl font-bold text-green-400">{resume.analysis_score}</p>
                        <p className="text-slate-400 text-sm">Score</p>
                      </div>
                    )}
                    <button
                      onClick={() => onNavigate('interview', resume.id)}
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition text-sm"
                    >
                      Start Interview
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {dashboard && resumes.length > 0 && dashboard.total_completed === 0 && (
        <div className="bg-slate-800 p-8 rounded-lg text-center">
          <p className="text-slate-400">No completed sessions for this resume yet. Start an interview to build analytics.</p>
        </div>
      )}

      {resumes.length === 0 && (
        <div className="bg-slate-800 p-12 rounded-lg text-center">
          <p className="text-slate-400 mb-4">No resumes yet. Upload one to get started!</p>
          <button
            onClick={() => onNavigate('upload')}
            className="inline-flex items-center gap-2 px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
          >
            <Plus size={20} />
            Upload Your First Resume
          </button>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        isOpen={confirmDialog.isOpen}
        title="Delete Session"
        message="Are you sure you want to delete this session? This action cannot be undone."
        cancelText="Cancel"
        confirmText="Delete"
        isDangerous={true}
        isLoading={deletingId === confirmDialog.sessionId}
        onCancel={handleCancelDelete}
        onConfirm={handleConfirmDelete}
      />

      {/* Success/Error Toast */}
      <Toast
        message={toast.message}
        type={toast.type}
        onClose={() => setToast({ message: '', type: 'success' })}
      />
    </div>
  );
}
