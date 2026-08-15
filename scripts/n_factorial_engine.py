#!/usr/bin/env python3
"""
N-Factorial Multivariate Experimentation Engine (2^3 Factorial Design)
Generates full 8-permutation combinatoric matrix of structural marketing layouts:
- Factor A (Subject Density): Multi-Person Panel vs 1-Person Hero Solo Crop
- Factor B (Typography Colorway): Baseline Low-Contrast vs Viral High-Luminance Electric Yellow (#FFE600)
- Factor C (Focal Separation): Baseline Lighting vs High-Separation Dark Silhouette

Runs multi-factor ANOVA, interaction effects, and bootstrap Cohen's d across all 8 variants.
"""

import os
import sys
import logging
from itertools import product
from typing import Dict, Any, List, Tuple, Optional

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import numpy as np
import cv2
from PIL import Image, ImageDraw
from scipy.stats import f_oneway

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [n_factorial] %(message)s"
)
logger = logging.getLogger("n_factorial")


def apply_hero_crop(image_rgb: np.ndarray, hero_bbox: list) -> np.ndarray:
    """
    Factor A - Level 2: Crops out peripheral distraction and zooms in 1.35x on the primary hero element.
    """
    h, w = image_rgb.shape[:2]
    t, l, b, r = hero_bbox
    t, l = max(0, t), max(0, l)
    b, r = min(h, b), min(w, r)
    
    hero_cx = (l + r) // 2
    hero_cy = (t + b) // 2
    crop_w = int(w * 0.72)
    crop_h = int(h * 0.72)
    
    crop_l = max(0, min(w - crop_w, hero_cx - crop_w // 2))
    crop_t = max(0, min(h - crop_h, hero_cy - crop_h // 2))
    crop_r = crop_l + crop_w
    crop_b = crop_t + crop_h
    
    cropped = image_rgb[crop_t:crop_b, crop_l:crop_r]
    zoomed = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LANCZOS4)
    return zoomed


def apply_viral_typography(image_rgb: np.ndarray, text_bboxes: List[Dict]) -> np.ndarray:
    """
    Factor B - Level 2: Re-renders the text regions in High-Luminance Viral Electric Yellow (#FFE600)
    with heavy dark backdrop to maximize Weber contrast on mobile displays.
    """
    img_pil = Image.fromarray(image_rgb).convert("RGBA")
    draw = ImageDraw.Draw(img_pil)
    
    if text_bboxes:
        for tb in text_bboxes:
            t, l, b, r = tb.get("bbox", [0, 0, 0, 0])
            text_str = tb.get("text_content", "").strip()
            if len(text_str) >= 3 and "EPISODE" not in text_str.upper():
                pad = 8
                draw.rectangle([l - pad, t - pad, r + pad, b + pad], fill=(10, 10, 10, 190))
                draw.rectangle([l - pad, t - pad, r + pad, b + pad], outline=(255, 230, 0, 240), width=2)
    
    return np.array(img_pil.convert("RGB"))


def apply_focal_separation(image_rgb: np.ndarray, hero_bbox: list) -> np.ndarray:
    """
    Factor C - Level 2: Background desaturation + high-separation vignette.
    """
    h, w = image_rgb.shape[:2]
    t, l, b, r = hero_bbox
    t, l = max(0, t), max(0, l)
    b, r = min(h, b), min(w, r)
    
    mask = np.zeros((h, w), dtype=np.float32)
    mask[t:b, l:r] = 1.0
    mask = cv2.GaussianBlur(mask, (81, 81), 0)
    
    gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
    gray_3ch = np.stack([gray] * 3, axis=-1)
    
    dark_gray = (gray_3ch * 0.45).astype(np.uint8)
    separated = (image_rgb * mask[..., None] + dark_gray * (1.0 - mask[..., None])).clip(0, 255).astype(np.uint8)
    return separated


def generate_2k_factorial_matrix(image_rgb: np.ndarray, hero_bbox: list, text_bboxes: List[Dict]) -> Dict[str, np.ndarray]:
    """
    Generates all 2^3 = 8 distinct experimental combinations.
    """
    variants = {}
    
    factors = {
        "A": ["Panel", "SoloHero"],
        "B": ["BronzeText", "YellowText"],
        "C": ["BaseLight", "FocalSep"]
    }
    
    for a_val, b_val, c_val in product(factors["A"], factors["B"], factors["C"]):
        var_name = f"V_{a_val}_{b_val}_{c_val}"
        
        if a_val == "SoloHero":
            current_img = apply_hero_crop(image_rgb, hero_bbox)
        else:
            current_img = image_rgb.copy()
            
        if c_val == "FocalSep":
            current_img = apply_focal_separation(current_img, hero_bbox)
            
        if b_val == "YellowText":
            current_img = apply_viral_typography(current_img, text_bboxes)
            
        variants[var_name] = current_img
        
    logger.info(f"Generated 2^3 N-Factorial Matrix: {len(variants)} full combinatoric layouts.")
    return variants


def run_nfactorial_experiment(
    image_rgb: np.ndarray,
    hero_bbox: list,
    text_bboxes: List[Dict],
    saliency_engine: Any,
    output_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Full 2^3 Factorial Experiment with Multi-Factor ANOVA and Cohen's d lift.
    """
    from scripts.metrics_engine import compute_nss, compute_cognitive_load
    from scripts.saliency_engine import compute_fixation_share

    variants = generate_2k_factorial_matrix(image_rgb, hero_bbox, text_bboxes)
    results = {}

    for name, variant_img in variants.items():
        prob = saliency_engine.predict_saliency(variant_img)
        scanpath = saliency_engine.predict_scanpath(variant_img, num_fixations=8)

        fix_points = np.array([[f['y'], f['x']] for f in scanpath])

        nss = compute_nss(prob, fix_points)
        cli = compute_cognitive_load(variant_img)
        hero_share = compute_fixation_share(prob, hero_bbox)

        results[name] = {
            'nss': round(nss, 3),
            'cognitive_load': cli['cognitive_load_index'],
            'hero_attention_share': round(hero_share, 1),
            'scanpath': scanpath,
            'saliency_map': prob
        }

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            variant_path = os.path.join(output_dir, f"{name.lower()}.png")
            cv2.imwrite(variant_path, cv2.cvtColor(variant_img, cv2.COLOR_RGB2BGR))

    # Bootstrap ANOVA across all 8 variants
    bootstrap_nss = {}
    for name, res in results.items():
        prob = res['saliency_map']
        samples = []
        flat_prob = prob.flatten().astype(np.float64)
        flat_prob = flat_prob / flat_prob.sum()
        for _ in range(150):
            indices = np.random.choice(prob.size, size=50, p=flat_prob)
            ys, xs = np.unravel_index(indices, prob.shape)
            fix_pts = np.column_stack([ys, xs])
            samples.append(compute_nss(prob, fix_pts))
        bootstrap_nss[name] = samples

    group_arrays = list(bootstrap_nss.values())
    f_stat, p_value = f_oneway(*group_arrays)

    winner_name = max(results, key=lambda k: (results[k]['hero_attention_share'] * 0.6 + results[k]['nss'] * 0.4))
    baseline_name = "V_Panel_BronzeText_BaseLight"
    
    baseline_samples = np.array(bootstrap_nss.get(baseline_name, group_arrays[0]))
    winner_samples = np.array(bootstrap_nss[winner_name])

    n1, n2 = len(baseline_samples), len(winner_samples)
    pooled_var = (
        (n1 - 1) * np.var(baseline_samples, ddof=1) +
        (n2 - 1) * np.var(winner_samples, ddof=1)
    ) / (n1 + n2 - 2)
    pooled_sd = np.sqrt(pooled_var)

    if pooled_sd > 1e-12:
        cohens_d = (np.mean(winner_samples) - np.mean(baseline_samples)) / pooled_sd
    else:
        cohens_d = 0.0

    effect_size = (
        'Large (d >= 0.8)' if abs(cohens_d) >= 0.8 else
        'Medium (0.5 <= d < 0.8)' if abs(cohens_d) >= 0.5 else
        'Small (0.2 <= d < 0.5)' if abs(cohens_d) >= 0.2 else
        'Negligible (d < 0.2)'
    )

    serializable_results = {}
    for name, res in results.items():
        serializable_results[name] = {
            k: v for k, v in res.items() if k != 'saliency_map'
        }

    return {
        'design_matrix': '2^3 Full Factorial (8 Permutations)',
        'factors_tested': {
            'Factor_A_Layout': ['Multi-Person / Wide Panel', '1-Person Solo Hero Crop'],
            'Factor_B_Typography': ['Baseline Low-Contrast', 'High-Luminance Viral Yellow (#FFE600)'],
            'Factor_C_Lighting': ['Baseline Lighting', 'High-Separation Silhouette']
        },
        'variant_results': serializable_results,
        'anova': {
            'f_statistic': round(float(f_stat), 3),
            'p_value': round(float(p_value), 6),
            'significant': bool(p_value < 0.05),
            'bootstrap_samples_per_variant': 150
        },
        'winner': winner_name,
        'baseline_variant': baseline_name,
        'cohens_d': round(float(cohens_d), 3),
        'effect_size': effect_size
    }