/**
 * Session Service
 * 
 * Handles API calls for interview session management
 * Including: delete session with proper error handling
 */
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Extract error message from backend response
 */
function extractErrorMessage(error) {
  if (error?.response?.data?.detail) {
    return error.response.data.detail;
  }
  if (error?.response?.status === 409) {
    return 'Session is currently processing. Try again in a moment.';
  }
  if (error?.response?.status === 404) {
    return 'Session not found or already deleted.';
  }
  if (error?.response?.status === 400) {
    return 'Cannot delete an active session. End it first.';
  }
  return 'Failed to delete session. Please try again.';
}

/**
 * Delete an interview session
 * 
 * @param {number} sessionId - The ID of the session to delete
 * @returns {Promise<{success: boolean, data?: object, message?: string, statusCode?: number, isRetryable?: boolean}>}
 */
export async function deleteSession(sessionId) {
  try {
    if (!sessionId) {
      return { success: false, message: 'Invalid session ID', isRetryable: false };
    }

    const token = localStorage.getItem('access_token');
    if (!token) {
      return { success: false, message: 'Not authenticated', isRetryable: false };
    }

    const { data } = await axios.delete(
      `${API_URL}/session/${sessionId}`,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );

    return { success: true, data };
  } catch (error) {
    const statusCode = error?.response?.status;
    const message = extractErrorMessage(error);
    const isRetryable = statusCode === 409 || statusCode >= 500; // 409 = conflict (processing), 5xx = temp server error
    
    console.error(`Failed to delete session ${sessionId}:`, error);
    return { success: false, message, statusCode, isRetryable };
  }
}

/**
 * Get session details
 * 
 * @param {number} sessionId - The ID of the session
 * @returns {Promise<{success: boolean, data?: object, message?: string}>}
 */
export async function getSession(sessionId) {
  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      return { success: false, message: 'Not authenticated' };
    }

    const { data } = await axios.get(
      `${API_URL}/session/${sessionId}`,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );

    return { success: true, data };
  } catch (error) {
    const message = extractErrorMessage(error);
    return { success: false, message };
  }
}

export const sessionService = {
  deleteSession,
  getSession,
};
