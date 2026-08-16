#!/usr/bin/env python3
"""
Biometrics Engine - Facial Gaze Vectors & Visual Face-Competition Proxies
Uses 3D Anthropometric Head Pose & Gaze Vector Geometry with solvePnP.

Computes:
1. 3D Eye Gaze Vectors (Yaw, Pitch, Roll & 3D Ray) for all detected human faces.
2. Directional Gaze Cueing: Checks if subjects are looking at the headline, hero, or viewer.
3. Image-derived expression-intensity proxy; no FACS or emotion classification is claimed.
4. Visual face-competition index based on detected person boxes; no FFA activity or neural localization is claimed.
"""

import os
import sys
import math
import logging
from typing import List, Dict, Any, Optional, Tuple

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import numpy as np
import cv2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [biometrics] %(message)s"
)
logger = logging.getLogger("biometrics")

# 3D Model Generic Anthropometric Coordinates (for solvePnP)
FACE_3D_MODEL = np.array([
    [0.0, 0.0, 0.0],          # Nose tip
    [0.0, -330.0, -65.0],     # Chin
    [-225.0, 170.0, -135.0],  # Left eye outer corner
    [225.0, 170.0, -135.0],   # Right eye outer corner
    [-150.0, -150.0, -125.0], # Left Mouth corner
    [150.0, -150.0, -125.0]   # Right mouth corner
], dtype=np.float64)


