#!/usr/bin/env python3
"""
Metrics Engine - Mathematically Rigorous Saliency & Cognitive Metrics
Implements NSS, s-AUC, CC, KLD, and Cognitive Load Index.

All formulas from: Bylinskii et al. (2019) "What Do Different Evaluation
Metrics Tell Us About Saliency Models?" - MIT Saliency Benchmark reference.
"""

import os
import sys
import logging

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import numpy as np
import cv2
from scipy.ndimage import zoom
from scipy.special import logsumexp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("metrics_engine")


def compute_nss(saliency_map, fixation_points):
    """
    Normalized Scanpath Saliency (Bylinskii et al. 2019).

    NSS = (1/N) * sum( z_scored_S(xi, yi) )

    where z_scored_S = (S - mean(S)) / std(S)
    and (xi, yi) are fixation locations.

    Args:
        saliency_map: (H, W) predicted saliency
        fixation_points: list of (y, x) tuples or Nx2 array

    Returns:
        float: NSS score. 0 = chance, >1 = good, >2 = excellent.
    """
    if len(fixation_points) == 0:
        return 0.0

    fix_arr = np.array(fixation_points)
    if fix_arr.ndim == 1:
        fix_arr = fix_arr.reshape(1, 2)

    mu = float(np.mean(saliency_map))
    sigma = float(np.std(saliency_map))
    if sigma < 1e-12:
        return 0.0

    z_scored = (saliency_map - mu) / sigma

    h, w = saliency_map.shape
    valid_mask = (
        (fix_arr[:, 0] >= 0) & (fix_arr[:, 0] < h) &
        (fix_arr[:, 1] >= 0) & (fix_arr[:, 1] < w)
    )
    valid_fix = fix_arr[valid_mask]
    if len(valid_fix) == 0:
        return 0.0

    values = z_scored[valid_fix[:, 0].astype(int), valid_fix[:, 1].astype(int)]
    return float(np.mean(values))


def compute_sauc(saliency_map, fixation_points, centerbias):
    """
    Shuffled AUC (center-bias corrected).

    Uses center bias distribution as the null model for negative sampling.
    This controls for the inherent tendency to look near image center.

    Args:
        saliency_map: (H, W) predicted saliency
        fixation_points: list of (y, x) tuples
        centerbias: (H, W) log-probability centerbias map

    Returns:
        float: s-AUC score. 0.5 = chance, >0.70 = good.
    """
    from sklearn.metrics import roc_auc_score

    if len(fixation_points) == 0:
        return 0.5

    fix_arr = np.array(fixation_points)
    h, w = saliency_map.shape

    valid_mask = (
        (fix_arr[:, 0] >= 0) & (fix_arr[:, 0] < h) &
        (fix_arr[:, 1] >= 0) & (fix_arr[:, 1] < w)
    )
    valid_fix = fix_arr[valid_mask]
    if len(valid_fix) == 0:
        return 0.5

    # Positive: saliency at fixation locations
    pos_values = saliency_map[valid_fix[:, 0].astype(int), valid_fix[:, 1].astype(int)]

    # Negative: sample from centerbias distribution (null model)
    if centerbias.shape != saliency_map.shape:
        cb = zoom(centerbias,
                  (h / centerbias.shape[0], w / centerbias.shape[1]),
                  order=0, mode='nearest')
    else:
        cb = centerbias

    cb_prob = np.exp(cb)
    cb_prob = cb_prob / cb_prob.sum()

    n_neg = min(len(pos_values) * 10, 5000)
    neg_indices = np.random.choice(
        saliency_map.size, size=n_neg,
        p=cb_prob.flatten(), replace=True
    )
    neg_y, neg_x = np.unravel_index(neg_indices, saliency_map.shape)
    neg_values = saliency_map[neg_y, neg_x]

    labels = np.concatenate([np.ones(len(pos_values)), np.zeros(len(neg_values))])
    scores = np.concatenate([pos_values, neg_values])

    if len(np.unique(labels)) < 2:
        return 0.5

    return float(roc_auc_score(labels, scores))


