/**
 * RecommendationsSection Component
 * Displays data-driven actionable next steps based on performance analysis
 * Provides specific, metric-based recommendations
 */

import React from 'react';
import { Target } from 'lucide-react';

export function RecommendationsSection({ recommendation }) {
  return (
    <div className="bg-slate-800 rounded-lg p-6 border-l-4 border-blue-500">
      <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
        <Target size={20} className="text-blue-400" />
        Data-Driven Next Steps
      </h3>
      <div className="bg-slate-700/50 rounded-lg p-4 mb-4">
        <p className="text-slate-300 leading-relaxed text-sm">{recommendation}</p>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition text-sm font-medium">
          Schedule Another Interview
        </button>
        <button className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition text-sm font-medium">
          Review Study Materials
        </button>
      </div>
    </div>
  );
}
