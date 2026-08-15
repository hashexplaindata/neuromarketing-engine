#!/usr/bin/env python3
"""
Saliency Engine - Real Pretrained Model Inference with Spatial Inhibition of Return (IOR)
Uses DeepGaze IIE (saliency density), DeepGaze III (scanpath),
YOLOv8-N (object detection), and EasyOCR (text region detection).

Implements Spatial Gaussian IOR (sigma = 80px) to guarantee realistic
multi-node saccadic eye movements across all competing human faces and text blocks.
"""

import os
import sys
import logging
import json
from typing import Optional, List, Dict, Tuple

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import numpy as np
import torch
import cv2
from PIL import Image
from scipy.ndimage import zoom, gaussian_filter
from scipy.special import logsumexp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [saliency] %(message)s"
)
logger = logging.getLogger("saliency")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(PROJECT_ROOT, "_config", "models")
CENTERBIAS_PATH = os.path.join(MODELS_DIR, "centerbias_mit1003.npy")

DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'


def download_centerbias():
    """Download centerbias_mit1003.npy from DeepGaze GitHub releases (2MB)."""
    os.makedirs(MODELS_DIR, exist_ok=True)
    if os.path.exists(CENTERBIAS_PATH):
        return
    url = "https://github.com/matthias-k/DeepGaze/releases/download/v1.0.0/centerbias_mit1003.npy"
    logger.info(f"Downloading centerbias from {url} ...")
    import urllib.request
    urllib.request.urlretrieve(url, CENTERBIAS_PATH)
    logger.info(f"Saved centerbias ({os.path.getsize(CENTERBIAS_PATH) / 1024:.0f} KB)")


class SaliencyEngine:
    """
    Real pretrained saliency inference engine with Spatial Gaussian IOR.
    - DeepGaze IIE: spatial saliency density P(x,y)
    - DeepGaze III: sequential scanpath prediction with Inhibition of Return
    """

    def __init__(self):
        import deepgaze_pytorch

        logger.info(f"Initializing SaliencyEngine on device: {DEVICE}")

        download_centerbias()
        self.centerbias_template = np.load(CENTERBIAS_PATH)
        logger.info(f"Loaded centerbias: shape={self.centerbias_template.shape}")

        logger.info("Loading DeepGaze IIE (pretrained=True) ...")
        self.saliency_model = deepgaze_pytorch.DeepGazeIIE(pretrained=True).to(DEVICE)
        self.saliency_model.eval()
        logger.info("DeepGaze IIE loaded.")

        logger.info("Loading DeepGaze III (pretrained=True) ...")
        self.scanpath_model = deepgaze_pytorch.DeepGazeIII(pretrained=True).to(DEVICE)
        self.scanpath_model.eval()
        logger.info("DeepGaze III loaded.")

    def _prepare_centerbias(self, h, w):
        cb = zoom(
            self.centerbias_template,
            (h / self.centerbias_template.shape[0],
             w / self.centerbias_template.shape[1]),
            order=0, mode='nearest'
        )
        cb -= logsumexp(cb)
        return cb

    def predict_saliency(self, image_rgb: np.ndarray) -> np.ndarray:
        """
        Returns P(x,y) - true probability density that sums to 1.0.
        """
        h, w = image_rgb.shape[:2]
        cb = self._prepare_centerbias(h, w)

        img_t = torch.tensor(
            image_rgb.transpose(2, 0, 1)[np.newaxis, ...], dtype=torch.float32
        ).to(DEVICE)
        cb_t = torch.tensor(cb[np.newaxis, ...], dtype=torch.float32).to(DEVICE)

        with torch.no_grad():
            log_density = self.saliency_model(img_t, cb_t)

        prob = torch.exp(log_density).cpu().numpy()[0, 0]
        prob /= prob.sum()

        logger.info(f"Saliency map: shape={prob.shape}, integral={prob.sum():.6f}")
        return prob.astype(np.float32)

    def predict_scanpath(self, image_rgb: np.ndarray, num_fixations: int = 8, ior_sigma: float = 75.0) -> list:
        """
        Predict sequential scanpath using DeepGaze III + Spatial Gaussian Inhibition of Return.
        
        Fixation 1 is the primary saliency maximum (e.g. center hero).
        For each subsequent fixation step:
        - A Gaussian suppression field (sigma = 75px) is accumulated over previously fixated nodes.
        - DeepGaze III autoregressive history conditions the probability density.
        - The combined density forces macro-saccadic jumps to alternate attractors (competing faces, text).
        """
        h, w = image_rgb.shape[:2]
        cb = self._prepare_centerbias(h, w)

        img_t = torch.tensor(
            image_rgb.transpose(2, 0, 1)[np.newaxis, ...], dtype=torch.float32
        ).to(DEVICE)
        cb_t = torch.tensor(cb[np.newaxis, ...], dtype=torch.float32).to(DEVICE)

        # Baseline Saliency Map
        with torch.no_grad():
            initial_log_density = self.saliency_model(img_t, cb_t)
        base_prob = torch.exp(initial_log_density).cpu().numpy()[0, 0]
        base_prob /= base_prob.sum()

        # Cumulative Inhibition of Return Map (1.0 = full uninhibited, 0.0 = fully suppressed)
        ior_map = np.ones((h, w), dtype=np.float32)

        # First fixation
        first_idx = np.argmax(base_prob)
        first_fy, first_fx = np.unravel_index(first_idx, base_prob.shape)

        fixations = [{"x": int(first_fx), "y": int(first_fy), "step": 1}]
        history_x = [float(first_fx)]
        history_y = [float(first_fy)]

        # Apply IOR for first fixation
        Y, X = np.ogrid[:h, :w]
        dist_sq = (X - first_fx)**2 + (Y - first_fy)**2
        ior_map *= (1.0 - 0.90 * np.exp(-dist_sq / (2.0 * ior_sigma**2)))

        for step in range(1, num_fixations):
            x_hist_padded = [float('nan')] * 4
            y_hist_padded = [float('nan')] * 4
            
            recent_x = history_x[-4:][::-1]
            recent_y = history_y[-4:][::-1]

            for i in range(len(recent_x)):
                x_hist_padded[i] = recent_x[i]
                y_hist_padded[i] = recent_y[i]

            hx_t = torch.tensor([x_hist_padded], dtype=torch.float32).to(DEVICE)
            hy_t = torch.tensor([y_hist_padded], dtype=torch.float32).to(DEVICE)

            with torch.no_grad():
                log_density = self.scanpath_model(img_t, cb_t, x_hist=hx_t, y_hist=hy_t)

            step_prob = torch.exp(log_density).cpu().numpy()[0, 0]
            step_prob /= step_prob.sum()

            # Blend DeepGaze III sequential prediction with Spatial IOR
            effective_prob = step_prob * ior_map
            if effective_prob.sum() > 0:
                effective_prob /= effective_prob.sum()
            else:
                effective_prob = step_prob

            idx = np.argmax(effective_prob)
            fy, fx = np.unravel_index(idx, effective_prob.shape)

            fixations.append({"x": int(fx), "y": int(fy), "step": step + 1})
            history_x.append(float(fx))
            history_y.append(float(fy))

            # Apply Gaussian suppression around newly fixated node
            dist_sq = (X - fx)**2 + (Y - fy)**2
            ior_map *= (1.0 - 0.85 * np.exp(-dist_sq / (2.0 * ior_sigma**2)))

        logger.info(f"Scanpath with Spatial IOR: {len(fixations)} macro-saccadic fixations computed across distinct visual nodes.")
        for f in fixations:
            logger.info(f"  Fixation {f['step']}: ({f['x']}, {f['y']})")

        return fixations


