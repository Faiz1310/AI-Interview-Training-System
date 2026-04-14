/**
 * BehaviorSection Component
 * Displays aggregated behavioral observations with frequency metrics
 * Groups repeated issues instead of listing per-question occurrences
 */

import React from 'react';

export function BehaviorSection({ behavior }) {
  return (
    <div className="bg-slate-800 rounded-lg p-6">
      <h3 className="text-lg font-semibold text-white mb-4">Behavioral Observations</h3>
      <div className="space-y-3">
        {behavior.map((item, idx) => (
          <div
            key={idx}
            className={`rounded-lg p-4 ${
              item.severity === 'high'
                ? 'bg-red-900/20 border border-red-700'
                : item.severity === 'medium'
                ? 'bg-yellow-900/20 border border-yellow-700'
                : item.severity === 'low'
                ? 'bg-blue-900/20 border border-blue-700'
                : 'bg-green-900/20 border border-green-700'
            }`}
          >
            <div className="flex items-start justify-between mb-2">
              <h4 className="font-semibold text-white flex-1">{item.observation}</h4>
              {item.severity !== 'none' && (
                <div className="flex gap-2 ml-2">
                  <span
                    className={`text-xs px-2 py-1 rounded uppercase font-semibold whitespace-nowrap ${
                      item.severity === 'high'
                        ? 'bg-red-600 text-white'
                        : item.severity === 'medium'
                        ? 'bg-yellow-600 text-white'
                        : 'bg-blue-600 text-white'
                    }`}
                  >
                    {item.severity}
                  </span>
                  {item.percentage && (
                    <span className="text-xs px-2 py-1 bg-slate-600 text-slate-200 rounded">
                      {item.percentage}
                    </span>
                  )}
                </div>
              )}
            </div>
            {item.frequency && (
              <p className="text-sm text-slate-300 mb-2">
                <span className="font-semibold">📊 Frequency:</span> {item.frequency}
              </p>
            )}
            {item.details && <p className="text-sm text-slate-300 mb-2">{item.details}</p>}
            {item.impact && (
              <p className="text-sm text-slate-300 mb-2">
                <span className="font-semibold">💡 Impact:</span> {item.impact}
              </p>
            )}
            {item.recommendation && (
              <p className="text-sm text-slate-400 bg-slate-700/50 rounded p-2">
                <span className="font-semibold text-slate-300">✓ Recommendation:</span> {item.recommendation}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
