import React, { useState } from 'react';
import { authService } from '../services/authService';
import { AuthHeader } from './auth/AuthHeader';
import { LoginForm } from './auth/LoginForm';
import { RegisterForm } from './auth/RegisterForm';
import { AuthToggle } from './auth/AuthToggle';

export function LoginRegisterPage({ onLoginSuccess, onNavigate }) {
  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      let result;
      if (isLogin) {
        result = await authService.login({
          email: formData.email,
          password: formData.password,
        });
      } else {
        result = await authService.register(formData);
      }

      if (result.success) {
        onLoginSuccess(result.data);
      } else {
        setError(result.message);
      }
    } catch (err) {
      setError(err?.message || 'An error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = () => {
    if (onNavigate) {
      onNavigate('forgot-password');
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 px-4">
      <div className="w-full max-w-md">
        {/* LetsTrain.ai Header */}
        <AuthHeader />

        {/* Auth Container */}
        <div className="bg-slate-800 rounded-lg p-8 shadow-2xl border border-slate-700">
          <h2 className="text-2xl font-bold text-white mb-6 text-center">
            {isLogin ? 'Welcome Back' : 'Get Started'}
          </h2>

          {/* Form Selection */}
          {isLogin ? (
            <LoginForm
              formData={formData}
              error={error}
              loading={loading}
              onInputChange={handleChange}
              onSubmit={handleSubmit}
              onForgotPassword={handleForgotPassword}
            />
          ) : (
            <RegisterForm
              formData={formData}
              error={error}
              loading={loading}
              onInputChange={handleChange}
              onSubmit={handleSubmit}
            />
          )}

          {/* Toggle Between Login/Register */}
          <AuthToggle isLogin={isLogin} onToggle={() => setIsLogin(!isLogin)} />
        </div>

        {/* Footer */}
        <div className="mt-6 text-center text-xs text-slate-500">
          <p>🚀 Powered by LetsTrain.ai</p>
          <p className="mt-2">Practice, Improve, Excel</p>
        </div>
      </div>
    </div>
  );
}
