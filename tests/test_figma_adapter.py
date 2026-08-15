"""
Figma Lightweight Payload & Vector Contour Tests
Verifies sandbox payload size and vector extraction
"""

import json
import numpy as np
from core.figma_adapter import extract_vector_contours, compress_saliency_alpha_mask, format_figma_delivery_payload

def test_vector_contours_and_compression():
    # 1. Create simulated 1024x1024 saliency density
    h, w = 1024, 1024
    y, x = np.ogrid[:h, :w]
    logits = 3.0 * np.exp(-((x - 0.5*w)**2 + (y - 0.5*h)**2) / (2.0 * (0.15*w)**2))
    density = np.exp(logits) / np.sum(np.exp(logits))
    
    # 2. Extract vector contours
    contours = extract_vector_contours(density, thresholds=[0.4, 0.7, 0.9])
    assert len(contours) == 3
    assert contours[0]["attention_tier"] == "40% Peak Attention"
    
    # 3. Compress alpha mask
    mask_b64 = compress_saliency_alpha_mask(density, target_size=(256, 256))
    assert mask_b64.startswith("data:image/png;base64,")
    # Base64 string length should be very small (< 25KB)
    assert len(mask_b64) < 25000

def test_full_figma_delivery_payload():
    density = np.ones((256, 256), dtype=np.float32) / (256*256)
    
    payload = format_figma_delivery_payload(
        session_id="sess_test_123",
        asset_id="asset_001",
        low_level_metrics={"visual_entropy_shannon": 6.8, "status": "PASS"},
        detected_bboxes=[
            {"box_id": "b1", "label": "CTA", "bbox_normalized": [0.7, 0.3, 0.8, 0.7]}
        ],
        scorecard={
            "domain_kpis": {"cta_visibility_index": {"value": 2.68}},
            "component_attention_distribution": [{"component": "CTA", "attention_share_pct": 25.0}]
        },
        confidence_audit={"ensemble_agreement": {"confidence_tier": "HIGH_CONFIDENCE", "confidence_score_pct": 92.4}},
        leaderboard=[{"variant_id": "VAR_09", "attention_index": 166.01}],
        density_map=density
    )
    
    assert payload["type"] == "FIGMA_NEUROMARKETING_DELIVERABLE_V1"
    assert "canvas_overlay" in payload
    assert "vector_contour_tiers" in payload["canvas_overlay"]
    assert "neuromarketing_metrics" in payload
    
    # Verify overall JSON size is well under 100 KB
    json_bytes = json.dumps(payload).encode("utf-8")
    assert len(json_bytes) < 100 * 1024 # < 100KB
