/**
 * AuthHeader Component
 * Displays the LetsTrain.ai branding and tagline
 */

import React from 'react';
import { Zap } from 'lucide-react';

export function AuthHeader() {
  return (
    <div className="text-center mb-8">
      <div className="flex items-center justify-center gap-2 mb-2">
        <Zap className="text-blue-400" size={32} />
        <h1 className="text-4xl font-bold text-white">LetsTrain.ai</h1>
      </div>
      <p className="text-slate-400 text-sm">Master interviews with AI-powered coaching</p>
    </div>
  );
}
