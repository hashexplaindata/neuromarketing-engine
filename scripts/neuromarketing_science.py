#!/usr/bin/env python3
"""
Neuromarketing Studio visual-diagnostics index engine.

This module computes transparent, image-derived visual proxies from saliency,
layout, copy legibility, and detected-person geometry. It does not claim to
measure EEG, frontal alpha asymmetry, frontal theta, amygdala activity,
emotion, memory encoding, or human motivation from a static asset.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

import numpy as np

logger = logging.getLogger("neuromarketing.science")


class NeuromarketingScienceEngine:
    """Compute model-derived visual proxies with explicit evidence boundaries."""

    def __init__(self):
        logger.info("Initializing NeuromarketingScienceEngine (visual-proxy mode) ...")

    def compute_neuro_indices(
        self,
        s_auc: float,
        nss: float,
        cognitive_load_index: float,
        hero_attention_share: float,
        biometrics_data: Dict[str, Any],
        linguistics_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Return visual diagnostics; neural and psychological states are not measured."""
        visual_expression = float(biometrics_data.get("average_visual_expression_proxy", 0.0))
        face_competition = float(biometrics_data.get("face_competition_index", 30.0))
        mobile_legibility = float(linguistics_data.get("mobile_legibility_score", 50.0))

        visual_approach_raw = (
            min(1.0, max(0.0, s_auc)) * 0.35
            + min(1.0, max(0.0, hero_attention_share / 60.0)) * 0.25
            + min(1.0, max(0.0, visual_expression / 100.0)) * 0.15
            + min(1.0, max(0.0, mobile_legibility / 100.0)) * 0.25
            - max(0.0, cognitive_load_index - 50.0) / 100.0
            - max(0.0, face_competition - 45.0) / 250.0
        )
        visual_approach_proxy = float(np.clip((visual_approach_raw - 0.45) * 3.0, -1.0, 1.0))
        approach_label = (
            "Higher visual engagement proxy"
            if visual_approach_proxy > 0.35
            else "Moderate visual engagement proxy"
            if visual_approach_proxy >= 0.0
            else "Lower visual engagement proxy"
        )

        visual_encoding_proxy = float(
            np.clip(
                min(1.0, max(0.0, nss / 8.0)) * 45.0
                + min(1.0, max(0.0, mobile_legibility / 100.0)) * 30.0
                + min(1.0, max(0.0, hero_attention_share / 50.0)) * 25.0
                - face_competition * 0.15,
                0.0,
                100.0,
            )
        )
        encoding_label = (
            "Higher visual encoding-related proxy"
            if visual_encoding_proxy > 70
            else "Moderate visual encoding-related proxy"
            if visual_encoding_proxy > 45
            else "Lower visual encoding-related proxy"
        )

        visual_conversion_score = float(
            np.clip(
                (max(0.0, visual_approach_proxy + 1.0) / 2.0 * 35.0)
                + visual_encoding_proxy * 0.30
                + min(1.0, max(0.0, s_auc)) * 15.0
                + min(1.0, max(0.0, mobile_legibility / 100.0)) * 20.0
                - face_competition * 0.10,
                0.0,
                100.0,
            )
        )
        viral_grade = (
            "A+ (high visual-conversion proxy)"
            if visual_conversion_score >= 85
            else "A (strong visual-conversion proxy)"
            if visual_conversion_score >= 75
            else "B (average visual-conversion proxy)"
            if visual_conversion_score >= 60
            else "C (lower visual-conversion proxy; review recommended)"
        )

        evidence_boundary = {
            "evidence_status": "MODEL_DERIVED_VISUAL_PROXY",
            "not_measured": [
                "EEG or other neural signals",
                "frontal alpha asymmetry",
                "frontal theta or memory encoding",
                "amygdala activity",
                "emotion or psychological state",
                "observed clicks, recall, or conversion",
            ],
        }

        logger.info(
            "Visual proxies computed: engagement=%0.3f, encoding=%0.1f/100, conversion=%0.1f/100",
            visual_approach_proxy,
            visual_encoding_proxy,
            visual_conversion_score,
        )

        return {
            "visual_approach_proxy": {
                "score": round(visual_approach_proxy, 3),
                "metric_name": "Image-derived visual engagement proxy",
                "interpretation": approach_label,
                **evidence_boundary,
            },
            "visual_encoding_proxy": {
                "score_pct": round(visual_encoding_proxy, 1),
                "metric_name": "Image-derived visual encoding-related proxy",
                "interpretation": encoding_label,
                **evidence_boundary,
            },
            "visual_conversion_readiness": {
                "composite_score": round(visual_conversion_score, 1),
                "grade": viral_grade,
                "formula_inputs": [
                    "saliency discrimination",
                    "predicted scanpath statistics",
                    "visual hierarchy",
                    "copy legibility",
                    "detected-person competition",
                ],
                **evidence_boundary,
            },
            # Compatibility aliases are deliberately null rather than fabricated.
            "frontal_alpha_asymmetry_faa": {
                "score": None,
                "metric_name": "FAA not measured",
                "status": "NOT_MEASURED",
                "deprecated_alias": True,
            },
            "frontal_theta_memory_encoding": {
                "score_pct": None,
                "metric_name": "Frontal theta/memory encoding not measured",
                "status": "NOT_MEASURED",
                "deprecated_alias": True,
            },
            # Existing UI/report consumers can retain this stable key while the
            # content explicitly states that it is a visual proxy, not observed CTR.
            "viral_ctr_potential": {
                "composite_score": round(visual_conversion_score, 1),
                "grade": viral_grade,
                **evidence_boundary,
            },
        }
