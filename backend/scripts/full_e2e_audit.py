import io
import json
import math
import subprocess
import tempfile
import time
import wave
from datetime import datetime, timedelta
from pathlib import Path

import bcrypt
from fastapi.testclient import TestClient

from database import SessionLocal, init_db
from main import app
from models.user import User


def clip(obj, n=240):
    try:
        return json.dumps(obj, default=str)[:n]
    except Exception:
        return str(obj)[:n]


def header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def make_tts_wav(text: str) -> Path:
    fd, path = tempfile.mkstemp(prefix="audit_tts_", suffix=".wav")
    # Close descriptor immediately to avoid Windows file-lock issues.
    # The PowerShell synthesizer will create/write this path.
    try:
        import os
        os.close(fd)
    except Exception:
        pass
    Path(path).unlink(missing_ok=True)
    ps = (
        "Add-Type -AssemblyName System.Speech; "
        "$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$speak.Rate = 0; "
        f"$speak.SetOutputToWaveFile('{path}'); "
        f"$speak.Speak('{text.replace("'", "''")}'); "
        "$speak.Dispose();"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0 or not Path(path).exists() or Path(path).stat().st_size == 0:
        raise RuntimeError(f"TTS generation failed: {result.stderr[:300]}")
    return Path(path)


def make_short_bad_audio() -> bytes:
    # Intentionally too short, expected controlled handling in /analyze_audio.
    return b"short"


