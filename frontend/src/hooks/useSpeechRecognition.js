/**
 * useSpeechRecognition — Issue 3 Fix
 *
 * Key changes vs broken version:
 *  - continuous = true, interimResults = true (mic no longer stops immediately)
 *  - onend restarts recognition if isRecording is still true
 *  - stop() is ONLY called by stopRecording(), never inside onstart/onresult
 */
import { useState, useRef, useCallback, useEffect } from "react";

const SpeechRecognition =
  window.SpeechRecognition || window.webkitSpeechRecognition;

export function useSpeechRecognition({ onTranscript, onError } = {}) {
  const [isRecording, setIsRecording] = useState(false);
  const [interimText, setInterimText] = useState("");
  const recognitionRef = useRef(null);
  const isRecordingRef = useRef(false); // stable ref for onend closure

  const isSupported = Boolean(SpeechRecognition);

  const startRecording = useCallback(() => {
    if (!isSupported) {
      onError?.("Speech recognition is not supported in this browser.");
      return;
    }
    if (isRecordingRef.current) return;

    const recognition = new SpeechRecognition();
    recognition.continuous = true;       // ← FIX: keeps mic open
    recognition.interimResults = true;   // ← FIX: shows partial results
    recognition.lang = "en-US";

    recognition.onstart = () => {
      // Do NOT call stop() here — that was the original bug
      setIsRecording(true);
      isRecordingRef.current = true;
    };

    recognition.onresult = (event) => {
      let interim = "";
      let final = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          final += transcript + " ";
        } else {
          interim += transcript;
        }
      }
      if (final) onTranscript?.(final);
      setInterimText(interim);
    };

    recognition.onerror = (event) => {
      // Don't treat "no-speech" as a fatal error — just log it
      if (event.error !== "no-speech") {
        console.error("[SpeechRecognition] error:", event.error);
        onError?.(event.error);
      }
    };

    // ← FIX: restart if still recording (handles browser auto-stop after silence)
    recognition.onend = () => {
      if (isRecordingRef.current) {
        try {
          recognition.start();
        } catch (e) {
          console.warn("[SpeechRecognition] restart failed:", e);
        }
      } else {
        setIsRecording(false);
        setInterimText("");
      }
    };

    recognitionRef.current = recognition;
    try {
      recognition.start();
    } catch (e) {
      console.error("[SpeechRecognition] start error:", e);
      onError?.(String(e));
    }
  }, [isSupported, onTranscript, onError]);

  const stopRecording = useCallback(() => {
    isRecordingRef.current = false; // signal onend not to restart
    recognitionRef.current?.stop();
    setIsRecording(false);
    setInterimText("");
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isRecordingRef.current = false;
      recognitionRef.current?.stop();
    };
  }, []);

  return { isRecording, interimText, isSupported, startRecording, stopRecording };
}
