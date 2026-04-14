/**
 * ChartsSection Component
 * Displays performance visualization with skill breakdown and progress tracking
 * Shows score breakdown and performance trends
 */

import React from 'react';
import { BarChart3, Award } from 'lucide-react';
import { Bar } from 'react-chartjs-2';

export function ChartsSection({ feedback }) {
  const skillChartData = {
    labels: ['Correctness', 'Clarity', 'Confidence'],
    datasets: [
      {
        label: 'Average Score',
        data: [feedback.avg_correctness, feedback.avg_clarity, feedback.avg_confidence],
        backgroundColor: [
          'rgba(34, 197, 94, 0.6)',
          'rgba(59, 130, 246, 0.6)',
          'rgba(234, 179, 8, 0.6)',
        ],
        borderColor: ['rgb(34, 197, 94)', 'rgb(59, 130, 246)', 'rgb(234, 179, 8)'],
        borderWidth: 2,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: { color: '#e2e8f0' },
      },
    },
    scales: {
      y: {
        min: 0,
        max: 100,
        ticks: { color: '#94a3b8' },
        grid: { color: 'rgba(148, 163, 184, 0.1)' },
      },
      x: {
        ticks: { color: '#94a3b8' },
        grid: { color: 'rgba(148, 163, 184, 0.1)' },
      },
    },
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Skill Breakdown */}
      <div className="bg-slate-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <BarChart3 size={20} className="text-blue-400" />
          Skill Breakdown
        </h3>
        <div style={{ height: '300px' }}>
          <Bar data={skillChartData} options={chartOptions} />
        </div>
      </div>

      {/* Performance Progress */}
      <div className="bg-slate-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Award size={20} className="text-yellow-400" />
          Performance Summary
        </h3>
        <div className="space-y-4">
          <div>
            <div className="flex justify-between mb-2">
              <span className="text-slate-300">Correctness</span>
              <span className="text-green-400 font-semibold">{feedback.avg_correctness.toFixed(1)}%</span>
            </div>
            <div className="bg-slate-700 rounded-full h-2">
              <div
                className="bg-green-500 h-2 rounded-full transition-all"
                style={{ width: `${feedback.avg_correctness}%` }}
              />
            </div>
          </div>
          <div>
            <div className="flex justify-between mb-2">
              <span className="text-slate-300">Clarity</span>
              <span className="text-blue-400 font-semibold">{feedback.avg_clarity.toFixed(1)}%</span>
            </div>
            <div className="bg-slate-700 rounded-full h-2">
              <div
                className="bg-blue-500 h-2 rounded-full transition-all"
                style={{ width: `${feedback.avg_clarity}%` }}
              />
            </div>
          </div>
          <div>
            <div className="flex justify-between mb-2">
              <span className="text-slate-300">Confidence</span>
              <span className="text-yellow-400 font-semibold">{feedback.avg_confidence.toFixed(1)}%</span>
            </div>
            <div className="bg-slate-700 rounded-full h-2">
              <div
                className="bg-yellow-500 h-2 rounded-full transition-all"
                style={{ width: `${feedback.avg_confidence}%` }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
