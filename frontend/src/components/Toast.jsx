/**
 * Toast Component
 * 
 * Simple notification for success/error messages
 * Features:
 * - Auto-dismiss after 3 seconds
 * - Success (green) / Error (red) styling
 * - Close button for manual dismissal
 */
import React, { useEffect } from 'react';
import { X, CheckCircle, AlertCircle } from 'lucide-react';

export function Toast({
  message,
  type = 'success', // 'success' | 'error'
  onClose,
  duration,
}) {
  // Error messages stay longer for user to read (5 seconds)
  // Success messages dismiss faster (3 seconds)
  const displayDuration = duration ?? (type === 'error' ? 5000 : 3000);

  useEffect(() => {
    if (!message || !onClose) return;

    const timer = setTimeout(onClose, displayDuration);
    return () => clearTimeout(timer);
  }, [message, onClose, displayDuration]);

  if (!message) {
    return null;
  }

  const isSuccess = type === 'success';
  const bgColor = isSuccess ? 'bg-green-900/20 border-green-700' : 'bg-red-900/20 border-red-700';
  const textColor = isSuccess ? 'text-green-300' : 'text-red-300';
  const iconColor = isSuccess ? 'text-green-400' : 'text-red-400';
  const Icon = isSuccess ? CheckCircle : AlertCircle;

  return (
    <div className={`fixed bottom-4 right-4 ${bgColor} border rounded-lg p-4 max-w-sm flex items-start gap-3 z-40 animate-in fade-in slide-in-from-bottom-4`}>
      <Icon className={`${iconColor} flex-shrink-0 mt-0.5`} size={20} />
      <p className={`${textColor} flex-1`}>{message}</p>
      <button
        onClick={onClose}
        className={`${textColor} hover:opacity-75 flex-shrink-0`}
      >
        <X size={18} />
      </button>
    </div>
  );
}
