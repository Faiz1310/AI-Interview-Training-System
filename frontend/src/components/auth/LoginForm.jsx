/**
 * LoginForm Component
 * Handles login-specific form
 */

import React from 'react';

export function LoginForm({ formData, error, loading, onInputChange, onSubmit, onForgotPassword }) {
  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-2">Email</label>
        <input
          type="email"
          name="email"
          value={formData.email}
          onChange={onInputChange}
          required
          placeholder="you@example.com"
          className="w-full px-4 py-2 bg-slate-700 border border-slate-600 text-white rounded-lg focus:outline-none focus:border-blue-500 transition"
        />
      </div>

      <div>
        <div className="flex justify-between items-center mb-2">
          <label className="block text-sm font-medium text-slate-300">Password</label>
          {onForgotPassword && (
            <button
              type="button"
              onClick={onForgotPassword}
              className="text-xs text-blue-400 hover:text-blue-300 transition"
            >
              Forgot?
            </button>
          )}
        </div>
        <input
          type="password"
          name="password"
          value={formData.password}
          onChange={onInputChange}
          required
          placeholder="••••••••"
          className="w-full px-4 py-2 bg-slate-700 border border-slate-600 text-white rounded-lg focus:outline-none focus:border-blue-500 transition"
        />
      </div>

      {error && (
        <div className="p-3 bg-red-600/20 border border-red-600 text-red-300 rounded-lg text-sm">
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={loading}
        className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? 'Logging in...' : 'Login'}
      </button>
    </form>
  );
}
