/**
 * authService — Issue 2 Fix
 *
 * Key changes:
 *  - Catches axios errors and reads error.response.data.detail
 *  - Shows specific backend messages ("Email already registered", "Invalid email or password")
 *  - Falls back to a generic message only when backend provides no detail
 */
import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function extractDetail(error) {
  const detail = error?.response?.data?.detail;

  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail) && detail.length > 0) {
    // FastAPI validation errors are often an array of detail objects.
    const first = detail[0];
    if (typeof first === "string") {
      return first;
    }
    if (first && typeof first === "object") {
      const msg = first.msg || first.message || JSON.stringify(first);
      if (msg) return String(msg);
    }
  }

  if (detail && typeof detail === "object") {
    const msg = detail.message || detail.error || JSON.stringify(detail);
    if (msg) return String(msg);
  }

  if (error?.code === "ERR_NETWORK" || !error?.response) {
    return `Cannot connect to backend (${API_URL}). Please make sure the server is running.`;
  }

  return "Something went wrong. Please try again.";
}

export async function register({ name, email, password }) {
  try {
    const { data } = await axios.post(`${API_URL}/register`, { name, email, password });
    return { success: true, data };
  } catch (error) {
    // ← FIX: surface backend detail directly (e.g. "Email already registered")
    return { success: false, message: extractDetail(error) };
  }
}

export async function login({ email, password }) {
  try {
    const { data } = await axios.post(`${API_URL}/login`, { email, password });
    return { success: true, data };
  } catch (error) {
    // ← FIX: surface backend detail directly (e.g. "Invalid email or password")
    return { success: false, message: extractDetail(error) };
  }
}

export async function getMe(token) {
  try {
    const { data } = await axios.get(`${API_URL}/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return { success: true, data };
  } catch (error) {
    return { success: false, message: extractDetail(error) };
  }
}

export const authService = {
  register,
  login,
  getMe,
};
