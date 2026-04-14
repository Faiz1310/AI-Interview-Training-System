/**
 * ScoreCard Component
 * Displays overall performance score with transparent breakdown
 * Shows how each metric (correctness, clarity, confidence) contributes to overall score
 */

import React from 'react';
import { Award } from 'lucide-react';

export function ScoreCard({ feedback }) {
  const scoreColor =
    feedback.overall_score >= 85
      ? 'from-green-600 to-green-700'
      : feedback.overall_score >= 70
      ? 'from-blue-600 to-blue-700'
      : feedback.overall_score >= 50
      ? 'from-yellow-600 to-yellow-700'
      : 'from-red-600 to-red-700';

  const breakdown = feedback.score_breakdown;

  return (
    <div className={`bg-gradient-to-br ${scoreColor} rounded-lg p-8 text-white shadow-lg`}>
      <div className="flex justify-between items-start mb-6">
        <div>
          <h3 className="text-lg font-semibold opacity-90">Overall Performance Score</h3>
          <p className="text-5xl font-bold mt-2">{feedback.overall_score}</p>
          <p className="text-lg mt-2 opacity-90">{feedback.performance_label}</p>
        </div>
        <Award size={48} className="opacity-80" />
      </div>

      {/* Score Breakdown - Explainable Components */}
      {breakdown && (
        <div className="mt-6 pt-6 border-t border-white/20">
          <h4 className="text-sm font-semibold opacity-90 mb-4">Score Breakdown</h4>
          <div className="space-y-3">
            {/* Correctness Contribution */}
            <div className="bg-white/10 rounded-lg p-3">
              <div className="flex justify-between items-center mb-1">
                <span className="text-sm">Correctness (50% weight)</span>
                <span className="font-bold">{breakdown.correctness.contribution.toFixed(1)} pts</span>
              </div>
              <div className="text-xs opacity-80">
                Score: {breakdown.correctness.score}/100 × 50% = {breakdown.correctness.contribution.toFixed(2)}
              </div>
            </div>

            {/* Clarity Contribution */}
            <div className="bg-white/10 rounded-lg p-3">
              <div className="flex justify-between items-center mb-1">
                <span className="text-sm">Clarity (30% weight)</span>
                <span className="font-bold">{breakdown.clarity.contribution.toFixed(1)} pts</span>
              </div>
              <div className="text-xs opacity-80">
                Score: {breakdown.clarity.score}/100 × 30% = {breakdown.clarity.contribution.toFixed(2)}
              </div>
            </div>

            {/* Confidence Contribution */}
            <div className="bg-white/10 rounded-lg p-3">
              <div className="flex justify-between items-center mb-1">
                <span className="text-sm">Confidence (20% weight)</span>
                <span className="font-bold">{breakdown.confidence.contribution.toFixed(1)} pts</span>
              </div>
              <div className="text-xs opacity-80">
                Score: {breakdown.confidence.score}/100 × 20% = {breakdown.confidence.contribution.toFixed(2)}
              </div>
            </div>
          </div>

          {/* Behavior Note - Independent of Score */}
          <div className="mt-4 pt-4 border-t border-white/20">
            <div className="text-xs opacity-80">
              <span className="font-semibold">📌 Important:</span> {breakdown.behavior.note}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
