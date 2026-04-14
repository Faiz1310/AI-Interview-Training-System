/**
 * CameraFeed — MediaPipe FaceMesh integration
 *
 * Extracts facial behavioral metrics in real-time:
 *  - Eye contact ratio
 *  - Head stability
 *  - Blink rate
 *  - Facial stress index
 *
 * Sends metrics to backend via onBehaviorMetrics callback.
 */
import { useEffect, useRef, useState, useCallback } from "react";

// MediaPipe FaceMesh landmark indices
const LEFT_EYE = [33, 160, 158, 133, 153, 144];
const RIGHT_EYE = [362, 385, 387, 263, 373, 380];
const NOSE_TIP = 1;
const LEFT_BROW_INNER = 107;
const RIGHT_BROW_INNER = 336;
const UPPER_LIP = 13;
const LOWER_LIP = 14;

const EAR_BLINK_THRESHOLD = 0.21;
const METRICS_INTERVAL_MS = 2000;

function eyeAspectRatio(landmarks, indices) {
  const p = indices.map((i) => landmarks[i]);
  const v1 = Math.sqrt((p[1].x - p[5].x) ** 2 + (p[1].y - p[5].y) ** 2);
  const v2 = Math.sqrt((p[2].x - p[4].x) ** 2 + (p[2].y - p[4].y) ** 2);
  const h = Math.sqrt((p[0].x - p[3].x) ** 2 + (p[0].y - p[3].y) ** 2);
  if (h === 0) return 0;
  return (v1 + v2) / (2.0 * h);
}

function estimateEyeContact(landmarks) {
  const leftEAR = eyeAspectRatio(landmarks, LEFT_EYE);
  const rightEAR = eyeAspectRatio(landmarks, RIGHT_EYE);
  const avgEAR = (leftEAR + rightEAR) / 2;
  return Math.min(1.0, Math.max(0.0, avgEAR / 0.32));
}

function estimateStress(landmarks) {
  let stress = 0;
  const lb = landmarks[LEFT_BROW_INNER];
  const rb = landmarks[RIGHT_BROW_INNER];
  if (lb && rb) {
    const browDist = Math.sqrt((lb.x - rb.x) ** 2 + (lb.y - rb.y) ** 2);
    if (browDist < 0.08) stress += 0.35;
  }
  const ul = landmarks[UPPER_LIP];
  const ll = landmarks[LOWER_LIP];
  if (ul && ll) {
    const lipDist = Math.abs(ul.y - ll.y);
    if (lipDist < 0.015) stress += 0.35;
  }
  return Math.min(1.0, Math.max(0.0, stress));
}

