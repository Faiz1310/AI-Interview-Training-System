/**
 * StrengthsSection Component
 * Displays areas where candidate excelled with confidence levels and evidence
 * Highlights patterns in high-scoring answers (≥80)
 */

import React from 'react';
import { CheckCircle } from 'lucide-react';

export function StrengthsSection({ strengths }) {
  return (
    <div className="bg-slate-800 rounded-lg p-6 border-l-4 border-green-500">
      <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
        <CheckCircle size={20} className="text-green-400" />
        Strengths ({strengths.length})
      </h3>
      <div className="space-y-3">
        {strengths.map((strength, idx) => (
          <div key={idx} className="bg-slate-700/50 rounded-lg p-4">
            <div className="flex items-start justify-between mb-2">
              <h4 className="font-semibold text-green-300 flex-1">{strength.area}</h4>
              <span className="text-xs px-2 py-1 bg-green-900/50 text-green-300 rounded whitespace-nowrap ml-2">
                {strength.confidence_level}
              </span>
            </div>
            <p className="text-sm text-slate-300 mb-2 font-medium">{strength.evidence}</p>
            <p className="text-xs text-slate-500">Observed in {strength.count} answer(s) - Consistency indicator</p>
          </div>
        ))}
      </div>
    </div>
  );
}