def compute_cc(map_a, map_b):
    """
    Pearson Linear Correlation Coefficient between two maps.

    CC(S, G) = cov(S, G) / (std(S) * std(G))

    Args:
        map_a, map_b: (H, W) arrays (same shape)

    Returns:
        float: CC in [-1, 1]. Higher = more agreement.
    """
    if map_a.shape != map_b.shape:
        map_b = zoom(map_b,
                     (map_a.shape[0] / map_b.shape[0],
                      map_a.shape[1] / map_b.shape[1]),
                     order=1, mode='nearest')

    a_flat = map_a.flatten().astype(np.float64)
    b_flat = map_b.flatten().astype(np.float64)

    if np.std(a_flat) < 1e-12 or np.std(b_flat) < 1e-12:
        return 0.0

    return float(np.corrcoef(a_flat, b_flat)[0, 1])


def compute_kld(ground_truth, prediction):
    """
    Kullback-Leibler Divergence.

    KLD(G || P) = sum( G * log(G / P) )
    """
    eps = 1e-12
    gt = ground_truth.astype(np.float64)
    pred = prediction.astype(np.float64)

    gt = gt / (gt.sum() + eps)
    pred = pred / (pred.sum() + eps)

    kld = float(np.sum(gt * np.log((gt + eps) / (pred + eps))))
    return max(0.0, kld)


def compute_cognitive_load(image_rgb):
    """
    Computational Cognitive Load Index from image analysis.

    Three components (Rosenholtz et al., MIT 2007):
    1. Shannon Spatial Entropy: H = -sum(p(i) * log2(p(i)))
    2. Edge Density: rho = |Canny edges| / (H*W)
    3. Luminance Congestion: local contrast variance

    Composite: CLI = (0.35*entropy_norm + 0.35*edge_norm + 0.30*lum_congestion) * 100
    """
    gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)

    # 1. Shannon Spatial Entropy
    hist, _ = np.histogram(gray.flatten(), bins=256, range=(0, 255), density=True)
    hist = hist[hist > 0]
    entropy = float(-np.sum(hist * np.log2(hist)))
    entropy_norm = entropy / 8.0

    # 2. Edge Density (Canny)
    edges = cv2.Canny(gray, 100, 200)
    edge_density = float(np.sum(edges > 0)) / float(edges.size)
    edge_norm = min(edge_density / 0.20, 1.0)

    # 3. Feature Congestion
    local_mean = cv2.blur(gray.astype(np.float32), (15, 15))
    local_var = cv2.blur((gray.astype(np.float32) - local_mean) ** 2, (15, 15))
    lum_congestion = float(np.mean(np.sqrt(local_var))) / 128.0

    # Composite CLI
    cli = (0.35 * entropy_norm + 0.35 * edge_norm + 0.30 * lum_congestion) * 100.0

    result = {
        'cognitive_load_index': round(cli, 1),
        'shannon_entropy_bits': round(entropy, 2),
        'edge_density_ratio': round(edge_density, 4),
        'luminance_congestion': round(lum_congestion, 4),
        'classification': (
            'Low (Clean Design)' if cli < 35 else
            'Moderate' if cli < 55 else
            'High (Decision Fatigue Risk)' if cli < 70 else
            'Very High (Visual Overload)'
        )
    }
    return result


def compute_all_metrics(saliency_map, scanpath, centerbias_template, image_rgb):
    """Compute all saliency and cognitive metrics for a single image."""
    h, w = saliency_map.shape

    fix_points = np.array([[f['y'], f['x']] for f in scanpath])

    cb = zoom(centerbias_template,
              (h / centerbias_template.shape[0],
               w / centerbias_template.shape[1]),
              order=0, mode='nearest')
    cb -= logsumexp(cb)

    nss = compute_nss(saliency_map, fix_points)
    sauc = compute_sauc(saliency_map, fix_points, cb)
    cli = compute_cognitive_load(image_rgb)

    return {
        'nss': round(nss, 3),
        's_auc': round(sauc, 4),
        'cognitive_load': cli,
        'fixation_count': len(scanpath),
        'saliency_integral': round(float(saliency_map.sum()), 6),
        'saliency_max': round(float(saliency_map.max()), 8),
        'saliency_dynamic_range': round(
            float(saliency_map.max() / (saliency_map.min() + 1e-12)), 2
        )
    }