/**
 * StatsGrid Component
 * Displays key performance metrics at a glance
 */

import React from 'react';
import { CheckCircle, Target, TrendingUp, AlertCircle } from 'lucide-react';

export function StatsGrid({ feedback }) {
  const stats = [
    {
      label: 'Avg Correctness',
      value: feedback.avg_correctness.toFixed(1),
      icon: CheckCircle,
      color: 'text-green-400',
    },
    {
      label: 'Avg Clarity',
      value: feedback.avg_clarity.toFixed(1),
      icon: Target,
      color: 'text-blue-400',
    },
    {
      label: 'Avg Confidence',
      value: feedback.avg_confidence.toFixed(1),
      icon: TrendingUp,
      color: 'text-yellow-400',
    },
    {
      label: 'Behavioral Issues',
      value: feedback.behavioral_issues_detected,
      icon: AlertCircle,
      color: feedback.behavioral_issues_detected > 0 ? 'text-red-400' : 'text-green-400',
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {stats.map((stat, idx) => {
        const Icon = stat.icon;
        return (
          <div key={idx} className="bg-slate-800 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Icon size={20} className={stat.color} />
              <h4 className="text-slate-400 text-sm font-medium">{stat.label}</h4>
            </div>
            <p className="text-2xl font-bold text-white">{stat.value}</p>
          </div>
        );
      })}
    </div>
  );
}
