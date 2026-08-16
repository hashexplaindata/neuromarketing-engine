"""Executive report synthesis from validated computational results.

Gemini is an optional narrative layer. The deterministic fallback remains
available for offline operation, but its status is explicit in the report.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

logger = logging.getLogger("report.synthesizer")


def _strip_json_fence(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def _build_prompt(experiment_id: str, metrics_data: Dict[str, Any], branding_config: Optional[Dict[str, Any]]) -> str:
    return f"""
You are a senior visual-attention and behavioural-science report editor. Interpret
only the supplied computational results for experiment '{experiment_id}'. Treat
image-derived engagement, encoding-related, face-competition, and conversion-readiness
scores as model-derived visual proxies. Do not invent human participants, EEG,
eye-tracking observations, frontal alpha asymmetry, frontal theta, memory, emotion,
amygdala activity, clicks, conversions, or statistical significance that are not
present in the input.

EXPERIMENT RESULTS:
{json.dumps(metrics_data, indent=2, default=str)}

BRANDING CONFIG:
{json.dumps(branding_config or {}, indent=2, default=str)}

Write a client-ready JSON object with exactly these keys:
- executive_summary: 2-3 precise sentences describing the observed/modelled visual hierarchy.
- cognitive_load_analysis: explain the supplied visual-complexity metrics and their limitations.
- brand_salience_rating: integer 1-100 only if the input supports it; otherwise null.
- actionable_recommendations: an array of 3-5 specific design or testing recommendations.
- winner_variant_id: only use a supplied variant winner; otherwise null.
- evidence_status: one of MEASURED, MODEL_PREDICTED, DERIVED_PROXY, or MIXED. Use DERIVED_PROXY or MODEL_PREDICTED for image-only outputs.
- limitations: an array of explicit limitations and alternative explanations.

Recommendations must be framed as hypotheses or design actions to test. Return
ONLY valid JSON.
"""


def _gemini_generate(api_key: str, model_name: str, prompt: str) -> str:
    """Use the current Google GenAI SDK, with legacy compatibility if installed."""
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.15,
                top_p=0.95,
                response_mime_type="application/json",
            ),
        )
        return response.text or ""
    except ImportError:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={"temperature": 0.15, "top_p": 0.95},
        )
        return model.generate_content(prompt).text or ""


def synthesize_executive_report(
    experiment_id: str,
    metrics_data: Dict[str, Any],
    branding_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
    target_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    is_placeholder_key = not gemini_api_key or gemini_api_key.startswith("your_") or gemini_api_key.endswith("placeholder")
    prompt = _build_prompt(experiment_id, metrics_data, branding_config)

    if not is_placeholder_key:
        try:
            scorecard = json.loads(_strip_json_fence(_gemini_generate(gemini_api_key, target_model, prompt)))
            if not isinstance(scorecard, dict):
                raise ValueError("Gemini response was not a JSON object")
            scorecard["synthesis_engine"] = f"{target_model} (Google GenAI)"
            scorecard["synthesis_status"] = "SUCCESS"
            scorecard.setdefault("evidence_status", "MIXED")
            logger.info("Live Gemini synthesis complete (%s)", target_model)
            return scorecard
        except Exception as exc:
            error_text = str(exc)
            logger.warning("Gemini synthesis unavailable; deterministic fallback used: %s", error_text)
            synthesis_error = error_text[:500]
    else:
        synthesis_error = "Gemini API key is not configured"

    # Deterministic fallback. It is explicitly labelled and does not claim live LLM output.
    nss_score = float(metrics_data.get("nss_score", 0.0) or 0.0)
    s_auc = float(metrics_data.get("s_auc", 0.0) or 0.0)
    cognitive_load = float(metrics_data.get("cognitive_load_score", 0.0) or 0.0)
    top_variant = metrics_data.get("winning_variant")
    cognitive_status = "Lower derived complexity" if cognitive_load < 40 else ("Moderate derived complexity" if cognitive_load < 55 else "Higher derived complexity")
    salience_score = int(min(98, max(1, (min(1.0, max(0.0, s_auc)) * 65) + (min(2.5, max(0.0, nss_score) / 5.0) * 16))))

    return {
        "experiment_id": experiment_id,
        "executive_summary": (
            f"The pretrained visual-attention models produced a predicted saliency pattern with "
            f"s-AUC {s_auc:.3f} and NSS {nss_score:.2f}. These outputs describe modelled visual priority, "
            f"not observed participant fixation or downstream behaviour."
        ),
        "cognitive_load_analysis": (
            f"Derived Shannon-entropy and edge-density inputs yield a complexity index of {cognitive_load:.1f}/100 "
            f"({cognitive_status}). This is a visual-complexity proxy and should be tested with human comprehension or task data."
        ),
        "brand_salience_rating": salience_score,
        "actionable_recommendations": [
            "Compare the current asset with a controlled variant that changes one design factor at a time.",
            "Validate the predicted focal region with observed attention, recall, or task-completion data before making a behavioural claim.",
            "Review secondary copy and CTA separation where the predicted saliency map shows competing peaks.",
        ],
        "winner_variant_id": top_variant,
        "evidence_status": "MODEL_PREDICTED",
        "limitations": [
            "No participant, EEG, eye-tracking, click, conversion, recall, emotion, amygdala, FAA, or theta outcome was supplied to this synthesis.",
            "The fallback narrative was generated deterministically because the Gemini provider was unavailable.",
        ],
        "synthesis_engine": "Deterministic validated fallback",
        "synthesis_status": "FALLBACK",
        "synthesis_error": synthesis_error,
    }