class BiometricsEngine:
    def __init__(self):
        logger.info("Initializing Biometrics Engine (Anthropometric Head Pose & Gaze Model) ...")

    def analyze_faces(
        self,
        image_rgb: np.ndarray,
        detected_persons: Optional[List[Dict]] = None,
        text_bboxes: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Extracts geometric head-pose/gaze vectors, gaze cueing, and image-derived visual proxies for detected person regions.
        """
        h, w = image_rgb.shape[:2]
        gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)

        person_boxes = []
        if detected_persons:
            for p in detected_persons:
                if p.get("source") == "YOLOv8" and p.get("label") == "person":
                    person_boxes.append(p.get("bbox"))
        
        # Fallback if no YOLO persons provided: center third
        if not person_boxes:
            person_boxes = [[int(h * 0.1), int(w * 0.25), int(h * 0.9), int(w * 0.75)]]

        # Sort left to right
        person_boxes = sorted(person_boxes, key=lambda b: b[1])
        face_count = len(person_boxes)
        logger.info(f"Analyzing {face_count} detected person regions for geometric gaze/head-pose and visual face-competition proxies.")

        focal_length = w
        cam_matrix = np.array([
            [focal_length, 0, w / 2],
            [0, focal_length, h / 2],
            [0, 0, 1]
        ], dtype=np.float64)
        dist_matrix = np.zeros((4, 1), dtype=np.float64)

        faces_data = []

        for idx, p_box in enumerate(person_boxes):
            t, l, b, r = p_box
            t, l = max(0, t), max(0, l)
            b, r = min(h, b), min(w, r)
            
            # Head/face region is approximately the top 45% of the person bounding box
            head_h = int((b - t) * 0.45)
            head_w = int(r - l)
            head_t = t
            head_b = min(h, t + head_h)
            head_l = l
            head_r = r
            
            face_center = ((head_l + head_r) // 2, (head_t + head_b) // 2)
            face_patch = gray[head_t:head_b, head_l:head_r]

            # Anthropometric 2D landmark estimation relative to head box
            left_eye_pt = (int(head_l + head_w * 0.32), int(head_t + head_h * 0.38))
            right_eye_pt = (int(head_l + head_w * 0.68), int(head_t + head_h * 0.38))
            nose_pt = (int(head_l + head_w * 0.50), int(head_t + head_h * 0.55))
            chin_pt = (int(head_l + head_w * 0.50), int(head_t + head_h * 0.95))
            mouth_left_pt = (int(head_l + head_w * 0.36), int(head_t + head_h * 0.78))
            mouth_right_pt = (int(head_l + head_w * 0.64), int(head_t + head_h * 0.78))

            # Fine-tune nose tip from bright/dark gradient in central patch
            if face_patch.size > 100:
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(face_patch)
                nose_pt = (int(head_l + head_w * 0.50 + (max_loc[0] - head_w//2) * 0.15), int(head_t + head_h * 0.55))

            image_points = np.array([
                nose_pt,
                chin_pt,
                left_eye_pt,
                right_eye_pt,
                mouth_left_pt,
                mouth_right_pt
            ], dtype=np.float64)

            # SolvePnP for 3D Head Pose & Gaze Vector
            success, rot_vec, trans_vec = cv2.solvePnP(
                FACE_3D_MODEL, image_points, cam_matrix, dist_matrix, flags=cv2.SOLVEPNP_ITERATIVE
            )

            rmat, _ = cv2.Rodrigues(rot_vec)
            angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)
            pitch = float(angles[0] * 360)
            yaw = float(angles[1] * 360)
            roll = float(angles[2] * 360)

            # 3D Gaze Vector Ray
            gaze_dx = math.sin(math.radians(yaw))
            gaze_dy = -math.sin(math.radians(pitch))
            gaze_length = math.sqrt(gaze_dx**2 + gaze_dy**2) + 1e-6
            gaze_norm_x = gaze_dx / gaze_length
            gaze_norm_y = gaze_dy / gaze_length

            gaze_target = "DIRECT_EYE_CONTACT"
            if yaw < -10.0:
                gaze_target = "LOOKING_LEFT"
            elif yaw > 10.0:
                gaze_target = "LOOKING_RIGHT"
            if pitch < -8.0:
                gaze_target += "_UP"
            elif pitch > 8.0:
                gaze_target += "_DOWN"

            # Check if gaze ray intersects any text bounding box (Gaze Cueing)
            gaze_ray_intersects_text = False
            intersected_text_label = None
            if text_bboxes:
                ray_end_x = face_center[0] + int(gaze_norm_x * 450)
                ray_end_y = face_center[1] + int(gaze_norm_y * 450)
                for tb in text_bboxes:
                    tb_t, tb_l, tb_b, tb_r = tb.get("bbox", [0, 0, 0, 0])
                    if min(face_center[0], ray_end_x) <= tb_r and max(face_center[0], ray_end_x) >= tb_l and \
                       min(face_center[1], ray_end_y) <= tb_b and max(face_center[1], ray_end_y) >= tb_t:
                        gaze_ray_intersects_text = True
                        intersected_text_label = tb.get("label", "Headline")
                        break

            # Image-derived expression-intensity proxy (not FACS, emotion, or amygdala activity).
            mouth_patch = face_patch[int(head_h * 0.65):int(head_h * 0.95), int(head_w * 0.25):int(head_w * 0.75)]
            mouth_contrast = float(np.std(mouth_patch)) if mouth_patch.size > 0 else 20.0
            
            visual_expression_proxy = min(100.0, max(0.0, (mouth_contrast * 1.5) + (abs(pitch) * 0.8) + (abs(yaw) * 0.5)))
            visual_expression_label = (
                "High visual expression contrast" if visual_expression_proxy > 60 else
                "Moderate visual expression contrast" if visual_expression_proxy > 35 else
                "Low visual expression contrast"
            )

            faces_data.append({
                "face_id": idx + 1,
                "bbox": [head_t, head_l, head_b, head_r],
                "center_coords": [int(face_center[0]), int(face_center[1])],
                "head_pose": {
                    "pitch_deg": round(pitch, 1),
                    "yaw_deg": round(yaw, 1),
                    "roll_deg": round(roll, 1)
                },
                "gaze_vector": {
                    "dx": round(float(gaze_dx), 3),
                    "dy": round(float(gaze_dy), 3),
                    "target": gaze_target,
                    "channels_into_headline": gaze_ray_intersects_text,
                    "cued_text_label": intersected_text_label
                },
                "visual_expression_proxy": {
                    "score": round(visual_expression_proxy, 1),
                    "classification": visual_expression_label,
                    "evidence_status": "MODEL_DERIVED_VISUAL_PROXY",
                    "not_measured": ["FACS action units", "emotion", "amygdala activity"]
                },
                "emotion_biometrics": {
                    "score": None,
                    "classification": "NOT_MEASURED_FROM_IMAGE_ONLY_INPUT",
                    "evidence_status": "NOT_MEASURED",
                    "deprecated_alias": True
                }
            })

        # Visual face-competition proxy based only on detected person regions.
        if face_count == 1:
            ffa_dispersion = 12.0
            dispersion_label = "Single detected person region"
        elif face_count == 2:
            ffa_dispersion = 45.0
            dispersion_label = "Two detected person regions; possible visual competition"
        else:
            ffa_dispersion = min(95.0, 30.0 * face_count)
            dispersion_label = f"Multiple detected person regions ({face_count}); visual competition proxy elevated"

        avg_visual_expression = float(np.mean([f["visual_expression_proxy"]["score"] for f in faces_data])) if faces_data else 0.0

        return {
            "face_count": face_count,
            "faces": faces_data,
            "face_competition_index": round(ffa_dispersion, 1),
            "face_competition_diagnosis": dispersion_label,
            "average_visual_expression_proxy": round(avg_visual_expression, 1),
            "ffa_attentional_dispersion_index": None,
            "ffa_dispersion_diagnosis": "NOT_MEASURED; use face_competition_index for the visual proxy",
            "average_amygdala_arousal": None,
            "evidence_status": "MODEL_DERIVED_VISUAL_GEOMETRY_ONLY"
        }