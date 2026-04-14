"""
Centralized AI service.
- Groq  (LLaMA 3.3 70B) → fast scoring, question generation
- Gemini (1.5 Flash)     → resume analysis, rich explanations

All API calls are wrapped in try/except with timeout and 1 retry.
On failure, structured fallback JSON is returned — server never crashes.
"""
import logging
import os
import time
import json
import re
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ─── Groq ──────────────────────────────────────────────────────────────────────
_groq_client = None


def get_groq():
    global _groq_client
    if _groq_client is None:
        from groq import Groq
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY not set in .env")
        _groq_client = Groq(api_key=api_key)
    return _groq_client


def groq_chat(
    messages: list,
    model: str = "llama-3.3-70b-versatile",
    temperature: float = 0.3,
    max_tokens: int = 1024,
    timeout: float = 20.0,
) -> str:
    """
    Call Groq chat completions with retry logic (1 retry max).
    Returns response text, or raises on both attempts failing.
    """
    last_error = None
    for attempt in range(2):
        try:
            client = get_groq()
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            last_error = e
            logger.warning(f"[Groq] attempt {attempt + 1} failed: {e}")
            if attempt == 0:
                time.sleep(1.0)  # brief pause before retry

    raise RuntimeError(f"Groq API unavailable after 2 attempts: {last_error}")


def groq_chat_safe(
    messages: list,
    fallback: dict,
    model: str = "llama-3.3-70b-versatile",
    temperature: float = 0.3,
    max_tokens: int = 1024,
    timeout: float = 20.0,
) -> str:
    """
    Like groq_chat but returns a JSON-serialized fallback dict on failure.
    Use when you need guaranteed JSON output and can tolerate a fallback.
    """
    import json
    try:
        return groq_chat(messages, model, temperature, max_tokens, timeout)
    except Exception as e:
        logger.error(f"[Groq] both attempts failed, using fallback: {e}")
        return json.dumps(fallback)


def groq_generate(prompt: str, temperature: float = 0.3, timeout: float = 20.0) -> str:
    """Single-prompt Groq helper with the same timeout/retry protection."""
    return groq_chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        timeout=timeout,
        max_tokens=2048,
    )


# ─── Gemini ────────────────────────────────────────────────────────────────────
_gemini_model = None
_available_models = []


def _get_available_gemini_models():
    """Detect available Gemini models that support generateContent."""
    global _available_models
    try:
        import google.generativeai as genai
        all_models = genai.list_models()
        available = [m.name.split('/')[-1] for m in all_models if 'generateContent' in m.supported_generation_methods]
        logger.info(f"[Gemini] Available models: {available}")
        _available_models = available
        return available
    except Exception as e:
        logger.warning(f"[Gemini] Failed to list models: {e}. Using fallback.")
        return []


def get_gemini():
    """Get Gemini model, dynamically detected. Falls back to gemini-1.0-pro-latest if needed."""
    global _gemini_model
    if _gemini_model is None:
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set in .env")
        genai.configure(api_key=api_key)
        
        # Use dynamic model detection
        available = _get_available_gemini_models()
        model_name = None
        
        # Prefer latest fast Gemini models first.
        for preferred in [
            "gemini-2.5-flash",
            "gemini-flash-latest",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-flash-latest",
        ]:
            if preferred in available:
                model_name = preferred
                logger.info(f"[Gemini] Using preferred model: {model_name}")
                break
        
        # Fallback to first available or hardcoded fallback
        if not model_name:
            if available:
                model_name = available[0]
                logger.warning(f"[Gemini] Preferred model not found, using: {model_name}")
            else:
                model_name = "gemini-1.0-pro-latest"
                logger.warning(f"[Gemini] No models detected, using hardcoded fallback: {model_name}")
        
        try:
            _gemini_model = genai.GenerativeModel(model_name)
        except Exception as e:
            logger.error(f"[Gemini] Failed to load model {model_name}: {e}. Retrying with fallback.")
            _gemini_model = genai.GenerativeModel("gemini-1.0-pro-latest")
    
    return _gemini_model


