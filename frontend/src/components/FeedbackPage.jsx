import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { AlertCircle } from 'lucide-react';
import { ScoreCard } from './feedback/ScoreCard';
import { StatsGrid } from './feedback/StatsGrid';
import { ChartsSection } from './feedback/ChartsSection';
import { StrengthsSection } from './feedback/StrengthsSection';
import { WeaknessesSection } from './feedback/WeaknessesSection';
import { BehaviorSection } from './feedback/BehaviorSection';
import { RecommendationsSection } from './feedback/RecommendationsSection';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function FeedbackPage({ sessionId, onNavigate }) {
  const [feedback, setFeedback] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadFeedback();
  }, [sessionId]);

  const loadFeedback = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('access_token');
      const headers = { 'Authorization': `Bearer ${token}` };
      
      const response = await axios.get(
        `${API_URL}/session/${sessionId}/feedback`,
        { headers }
      );
      
      setFeedback(response.data);
      setError(null);
    } catch (err) {
      console.error('Failed to load feedback:', err);
      setError(err.response?.data?.detail || 'Failed to load feedback');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="text-white text-center py-12">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-blue-500" />
        <p className="mt-4">Loading your feedback...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-700 rounded-lg p-6 text-red-300">
        <div className="flex items-center gap-2 mb-2">
          <AlertCircle size={20} />
          <h3 className="font-semibold">Error Loading Feedback</h3>
        </div>
        <p>{error}</p>
        <button
          onClick={loadFeedback}
          className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded transition"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!feedback) {
    return <div className="text-white text-center py-12">No feedback available</div>;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-3xl font-bold text-white">Interview Feedback</h2>
        <button
          onClick={() => onNavigate('dashboard')}
          className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition"
        >
          Back to Dashboard
        </button>
      </div>

      {/* Scoring Explanation */}
      <div className="bg-gradient-to-r from-blue-900/20 to-purple-900/20 border border-blue-700/30 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <div className="text-blue-400 text-lg">ℹ️</div>
          <div>
            <h3 className="font-semibold text-white mb-2">How Your Score is Calculated</h3>
            <p className="text-slate-300 text-sm">
              Your overall score is based on three dimensions: 
              <span className="text-blue-300 font-medium"> Correctness (50%)</span> — technical accuracy,
              <span className="text-green-300 font-medium"> Clarity (30%)</span> — communication quality, and
              <span className="text-purple-300 font-medium"> Confidence (20%)</span> — delivery and presence.
            </p>
            <p className="text-slate-400 text-xs mt-2">
              🔒 Note: Behavioral factors like eye contact and speech pace are evaluated separately and never reduce your technical scores.
            </p>
          </div>
        </div>
      </div>

      {/* Overall Score Card */}
      <ScoreCard feedback={feedback} />

      {/* Behavior Metrics Summary (if available) */}
      {feedback.behavior_metrics && (
        <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <span>📊</span> Behavioral Assessment
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-slate-700/50 rounded-lg p-4">
              <div className="text-xs text-slate-400 mb-2">Attention Score</div>
              <div className="text-2xl font-bold text-blue-400">{feedback.behavior_metrics.attention_score?.toFixed(1) || 'N/A'}</div>
              <div className="text-xs text-slate-500 mt-1">Eye contact & focus</div>
            </div>
            <div className="bg-slate-700/50 rounded-lg p-4">
              <div className="text-xs text-slate-400 mb-2">Presence Score</div>
              <div className="text-2xl font-bold text-purple-400">{feedback.behavior_metrics.presence_score?.toFixed(1) || 'N/A'}</div>
              <div className="text-xs text-slate-500 mt-1">Composure & stability</div>
            </div>
            <div className="bg-slate-700/50 rounded-lg p-4">
              <div className="text-xs text-slate-400 mb-2">Vocal Confidence</div>
              <div className="text-2xl font-bold text-green-400">{feedback.behavior_metrics.vocal_confidence_score?.toFixed(1) || 'N/A'}</div>
              <div className="text-xs text-slate-500 mt-1">Speech quality & energy</div>
            </div>
            <div className="bg-slate-700/50 rounded-lg p-4">
              <div className="text-xs text-slate-400 mb-2">Attention Level</div>
              <div className="text-lg font-bold text-yellow-400">{feedback.behavior_metrics.attention_level || 'Unknown'}</div>
              <div className="text-xs text-slate-500 mt-1">Overall focus</div>
            </div>
          </div>
          {feedback.behavior_metrics.insights && (
            <div className="mt-4 p-3 bg-slate-900/50 rounded border border-slate-600 text-sm text-slate-300">
              <span className="font-semibold text-slate-200">📈 Insight: </span>
              {feedback.behavior_metrics.insights}
            </div>
          )}
        </div>
      )}

      {/* Stats Grid */}
      <StatsGrid feedback={feedback} />

      {/* Charts */}
      <ChartsSection feedback={feedback} sessionId={sessionId} />

      {/* Strengths Section */}
      {feedback.strengths && feedback.strengths.length > 0 && (
        <StrengthsSection strengths={feedback.strengths} />
      )}

      {/* Weaknesses Section */}
      {feedback.weaknesses && feedback.weaknesses.length > 0 && (
        <WeaknessesSection weaknesses={feedback.weaknesses} />
      )}

      {/* Behavior Feedback Section */}
      {feedback.behavior_feedback && feedback.behavior_feedback.length > 0 && (
        <BehaviorSection behavior={feedback.behavior_feedback} />
      )}

      {/* Recommendations Section */}
      {feedback.final_recommendation && (
        <RecommendationsSection recommendation={feedback.final_recommendation} />
      )}
    </div>
  );
}
