/**
 * WeaknessesSection Component
 * Displays areas for improvement with data-driven metrics
 * Shows specific score percentages and why each weakness matters
 */

import React from 'react';
import { AlertCircle } from 'lucide-react';

export function WeaknessesSection({ weaknesses }) {
  return (
    <div className="bg-slate-800 rounded-lg p-6 border-l-4 border-red-500">
      <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
        <AlertCircle size={20} className="text-red-400" />
        Areas for Improvement ({weaknesses.length})
      </h3>
      <div className="space-y-3">
        {weaknesses.map((weakness, idx) => (
          <div key={idx} className="bg-slate-700/50 rounded-lg p-4">
            <div className="flex items-start justify-between mb-2">
              <h4 className="font-semibold text-red-300 flex-1">{weakness.area}</h4>
              <div className="flex gap-2 ml-2">
                <span
                  className={`text-xs px-2 py-1 rounded whitespace-nowrap ${
                    weakness.severity === 'high'
                      ? 'bg-red-900/50 text-red-300'
                      : weakness.severity === 'medium'
                      ? 'bg-yellow-900/50 text-yellow-300'
                      : 'bg-blue-900/50 text-blue-300'
                  }`}
                >
                  {weakness.severity}
                </span>
                {weakness.metric && (
                  <span className="text-xs px-2 py-1 bg-slate-600 text-slate-200 rounded">
                    {weakness.metric}
                  </span>
                )}
              </div>
            </div>
            <p className="text-sm text-slate-300 mb-2 font-medium">{weakness.evidence}</p>
            <p className="text-sm text-slate-400 mb-2">
              <span className="font-semibold text-slate-300">Why this matters:</span> {weakness.explanation}
            </p>
            <p className="text-xs text-slate-500">Observed in {weakness.count} answer(s)</p>
          </div>
        ))}
      </div>
    </div>
  );
}
