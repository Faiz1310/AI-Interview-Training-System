/**
 * useAudioRecorder — MediaRecorder hook for capturing audio during answers.
 * Records audio as webm/opus, returns blob for backend analysis.
 * 
 * REFINEMENT 3: Enforces maximum 60s recording duration
 * - Automatically stops recording at 60 seconds
 * - Can be stopped earlier by user action
 */
import { useState, useRef, useCallback, useEffect } from "react";

const MAX_RECORDING_DURATION_MS = 60000; // 60 seconds

export function useAudioRecorder() {
  const [isRecordingAudio, setIsRecordingAudio] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0); // Track duration in ms
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);
  const recordingStartTimeRef = useRef(null);
  const durationIntervalRef = useRef(null);

  const startAudioRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";

      const recorder = new MediaRecorder(stream, { mimeType });
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      recorder.start(1000); // collect data every second
      mediaRecorderRef.current = recorder;
      recordingStartTimeRef.current = Date.now();
      setRecordingDuration(0);
      setIsRecordingAudio(true);

      // REFINEMENT 3: Track recording duration and auto-stop at 60s
      durationIntervalRef.current = setInterval(() => {
        const elapsed = Date.now() - recordingStartTimeRef.current;
        setRecordingDuration(elapsed);

        // Auto-stop at 60 seconds
        if (elapsed >= MAX_RECORDING_DURATION_MS) {
          clearInterval(durationIntervalRef.current);
          recorder.stop();
        }
      }, 100);
    } catch (err) {
      console.error("[AudioRecorder] Failed to start:", err);
    }
  }, []);

  const stopAudioRecording = useCallback(() => {
    return new Promise((resolve) => {
      // Clear duration tracking
      if (durationIntervalRef.current) {
        clearInterval(durationIntervalRef.current);
        durationIntervalRef.current = null;
      }
      setRecordingDuration(0);

      const recorder = mediaRecorderRef.current;
      if (!recorder || recorder.state === "inactive") {
        resolve(null);
        return;
      }

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType });
        chunksRef.current = [];
        setIsRecordingAudio(false);

        // Stop audio tracks
        if (streamRef.current) {
          streamRef.current.getTracks().forEach((t) => t.stop());
          streamRef.current = null;
        }

        resolve(blob);
      };

      recorder.stop();
    });
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (durationIntervalRef.current) {
        clearInterval(durationIntervalRef.current);
      }
    };
  }, []);

  return {
    isRecordingAudio,
    recordingDuration, // in milliseconds
    recordingDurationSeconds: Math.floor(recordingDuration / 1000),
    startAudioRecording,
    stopAudioRecording,
  };
}
