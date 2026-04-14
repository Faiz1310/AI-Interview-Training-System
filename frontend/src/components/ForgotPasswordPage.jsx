/**
 * ForgotPasswordPage Component
 * Allows users to request a password reset by entering their email
 */

import React, { useState } from 'react';
import { Mail, ArrowLeft, Loader } from 'lucide-react';

export function ForgotPasswordPage({ onNavigate }) {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!email.trim()) {
      setError('Please enter your email address');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });

      const data = await response.json();

      if (response.ok) {
        setSubmitted(true);
        setEmail('');
      } else {
        setError(data.detail || 'Failed to process request');
      }
    } catch (err) {
      setError('Network error. Please try again.');
      console.error('Forgot password error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => onNavigate?.('login')}
            className="flex items-center gap-2 text-slate-400 hover:text-white transition mb-4"
          >
            <ArrowLeft size={18} />
            Back to Login
          </button>
          <h1 className="text-3xl font-bold text-white mb-2">Forgot Password?</h1>
          <p className="text-slate-400">
            Enter your email address and we'll send you instructions to reset your password.
          </p>
        </div>

        {/* Success Message */}
        {submitted && (
          <div className="bg-green-900/20 border border-green-500/30 rounded-lg p-4 mb-6">
            <div className="flex items-start gap-3">
              <Mail className="text-green-400 flex-shrink-0 mt-0.5" size={20} />
              <div>
                <h3 className="text-green-400 font-semibold mb-1">Check your email</h3>
                <p className="text-green-300/80 text-sm">
                  If an account exists with this email, a password reset link has been sent. 
                  The link expires in 30 minutes.
                </p>
              </div>
            </div>
            <button
              onClick={() => onNavigate?.('login')}
              className="mt-4 w-full bg-green-600 hover:bg-green-700 text-white py-2 rounded-lg transition font-medium"
            >
              Back to Login
            </button>
            <button
              onClick={() => {
                setSubmitted(false);
                setEmail('');
              }}
              className="mt-2 w-full bg-slate-700 hover:bg-slate-600 text-white py-2 rounded-lg transition font-medium"
            >
              Try Another Email
            </button>
          </div>
        )}

        {/* Form */}
        {!submitted && (
          <form onSubmit={handleSubmit} className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-lg p-6">
            {/* Error Message */}
            {error && (
              <div className="mb-4 p-3 bg-red-900/20 border border-red-500/30 text-red-400 rounded text-sm">
                {error}
              </div>
            )}

            {/* Email Input */}
            <div className="mb-6">
              <label htmlFor="email" className="block text-sm font-medium text-slate-300 mb-2">
                Email Address
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="your@email.com"
                disabled={loading}
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 transition disabled:opacity-50"
              />
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 text-white font-medium py-2 rounded-lg transition flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader size={18} className="animate-spin" />
                  Sending...
                </>
              ) : (
                <>
                  <Mail size={18} />
                  Send Reset Link
                </>
              )}
            </button>

            {/* Security Note */}
            <div className="mt-4 p-3 bg-slate-700/50 rounded text-xs text-slate-400 border border-slate-600">
              <p className="font-semibold mb-1">🔒 Security Note:</p>
              <p>
                For your security, we won't reveal whether this email is registered. 
                If an account exists, you'll receive reset instructions.
              </p>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

export default ForgotPasswordPage;