def run_audit():
    init_db()
    client = TestClient(app)
    ts = int(time.time() * 1000)

    report = []
    findings = []

    # STEP 1: AUTH
    email = f"audit_user_{ts}@example.com"
    password = "AuditPass123!"
    reg = client.post("/register", json={"name": "Audit User", "email": email, "password": password})
    reg_j = reg.json() if reg.headers.get("content-type", "").startswith("application/json") else {"raw": reg.text}
    token = reg_j.get("access_token") if isinstance(reg_j, dict) else None
    me = client.get("/me", headers=header(token or "")) if token else None
    me_j = me.json() if me and me.headers.get("content-type", "").startswith("application/json") else {"raw": me.text if me else None}
    login = client.post("/login", json={"email": email, "password": password})
    login_j = login.json() if login.headers.get("content-type", "").startswith("application/json") else {"raw": login.text}

    pass_auth = (
        reg.status_code == 200
        and login.status_code == 200
        and bool(token)
        and me is not None and me.status_code == 200
    )
    if not pass_auth:
        findings.append("Authentication workflow broken")
    report.append({
        "module": "1. Authentication",
        "pass": pass_auth,
        "statuses": {"register": reg.status_code, "login": login.status_code, "me": me.status_code if me else None},
        "samples": {"register": clip(reg_j), "login": clip(login_j), "me": clip(me_j)},
        "issues": None if pass_auth else "Register/Login/JWT /me validation failed",
    })

    if not token:
        # Can't continue without auth token.
        return report, findings, "UNSTABLE"

    # STEP 2: RESUME
    resume_text = (
        "Jane Doe\n"
        "Senior Python Engineer\n"
        "Skills: Python, FastAPI, SQLAlchemy, Docker, Redis, Testing\n"
        "Projects: Built scalable interview analytics API with async processing.\n"
    )
    jd_text = (
        "Hiring Python backend engineer with FastAPI, SQLAlchemy, system design, and API testing experience."
    )
    files = {
        "resume_file": ("resume.txt", resume_text.encode("utf-8"), "text/plain"),
        "jd_file": ("jd.txt", jd_text.encode("utf-8"), "text/plain"),
    }
    upload = client.post("/upload_resume", headers=header(token), files=files, data={"job_role": "Senior Python Backend Engineer"})
    upload_j = upload.json() if upload.headers.get("content-type", "").startswith("application/json") else {"raw": upload.text}
    resume_id = upload_j.get("id") if isinstance(upload_j, dict) else None
    resumes = client.get("/resumes", headers=header(token))
    resumes_j = resumes.json() if resumes.headers.get("content-type", "").startswith("application/json") else {"raw": resumes.text}
    has_resume = isinstance(resumes_j, list) and any(r.get("id") == resume_id for r in resumes_j)

    # RAG readiness: generate questions endpoint should work.
    gq = client.post("/generate_questions", headers=header(token), json={"resume_id": resume_id, "difficulty_level": 2, "limit": 5}) if resume_id else None
    gq_j = gq.json() if gq and gq.headers.get("content-type", "").startswith("application/json") else {"raw": gq.text if gq else None}

    pass_resume = (
        upload.status_code == 200 and bool(resume_id)
        and resumes.status_code == 200 and has_resume
        and gq is not None and gq.status_code == 200
        and isinstance(gq_j, dict) and len(gq_j.get("questions", [])) > 0
    )
    if not pass_resume:
        findings.append("Resume upload/storage or RAG readiness failed")
    report.append({
        "module": "2. Resume System",
        "pass": pass_resume,
        "statuses": {"upload_resume": upload.status_code, "resumes": resumes.status_code, "generate_questions": gq.status_code if gq else None},
        "samples": {"upload_resume": clip(upload_j), "generate_questions": clip(gq_j)},
        "issues": None if pass_resume else "Upload/list/generate questions failed",
    })

    # STEP 3: START INTERVIEW
    start = client.post("/start_session", headers=header(token), json={"resume_id": resume_id, "total_questions": 5}) if resume_id else None
    start_j = start.json() if start and start.headers.get("content-type", "").startswith("application/json") else {"raw": start.text if start else None}
    session_id = start_j.get("session_id") if isinstance(start_j, dict) else None
    q0 = (start_j or {}).get("next_question", {}) if isinstance(start_j, dict) else {}
    q0_text = q0.get("question") or q0.get("question_text") or ""
    keywords = ["python", "fastapi", "sqlalchemy", "api", "backend"]
    context_hint = any(k in str(q0_text).lower() for k in keywords)
    pass_start = (start is not None and start.status_code == 200 and bool(session_id) and bool(q0_text) and context_hint)
    if not pass_start:
        findings.append("Session start or context-aware first question failed")
    report.append({
        "module": "3. Interview Engine",
        "pass": pass_start,
        "statuses": {"start_session": start.status_code if start else None},
        "samples": {"start_session": clip(start_j), "first_question": str(q0_text)[:180]},
        "issues": None if pass_start else "First question missing or not context-relevant",
    })

    # STEP 4 + STEP 5: Answer flow (JSON + AUDIO), multi-question/adaptive
    asked = set()
    adaptive_signals = []

    def submit_json_answer(question_payload: dict, answer_text: str):
        payload = {
            "session_id": session_id,
            "question": question_payload.get("question") or question_payload.get("question_text"),
            "question_type": question_payload.get("question_type", "general"),
            "difficulty_level": question_payload.get("difficulty_level", 2),
            "topic": question_payload.get("topic", "general"),
            "is_reused": question_payload.get("is_reused", False),
            "selection_reason": question_payload.get("selection_reason", ""),
            "selection_context": question_payload.get("selection_context", {}),
            "previous_score": question_payload.get("previous_score"),
            "answer": answer_text,
        }
        r = client.post("/submit_answer", headers=header(token), json=payload)
        b = r.json() if r.headers.get("content-type", "").startswith("application/json") else {"raw": r.text}
        return r, b

    json_answer_text = (
        "I would design this using FastAPI with clear service boundaries, async DB access via SQLAlchemy, "
        "and tests around API contracts, error handling, and security."
    )
    r_json, b_json = submit_json_answer(q0, json_answer_text)
    q1 = b_json.get("next_question") if isinstance(b_json, dict) else None
    json_ok = (
        r_json.status_code == 200
        and isinstance(b_json, dict)
        and b_json.get("current_answer", {}).get("overall") is not None
        and q1 is not None
    )
    if q0_text:
        asked.add(str(q0_text).strip().lower())
    if q1 and (q1.get("question") or q1.get("question_text")):
        asked.add(str(q1.get("question") or q1.get("question_text")).strip().lower())
    if isinstance(b_json, dict):
        adaptive_signals.append((q0.get("difficulty_level"), q1.get("difficulty_level") if q1 else None, q1.get("selection_reason") if q1 else None))

    # Audio answer with real spoken wav (mandatory).
    audio_transcription_ok = False
    audio_eval_ok = False
    q2 = None
    audio_sample = {}
    wav_path = None
    try:
        wav_path = make_tts_wav("I optimized a FastAPI service by adding async endpoints and query indexes.")
        mp_data = {
            "session_id": str(session_id),
            "question": (q1 or {}).get("question") or (q1 or {}).get("question_text"),
            "question_type": (q1 or {}).get("question_type", "general"),
            "difficulty_level": str((q1 or {}).get("difficulty_level", 2)),
            "topic": (q1 or {}).get("topic", "general"),
            "is_reused": str((q1 or {}).get("is_reused", False)).lower(),
            "selection_reason": (q1 or {}).get("selection_reason", ""),
            "selection_context": json.dumps((q1 or {}).get("selection_context", {})),
            "answer": "Backup typed answer in case transcription fails.",
        }
        if (q1 or {}).get("previous_score") is not None:
            mp_data["previous_score"] = str((q1 or {}).get("previous_score"))
        with open(wav_path, "rb") as f:
            files_audio = {"audio_file": ("speech.wav", f, "audio/wav")}
            r_audio = client.post("/submit_answer", headers=header(token), data=mp_data, files=files_audio)
        b_audio = r_audio.json() if r_audio.headers.get("content-type", "").startswith("application/json") else {"raw": r_audio.text}
        tr = b_audio.get("transcription") if isinstance(b_audio, dict) else None
        audio_transcription_ok = bool(tr and str(tr).strip())
        audio_eval_ok = (r_audio.status_code == 200 and isinstance(b_audio, dict) and b_audio.get("current_answer", {}).get("overall") is not None)
        q2 = b_audio.get("next_question") if isinstance(b_audio, dict) else None
        audio_sample = {
            "status": r_audio.status_code,
            "transcription": str(tr)[:180] if tr else None,
            "body": clip(b_audio),
        }
        if q2 and (q2.get("question") or q2.get("question_text")):
            asked.add(str(q2.get("question") or q2.get("question_text")).strip().lower())
        if isinstance(b_audio, dict):
            adaptive_signals.append(((q1 or {}).get("difficulty_level"), q2.get("difficulty_level") if q2 else None, q2.get("selection_reason") if q2 else None))
    except Exception as e:
        audio_sample = {"status": None, "transcription": None, "body": f"audio submission exception: {type(e).__name__}: {e}"}
        audio_eval_ok = False
        audio_transcription_ok = False
    finally:
        if wav_path and wav_path.exists():
            wav_path.unlink(missing_ok=True)

    # Continue multi-question flow to test non-repetition/adaptive behavior.
    turn_responses = [
        ("JSON", r_json.status_code, clip(b_json)),
    ]
    if audio_sample.get("status") is not None:
        turn_responses.append(("AUDIO", audio_sample.get("status"), audio_sample.get("body")))

    current_q = q2
    for i in range(2):
        if not current_q:
            break
        answer_text = f"Turn {i+3} response: I would explain tradeoffs, give concrete examples, and quantify impact."
        r_turn, b_turn = submit_json_answer(current_q, answer_text)
        turn_responses.append((f"JSON_{i+2}", r_turn.status_code, clip(b_turn)))
        nxt = b_turn.get("next_question") if isinstance(b_turn, dict) else None
        q_text = (nxt or {}).get("question") or (nxt or {}).get("question_text")
        if q_text:
            asked.add(str(q_text).strip().lower())
        adaptive_signals.append((current_q.get("difficulty_level"), (nxt or {}).get("difficulty_level") if nxt else None, (nxt or {}).get("selection_reason") if nxt else None))
        current_q = nxt

    all_turns_ok = all(code == 200 for _, code, _ in turn_responses)
    no_repetition = len(asked) >= 4
    adaptive_observed = any((a != b) or bool(reason) for a, b, reason in adaptive_signals if a is not None and b is not None)

    pass_answer_processing = json_ok and audio_eval_ok and audio_transcription_ok
    pass_multi_flow = all_turns_ok and no_repetition and adaptive_observed
    if not pass_answer_processing:
        findings.append("Answer processing failed on JSON/audio transcription/evaluation")
    if not pass_multi_flow:
        findings.append("Multi-question flow repetition/adaptation issues")

    report.append({
        "module": "4. Answer Processing",
        "pass": pass_answer_processing,
        "statuses": {"json_submit": r_json.status_code, "audio_submit": audio_sample.get("status")},
        "samples": {"json": clip(b_json), "audio": clip(audio_sample)},
        "issues": None if pass_answer_processing else "JSON or audio submission/transcription/evaluation failed",
    })

    report.append({
        "module": "5. Multi-Question Flow",
        "pass": pass_multi_flow,
        "statuses": {k: v for k, v, _ in turn_responses},
        "samples": {"turns": [s for _, _, s in turn_responses][:4], "asked_unique_count": len(asked), "adaptive_signals": adaptive_signals[:4]},
        "issues": None if pass_multi_flow else "Repetition detected, adaptation signal missing, or crash in turns",
    })

    # STEP 8 (behavior metrics) before ending session
    behavior_payload = {
        "session_id": session_id,
        "eye_contact_score": 0.82,
        "head_stability_score": 0.76,
        "blink_rate": 15.0,
        "facial_stress_index": 0.22,
    }
    bmet = client.post("/submit_behavior_metrics", headers=header(token), json=behavior_payload)
    bmet_j = bmet.json() if bmet.headers.get("content-type", "").startswith("application/json") else {"raw": bmet.text}
    window = bmet_j.get("window_metrics", {}) if isinstance(bmet_j, dict) else {}
    bconf = bmet_j.get("behavioral_confidence") if isinstance(bmet_j, dict) else None
    bmetrics_valid = (
        bmet.status_code == 200
        and isinstance(bconf, (int, float)) and 0 <= float(bconf) <= 100
        and all(isinstance(window.get(k), (int, float)) for k in ["avg_eye_contact", "avg_head_stability", "avg_blink_rate", "avg_stress_index"])
    )
    if not bmetrics_valid:
        findings.append("Behavior metrics submission/aggregation invalid")

    report.append({
        "module": "8. Behavior Metrics",
        "pass": bmetrics_valid,
        "statuses": {"submit_behavior_metrics": bmet.status_code},
        "samples": {"behavior": clip(bmet_j)},
        "issues": None if bmetrics_valid else "Behavior metrics missing/out of expected range",
    })

    # STEP 6: SESSION COMPLETION
    end = client.post("/end_session", headers=header(token), json={"session_id": session_id})
    end_j = end.json() if end.headers.get("content-type", "").startswith("application/json") else {"raw": end.text}
    pass_end = end.status_code == 200 and isinstance(end_j, dict) and end_j.get("status") == "completed"
    if not pass_end:
        findings.append("Session completion failed")
    report.append({
        "module": "6. Session Management (Completion)",
        "pass": pass_end,
        "statuses": {"end_session": end.status_code},
        "samples": {"end_session": clip(end_j)},
        "issues": None if pass_end else "Could not complete session",
    })

    # STEP 7: FEEDBACK
    fb = client.get(f"/session/{session_id}/feedback", headers=header(token))
    fb_j = fb.json() if fb.headers.get("content-type", "").startswith("application/json") else {"raw": fb.text}
    score_breakdown = fb_j.get("score_breakdown") if isinstance(fb_j, dict) else None
    behavior_metrics = fb_j.get("behavior_metrics") if isinstance(fb_j, dict) else None
    # no null in core score fields
    feedback_ok = (
        fb.status_code == 200
        and isinstance(fb_j, dict)
        and isinstance(score_breakdown, dict)
        and all(fb_j.get(k) is not None for k in ["overall_score", "avg_correctness", "avg_clarity", "avg_confidence"])
        and isinstance(behavior_metrics, dict)
    )
    if not feedback_ok:
        findings.append("Feedback generation missing required fields")
    report.append({
        "module": "7. Feedback System",
        "pass": feedback_ok,
        "statuses": {"feedback": fb.status_code},
        "samples": {"feedback": clip(fb_j)},
        "issues": None if feedback_ok else "Feedback missing score breakdown/behavior metrics/core fields",
    })

    # STEP 9: Dashboard + soft delete/restore
    dash1 = client.get("/dashboard", headers=header(token), params={"resume_id": resume_id})
    dash1_j = dash1.json() if dash1.headers.get("content-type", "").startswith("application/json") else {"raw": dash1.text}
    listed_before = isinstance(dash1_j, dict) and any(s.get("session_id") == session_id for s in dash1_j.get("session_summary", []))

    delete = client.delete(f"/session/{session_id}", headers=header(token))
    delete_j = delete.json() if delete.headers.get("content-type", "").startswith("application/json") else {"raw": delete.text}

    dash2 = client.get("/dashboard", headers=header(token), params={"resume_id": resume_id})
    dash2_j = dash2.json() if dash2.headers.get("content-type", "").startswith("application/json") else {"raw": dash2.text}
    listed_after_delete = isinstance(dash2_j, dict) and any(s.get("session_id") == session_id for s in dash2_j.get("session_summary", []))

    deleted_list = client.get("/sessions/deleted", headers=header(token))
    deleted_list_j = deleted_list.json() if deleted_list.headers.get("content-type", "").startswith("application/json") else {"raw": deleted_list.text}
    in_deleted = isinstance(deleted_list_j, dict) and any(s.get("session_id") == session_id for s in deleted_list_j.get("deleted_sessions", []))

    restore = client.post(f"/session/{session_id}/restore", headers=header(token))
    restore_j = restore.json() if restore.headers.get("content-type", "").startswith("application/json") else {"raw": restore.text}

    dash3 = client.get("/dashboard", headers=header(token), params={"resume_id": resume_id})
    dash3_j = dash3.json() if dash3.headers.get("content-type", "").startswith("application/json") else {"raw": dash3.text}
    listed_after_restore = isinstance(dash3_j, dict) and any(s.get("session_id") == session_id for s in dash3_j.get("session_summary", []))

    pass_dash = (
        dash1.status_code == 200 and listed_before
        and delete.status_code == 200 and not listed_after_delete
        and deleted_list.status_code == 200 and in_deleted
        and restore.status_code == 200 and listed_after_restore
    )
    if not pass_dash:
        findings.append("Dashboard/delete/restore consistency failed")
    report.append({
        "module": "9. Dashboard + Soft Delete/Restore",
        "pass": pass_dash,
        "statuses": {
            "dashboard_before": dash1.status_code,
            "delete": delete.status_code,
            "dashboard_after_delete": dash2.status_code,
            "deleted_list": deleted_list.status_code,
            "restore": restore.status_code,
            "dashboard_after_restore": dash3.status_code,
        },
        "samples": {
            "delete": clip(delete_j),
            "restore": clip(restore_j),
            "deleted_list": clip(deleted_list_j),
        },
        "issues": None if pass_dash else "Session visibility/state transitions inconsistent",
    })

    # STEP 10: PASSWORD RESET
    reset_email = f"audit_reset_{ts}@example.com"
    reset_old = "OldPass123!"
    with SessionLocal() as db:
        u = User(
            name="Reset User",
            email=reset_email,
            password_hash=bcrypt.hashpw(reset_old.encode(), bcrypt.gensalt()).decode(),
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        reset_uid = u.id

    fp = client.post("/forgot-password", json={"email": reset_email})
    fp_j = fp.json() if fp.headers.get("content-type", "").startswith("application/json") else {"raw": fp.text}
    reset_token = fp_j.get("token") if isinstance(fp_j, dict) else None

    with SessionLocal() as db:
        u = db.query(User).filter(User.id == reset_uid).first()
        token_hash_ok = bool(reset_token and u and u.reset_token_hash == __import__("hashlib").sha256(reset_token.encode()).hexdigest())
        expiry_exists = bool(u and u.reset_token_expiry)

    rp = client.post("/reset-password", json={"token": reset_token, "new_password": "NewPass123!"})
    rp_j = rp.json() if rp.headers.get("content-type", "").startswith("application/json") else {"raw": rp.text}
    login_new = client.post("/login", json={"email": reset_email, "password": "NewPass123!"})
    login_old = client.post("/login", json={"email": reset_email, "password": reset_old})
    reuse = client.post("/reset-password", json={"token": reset_token, "new_password": "ReuseBad123!"})

    # Expiry
    fp2 = client.post("/forgot-password", json={"email": reset_email})
    fp2_j = fp2.json() if fp2.headers.get("content-type", "").startswith("application/json") else {"raw": fp2.text}
    exp_token = fp2_j.get("token") if isinstance(fp2_j, dict) else None
    with SessionLocal() as db:
        u = db.query(User).filter(User.id == reset_uid).first()
        u.reset_token_expiry = datetime.utcnow() - timedelta(minutes=1)
        db.commit()
    exp = client.post("/reset-password", json={"token": exp_token, "new_password": "ExpiredBad123!"})
    exp_j = exp.json() if exp.headers.get("content-type", "").startswith("application/json") else {"raw": exp.text}
    exp_msg = clip(exp_j).lower()

    pass_reset = (
        fp.status_code == 200 and bool(reset_token) and token_hash_ok and expiry_exists
        and rp.status_code == 200
        and login_new.status_code == 200 and login_old.status_code != 200
        and reuse.status_code >= 400
        and exp.status_code == 400 and "expired" in exp_msg
    )
    if not pass_reset:
        findings.append("Password reset security flow failed")
    report.append({
        "module": "10. Password Reset",
        "pass": pass_reset,
        "statuses": {
            "forgot": fp.status_code,
            "reset": rp.status_code,
            "login_new": login_new.status_code,
            "login_old": login_old.status_code,
            "reuse": reuse.status_code,
            "expired": exp.status_code,
        },
        "samples": {"forgot": clip(fp_j), "reset": clip(rp_j), "expired": clip(exp_j)},
        "issues": None if pass_reset else "Forgot/reset/reuse/expiry checks failed",
    })

    # EDGE CASES
    edge = []
    # invalid register (short password)
    e1 = client.post("/register", json={"name": "x", "email": f"edge_{ts}@example.com", "password": "123"})
    edge.append(("short_password_register", e1.status_code, clip(e1.json() if e1.headers.get("content-type", "").startswith("application/json") else e1.text)))

    # missing field start_session
    e2 = client.post("/start_session", headers=header(token), json={"total_questions": 5})
    edge.append(("start_session_missing_resume_id", e2.status_code, clip(e2.json() if e2.headers.get("content-type", "").startswith("application/json") else e2.text)))

    # empty answer
    e3 = client.post(
        "/submit_answer",
        headers=header(token),
        json={
            "session_id": session_id,
            "question": "Test question",
            "answer": "",
            "question_type": "general",
            "difficulty_level": 2,
            "topic": "general",
        },
    )
    edge.append(("submit_empty_answer", e3.status_code, clip(e3.json() if e3.headers.get("content-type", "").startswith("application/json") else e3.text)))

    # bad audio
    e4 = client.post(
        "/analyze_audio",
        headers=header(token),
        data={"session_id": str(session_id)},
        files={"audio_file": ("bad.wav", io.BytesIO(make_short_bad_audio()), "audio/wav")},
    )
    e4_j = e4.json() if e4.headers.get("content-type", "").startswith("application/json") else {"raw": e4.text}
    edge.append(("analyze_audio_bad_short", e4.status_code, clip(e4_j)))

    # invalid token reset
    e5 = client.post("/reset-password", json={"token": "invalid.token.value", "new_password": "EdgePass123!"})
    edge.append(("reset_invalid_token", e5.status_code, clip(e5.json() if e5.headers.get("content-type", "").startswith("application/json") else e5.text)))

    edge_ok = all(code < 500 for _, code, _ in edge)
    if not edge_ok:
        findings.append("One or more edge cases produced server crash (5xx)")
    report.append({
        "module": "Edge Case Testing",
        "pass": edge_ok,
        "statuses": {name: code for name, code, _ in edge},
        "samples": {name: sample for name, _, sample in edge},
        "issues": None if edge_ok else "At least one invalid-input test returned 5xx",
    })

    # Final verdict
    module_passes = [m["pass"] for m in report]
    if all(module_passes):
        verdict = "STABLE"
    else:
        # Major instability if core modules fail
        core_failed = any(
            not m["pass"] and m["module"] in {
                "1. Authentication",
                "2. Resume System",
                "3. Interview Engine",
                "4. Answer Processing",
                "6. Session Management (Completion)",
                "10. Password Reset",
            }
            for m in report
        )
        verdict = "UNSTABLE" if core_failed else "PARTIALLY STABLE"

    return report, findings, verdict


if __name__ == "__main__":
    results, findings, verdict = run_audit()
    print("=== COMPLETE E2E AUDIT REPORT ===")
    for item in results:
        print(json.dumps(item, default=str))
    print("=== FINDINGS ===")
    if findings:
        for f in findings:
            print(f"- {f}")
    else:
        print("- No critical findings")
    print("=== FINAL VERDICT ===")
    print(verdict)
