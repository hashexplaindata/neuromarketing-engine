import json

import pytest

from scripts import report_synthesizer


@pytest.fixture
def metrics_data():
    return {
        "s_auc": 0.82,
        "nss_score": 2.8,
        "cognitive_load_score": 44.0,
        "winning_variant": "V_A",
        "visual_engagement_proxy_score": 0.2,
    }


def test_fallback_is_explicit_and_deterministic(monkeypatch, metrics_data):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    first = report_synthesizer.synthesize_executive_report("exp-1", metrics_data)
    second = report_synthesizer.synthesize_executive_report("exp-1", metrics_data)
    assert first == second
    assert first["synthesis_status"] == "FALLBACK"
    assert first["evidence_status"] == "MODEL_PREDICTED"
    assert "not observed participant fixation" in first["executive_summary"]
    assert "EEG" in first["limitations"][0]


def test_prompt_forbids_neural_and_behavioural_invention(metrics_data):
    prompt = report_synthesizer._build_prompt("exp-2", metrics_data, None)
    assert "frontal alpha asymmetry" in prompt
    assert "amygdala activity" in prompt
    assert "Do not invent human participants" in prompt
    assert "model-derived visual proxies" in prompt


def test_provider_json_is_normalized_and_marked_success(monkeypatch, metrics_data):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test")
    monkeypatch.setattr(report_synthesizer, "_gemini_generate", lambda *args: json.dumps({"executive_summary": "safe", "evidence_status": "DERIVED_PROXY"}))
    result = report_synthesizer.synthesize_executive_report("exp-3", metrics_data)
    assert result["synthesis_status"] == "SUCCESS"
    assert result["synthesis_engine"] == "gemini-test (Google GenAI)"
    assert result["evidence_status"] == "DERIVED_PROXY"


def test_malformed_provider_response_falls_back(monkeypatch, metrics_data):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(report_synthesizer, "_gemini_generate", lambda *args: "not-json")
    result = report_synthesizer.synthesize_executive_report("exp-4", metrics_data)
    assert result["synthesis_status"] == "FALLBACK"
    assert result["synthesis_error"]