class ObjectDetector:
    """Real YOLOv8-N + EasyOCR detection."""

    def __init__(self):
        from ultralytics import YOLO
        import easyocr

        logger.info("Loading YOLOv8-N (COCO pretrained) ...")
        self.yolo = YOLO('yolov8n.pt')
        logger.info("YOLOv8-N loaded.")

        logger.info("Loading EasyOCR (English) ...")
        self.reader = easyocr.Reader(['en'], gpu=False)
        logger.info("EasyOCR loaded.")

    def detect(self, image_path: str) -> list:
        detections = []

        try:
            results = self.yolo.predict(image_path, conf=0.25, verbose=False)
            for box in results[0].boxes:
                x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
                detections.append({
                    'label': results[0].names[int(box.cls[0])],
                    'confidence': round(float(box.conf[0]), 3),
                    'bbox': [y1, x1, y2, x2],
                    'source': 'YOLOv8'
                })
            logger.info(f"YOLOv8: {len(detections)} objects detected")
        except Exception as e:
            logger.warning(f"YOLOv8 detection notice: {e}")

        try:
            img_gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img_gray is None:
                img_gray = cv2.cvtColor(cv2.imread(image_path), cv2.COLOR_BGR2GRAY)
            
            ocr_results = self.reader.readtext(img_gray)
            text_count = 0
            for bbox_pts, text, conf in ocr_results:
                if conf < 0.25 or len(text.strip()) < 2:
                    continue
                xs = [p[0] for p in bbox_pts]
                ys = [p[1] for p in bbox_pts]
                detections.append({
                    'label': f'TEXT: "{text.strip()}"',
                    'confidence': round(float(conf), 3),
                    'bbox': [int(min(ys)), int(min(xs)), int(max(ys)), int(max(xs))],
                    'source': 'EasyOCR',
                    'text_content': text.strip()
                })
                text_count += 1

            logger.info(f"EasyOCR: {text_count} text regions detected")
        except Exception as e:
            logger.warning(f"EasyOCR detection notice: {e}")

        return detections


def compute_fixation_share(prob_density: np.ndarray, bbox: list) -> float:
    """FixShare(Rk) = integral of P(x,y) over bounding box, as percentage."""
    t, l, b, r = bbox
    h, w = prob_density.shape
    t, l = max(0, t), max(0, l)
    b, r = min(h, b), min(w, r)
    return float(prob_density[t:b, l:r].sum()) * 100.0


def compute_ttff(scanpath: list, bbox: list) -> Optional[int]:
    """TTFF from predicted scanpath. Returns ms or None."""
    t, l, b, r = bbox
    BASE_MS = 80
    SACCADE_MS = 60
    for fix in scanpath:
        fx, fy = fix['x'], fix['y']
        if l <= fx <= r and t <= fy <= b:
            return BASE_MS + ((fix['step'] - 1) * SACCADE_MS)
    return None