export function CameraFeed({ className = "", sessionId, onBehaviorMetrics }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const faceMeshRef = useRef(null);
  const animFrameRef = useRef(null);
  const [error, setError] = useState(null);
  const [ready, setReady] = useState(false);
  const [faceMeshLoaded, setFaceMeshLoaded] = useState(false);

  const metricsRef = useRef({
    eyeContactSum: 0,
    blinkCount: 0,
    stressSum: 0,
    frameCount: 0,
    lastNosePos: null,
    totalMovement: 0,
    movementFrames: 0,
    wasBlinking: false,
  });
  const intervalRef = useRef(null);

  const flushMetrics = useCallback(() => {
    const m = metricsRef.current;
    if (m.frameCount === 0 || !onBehaviorMetrics) return;

    const avgEyeContact = m.eyeContactSum / m.frameCount;
    const avgStress = m.stressSum / m.frameCount;

    let headStability = 0.7;
    if (m.movementFrames > 0) {
      const avgMovement = m.totalMovement / m.movementFrames;
      headStability = Math.min(1.0, Math.max(0.0, 1.0 - avgMovement * 20.0));
    }

    const intervalSec = METRICS_INTERVAL_MS / 1000;
    const blinkRate = (m.blinkCount / intervalSec) * 60;

    onBehaviorMetrics({
      session_id: sessionId,
      eye_contact_score: Math.round(avgEyeContact * 1000) / 1000,
      head_stability_score: Math.round(headStability * 1000) / 1000,
      blink_rate: Math.round(blinkRate * 100) / 100,
      facial_stress_index: Math.round(avgStress * 1000) / 1000,
    });

    metricsRef.current = {
      eyeContactSum: 0,
      blinkCount: 0,
      stressSum: 0,
      frameCount: 0,
      lastNosePos: m.lastNosePos,
      totalMovement: 0,
      movementFrames: 0,
      wasBlinking: false,
    };
  }, [sessionId, onBehaviorMetrics]);

  const onResults = useCallback((results) => {
    if (!results.multiFaceLandmarks || results.multiFaceLandmarks.length === 0)
      return;

    const landmarks = results.multiFaceLandmarks[0];
    const m = metricsRef.current;

    const eyeContact = estimateEyeContact(landmarks);
    m.eyeContactSum += eyeContact;

    const leftEAR = eyeAspectRatio(landmarks, LEFT_EYE);
    const rightEAR = eyeAspectRatio(landmarks, RIGHT_EYE);
    const avgEAR = (leftEAR + rightEAR) / 2;
    const isBlinking = avgEAR < EAR_BLINK_THRESHOLD;
    if (isBlinking && !m.wasBlinking) {
      m.blinkCount++;
    }
    m.wasBlinking = isBlinking;

    const nose = landmarks[NOSE_TIP];
    if (m.lastNosePos) {
      const dx = nose.x - m.lastNosePos.x;
      const dy = nose.y - m.lastNosePos.y;
      m.totalMovement += Math.sqrt(dx * dx + dy * dy);
      m.movementFrames++;
    }
    m.lastNosePos = { x: nose.x, y: nose.y };

    const stress = estimateStress(landmarks);
    m.stressSum += stress;

    m.frameCount++;
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function init() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: 640, height: 480 },
        });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.onloadedmetadata = () => {
            videoRef.current.play().catch(console.warn);
            setReady(true);
          };
        }

        // Initialize FaceMesh
        try {
          const { FaceMesh } = await import("@mediapipe/face_mesh");
          if (cancelled) return;

          const faceMesh = new FaceMesh({
            locateFile: (file) =>
              `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`,
          });

          faceMesh.setOptions({
            maxNumFaces: 1,
            refineLandmarks: true,
            minDetectionConfidence: 0.5,
            minTrackingConfidence: 0.5,
          });

          faceMesh.onResults(onResults);
          faceMeshRef.current = faceMesh;
          setFaceMeshLoaded(true);

          const processFrame = async () => {
            if (cancelled || !videoRef.current || !faceMeshRef.current) return;
            if (videoRef.current.readyState >= 2) {
              try {
                await faceMeshRef.current.send({ image: videoRef.current });
              } catch (e) {
                // silently handle frame errors
              }
            }
            if (!cancelled) {
              animFrameRef.current = requestAnimationFrame(processFrame);
            }
          };
          animFrameRef.current = requestAnimationFrame(processFrame);
        } catch (fmErr) {
          console.warn("[CameraFeed] FaceMesh failed to load, camera-only mode:", fmErr);
        }
      } catch (err) {
        if (cancelled) return;
        if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
          setError("Camera access was blocked. Please allow camera permissions in your browser settings and reload the page.");
        } else if (err.name === "NotFoundError") {
          setError("No camera found. Please connect a webcam and try again.");
        } else {
          setError(`Camera error: ${err.message}`);
        }
        console.error("[CameraFeed]", err);
      }
    }

    init();

    if (onBehaviorMetrics && sessionId) {
      intervalRef.current = setInterval(flushMetrics, METRICS_INTERVAL_MS);
    }

    return () => {
      cancelled = true;
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
      }
      if (faceMeshRef.current) {
        faceMeshRef.current.close();
        faceMeshRef.current = null;
      }
    };
  }, [onResults, flushMetrics, onBehaviorMetrics, sessionId]);

  if (error) {
    return (
      <div
        className={`flex items-center justify-center bg-gray-900 text-white text-sm text-center p-4 rounded-lg ${className}`}
        role="alert"
      >
        <div>
          <div className="text-2xl mb-2">cam</div>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`relative ${className}`}>
      {!ready && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-900 text-white text-sm rounded-lg">
          Initializing camera...
        </div>
      )}
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className="w-full h-full object-cover rounded-lg"
        style={{ transform: "scaleX(-1)" }}
      />
      <canvas ref={canvasRef} className="hidden" />
      {ready && (
        <div className="absolute top-2 right-2 flex gap-1">
          <span className="px-2 py-1 bg-green-600/80 text-white text-xs rounded">
            LIVE
          </span>
          {faceMeshLoaded && (
            <span className="px-2 py-1 bg-blue-600/80 text-white text-xs rounded">
              FaceMesh
            </span>
          )}
        </div>
      )}
    </div>
  );
}
