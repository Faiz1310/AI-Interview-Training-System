/**
 * ConfirmDialog Component
 * 
 * Reusable confirmation modal for destructive actions
 * Features:
 * - Customizable title and message
 * - Loading state during confirmation
 * - Primary/danger button styling
 * - Keyboard support (ESC to cancel)
 */
import React from 'react';
import { AlertTriangle } from 'lucide-react';

export function ConfirmDialog({
  isOpen,
  title = 'Confirm Action',
  message = 'Are you sure?',
  cancelText = 'Cancel',
  confirmText = 'Confirm',
  isDangerous = false,
  isLoading = false,
  onCancel,
  onConfirm,
}) {
  const dialogRef = React.useRef(null);
  const cancelBtnRef = React.useRef(null);
  const confirmBtnRef = React.useRef(null);

  // Handle ESC key to close dialog and keyboard navigation
  React.useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen && !isLoading) {
        onCancel?.();
      }
      // Tab key navigation within dialog
      if (e.key === 'Tab' && isOpen && dialogRef.current) {
        const focusableElements = dialogRef.current.querySelectorAll(
          'button:not([disabled])'
        );
        if (focusableElements.length === 0) return;

        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];
        const activeElement = document.activeElement;

        // Trap focus within dialog
        if (e.shiftKey) {
          if (activeElement === firstElement) {
            e.preventDefault();
            lastElement.focus();
          }
        } else {
          if (activeElement === lastElement) {
            e.preventDefault();
            firstElement.focus();
          }
        }
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      // Focus cancel button by default
      setTimeout(() => cancelBtnRef.current?.focus(), 50);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'auto';
    };
  }, [isOpen, isLoading, onCancel]);

  if (!isOpen) {
    return null;
  }

  return (
    <div 
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      role="presentation"
      onClick={(e) => {
        // Close on backdrop click, but not on dialog click
        if (e.target === e.currentTarget && !isLoading) {
          onCancel?.();
        }
      }}
    >
      <div 
        ref={dialogRef}
        className="bg-slate-800 rounded-lg max-w-md w-full mx-4"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="dialog-title"
        aria-describedby="dialog-description"
      >
        {/* Header */}
        <div className="p-6 border-b border-slate-700 flex items-start gap-3">
          {isDangerous && <AlertTriangle className="text-red-400 flex-shrink-0 mt-1" size={20} />}
          <div>
            <h2 id="dialog-title" className="text-lg font-semibold text-white">{title}</h2>
          </div>
        </div>

        {/* Message */}
        <div className="p-6">
          <p id="dialog-description" className="text-slate-300">{message}</p>
        </div>

        {/* Buttons */}
        <div className="p-6 border-t border-slate-700 flex gap-3 justify-end">
          <button
            ref={cancelBtnRef}
            onClick={onCancel}
            disabled={isLoading}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-slate-500"
            aria-label="Cancel delete action"
          >
            {cancelText}
          </button>
          <button
            ref={confirmBtnRef}
            onClick={onConfirm}
            disabled={isLoading}
            className={`px-4 py-2 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 focus:outline-none focus:ring-2 ${
              isDangerous
                ? 'bg-red-600 hover:bg-red-700 text-white focus:ring-red-500'
                : 'bg-blue-600 hover:bg-blue-700 text-white focus:ring-blue-500'
            }`}
            aria-label={isLoading ? 'Deleting session' : isDangerous ? 'Confirm delete session' : 'Confirm action'}
          >
            {isLoading && (
              <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            )}
            {isLoading ? 'Deleting...' : confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
