/**
 * useAnswerSubmit — Issue 5 Fix
 *
 * Key changes:
 *  - Validates session_id exists before allowing submit
 *  - Submit is allowed even when mic was never used (manual text input)
 *  - Sends { session_id, question, answer } as required
 *  - Logs backend errors clearly
 */
import { useState } from "react";
import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function useAnswerSubmit({ token, sessionId, question }) {
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  // ← FIX: button should be enabled if answer has text AND session exists
  //   (mic usage is optional — manual typing must always work)
  function canSubmit(answerText) {
    return Boolean(sessionId) && answerText && answerText.trim().length > 0 && !submitting;
  }

  async function submitAnswer(answerText) {
    // ← FIX: guard against missing session_id
    if (!sessionId) {
      setError("No active session. Please start an interview session first.");
      return;
    }
    if (!answerText || !answerText.trim()) {
      setError("Please provide an answer before submitting.");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      // ← FIX: send exactly { session_id, question, answer }
      const { data } = await axios.post(
        `${API_URL}/submit_answer`,
        {
          session_id: sessionId,
          question: question,
          answer: answerText.trim(),
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setResult(data);
      return data;
    } catch (err) {
      // ← FIX: log clearly and surface useful message to user
      const detail = err?.response?.data?.detail || err.message || "Submission failed";
      console.error("[useAnswerSubmit] Backend error:", {
        status: err?.response?.status,
        detail,
        payload: err?.response?.data,
      });
      setError(detail);
      return null;
    } finally {
      setSubmitting(false);
    }
  }

  return { submitting, result, error, canSubmit, submitAnswer };
}