def gemini_generate(prompt: str, temperature: float = 0.4, timeout: float = 20.0) -> str:
    """
    Call Gemini with retry logic (1 retry max).
    Returns response text, or raises on both attempts failing.
    Handles 404, rate limits, and other transient errors gracefully.
    """
    import google.generativeai as genai

    last_error = None
    for attempt in range(2):
        try:
            model = get_gemini()
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=2048,
                ),
                request_options={"timeout": timeout},
            )
            if not response or not response.text:
                raise ValueError("Gemini returned empty response")
            return response.text.strip()
        except Exception as e:
            last_error = e
            logger.warning(f"[Gemini] attempt {attempt + 1} failed: {type(e).__name__}: {e}")
            # Log 404 errors specifically for debugging
            if "404" in str(e):
                logger.error(f"[Gemini] 404 Error — model may not be available. Checking available models...")
                _get_available_gemini_models()
            if attempt == 0:
                time.sleep(1.0)

    raise RuntimeError(f"Gemini API unavailable after 2 attempts: {last_error}")


def gemini_generate_safe(prompt: str, fallback: dict, temperature: float = 0.4) -> str:
    """
    Like gemini_generate but returns a JSON-serialized fallback dict on failure.
    Use when you need guaranteed JSON output and can tolerate a fallback.
    """
    import json
    try:
        return gemini_generate(prompt, temperature)
    except Exception as e:
        logger.error(f"[Gemini] both attempts failed, using fallback: {e}")
        return json.dumps(fallback)


def _parse_resume_analysis_json(raw: str, model_used: str, fallback_model: str = "fallback") -> dict:
    """Normalize Gemini/Groq output to a stable resume-analysis payload."""
    fallback = {
        "analysis_score": 50,
        "summary": "AI analysis temporarily unavailable.",
        "strengths": ["Resume uploaded successfully"],
        "weaknesses": ["AI analysis temporarily unavailable"],
        "suggestions": ["Please try again later"],
        "model_used": fallback_model,
    }

    if not raw:
        return fallback

    try:
        cleaned = re.sub(r"```json|```", "", raw).strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1:
            return fallback

        data = json.loads(cleaned[start : end + 1])
        score = data.get("analysis_score", data.get("score", 50))
        return {
            "analysis_score": int(max(0, min(100, float(score)))),
            "summary": str(data.get("summary", "")) or "Resume analysis complete.",
            "strengths": list(data.get("strengths", [])) if isinstance(data.get("strengths", []), list) else [str(data.get("strengths"))],
            "weaknesses": list(data.get("weaknesses", [])) if isinstance(data.get("weaknesses", []), list) else [str(data.get("weaknesses"))],
            "suggestions": list(data.get("suggestions", [])) if isinstance(data.get("suggestions", []), list) else [str(data.get("suggestions"))],
            "model_used": model_used,
        }
    except Exception as e:
        logger.warning(f"[ResumeAnalysis] JSON normalization failed for {model_used}: {e}")
        return fallback


def safe_resume_analysis(prompt: str, temperature: float = 0.3, timeout: float = 20.0) -> dict:
    """Gemini first, then Groq fallback, then hard fallback if both fail."""
    fallback = {
        "analysis_score": 50,
        "summary": "AI analysis temporarily unavailable.",
        "strengths": ["Resume uploaded successfully"],
        "weaknesses": ["AI analysis temporarily unavailable"],
        "suggestions": ["Please try again later"],
        "model_used": "fallback",
    }

    try:
        raw = gemini_generate(prompt, temperature=temperature, timeout=timeout)
        result = _parse_resume_analysis_json(raw, model_used="gemini")
        logger.info("[ResumeAnalysis] completed using gemini")
        return result
    except Exception as gemini_error:
        logger.warning(f"[ResumeAnalysis] Gemini failed, falling back to Groq: {gemini_error}")

    try:
        raw = groq_generate(prompt, temperature=temperature, timeout=timeout)
        result = _parse_resume_analysis_json(raw, model_used="groq")
        logger.info("[ResumeAnalysis] completed using groq")
        return result
    except Exception as groq_error:
        logger.error(f"[ResumeAnalysis] Groq fallback failed: {groq_error}")
        return fallback


def initialize_ai_services():
    """
    Called at startup to preload models and log available options.
    Helps catch configuration issues early.
    
    NOTE: Gemini model listing is skipped here (network call).
    It will be called lazily on first use or in background task.
    """
    logger.info("═" * 60)
    logger.info("[AI Services] Initializing...")
    
    # Test Groq (fast, no network)
    try:
        get_groq()
        logger.info("[Groq] ✓ Connected and ready")
    except Exception as e:
        logger.error(f"[Groq] ✗ Failed to initialize: {e}")
    
    # Test Gemini availability (just check API key, no model listing yet)
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            logger.info("[Gemini] ✓ API key configured")
        else:
            logger.warning("[Gemini] ⚠ GEMINI_API_KEY not set")
    except Exception as e:
        logger.error(f"[Gemini] ✗ Failed to configure: {e}")
    
    logger.info("═" * 60)
