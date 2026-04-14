/**
 * AuthToggle Component
 * Allows switching between Login and Register modes
 */

import React from 'react';

export function AuthToggle({ isLogin, onToggle }) {
  return (
    <div className="mt-6 text-center">
      <p className="text-sm text-slate-400">
        {isLogin ? "Don't have an account? " : 'Already have an account? '}
        <button
          onClick={onToggle}
          className="text-blue-400 hover:text-blue-300 font-medium transition"
        >
          {isLogin ? 'Sign Up' : 'Login'}
        </button>
      </p>
    </div>
  );
}
