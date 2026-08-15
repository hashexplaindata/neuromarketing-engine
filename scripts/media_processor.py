#!/usr/bin/env python3
"""
Universal Media Processor — Static Images & Video Temporal Attention Ingestion
Supports:
- Images: .jpg, .jpeg, .png, .webp, .bmp, .tiff, .avif
- Videos: .mp4, .mov, .avi, .mkv, .webm
  Extracts keyframes at 1fps / scene cuts, computes temporal second-by-second attention retention curves.
"""

import os
import sys
import logging
from typing import List, Dict, Any, Tuple, Optional

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import numpy as np
import cv2
from PIL import Image

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [media_processor] %(message)s"
)
logger = logging.getLogger("media_processor")

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif', '.avif'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v'}


class MediaProcessor:
    @staticmethod
    def is_video(file_path: str) -> bool:
        ext = os.path.splitext(file_path)[1].lower()
        return ext in VIDEO_EXTENSIONS

    @staticmethod
    def is_image(file_path: str) -> bool:
        ext = os.path.splitext(file_path)[1].lower()
        return ext in IMAGE_EXTENSIONS

    @staticmethod
    def load_image(file_path: str) -> np.ndarray:
        """Loads any image format to standard RGB numpy uint8 array."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Asset not found: {file_path}")
        img = Image.open(file_path).convert("RGB")
        return np.array(img)

    @staticmethod
    def extract_video_frames(
        video_path: str,
        fps_sample_rate: float = 1.0,
        max_frames: int = 30,
        output_dir: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Extracts temporal frames from any video format for temporal neuromarketing analysis.
        Returns list of {frame_idx, timestamp_sec, image_rgb, frame_path}
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")

        video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_sec = total_frames / float(video_fps)

        frame_interval = max(1, int(video_fps / fps_sample_rate))
        extracted_frames = []

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        current_frame_idx = 0
        saved_count = 0

        while cap.isOpened() and saved_count < max_frames:
            ret, frame = cap.read()
            if not ret:
                break

            if current_frame_idx % frame_interval == 0:
                timestamp_sec = round(current_frame_idx / float(video_fps), 2)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                frame_path = None
                if output_dir:
                    frame_path = os.path.join(output_dir, f"frame_{saved_count:03d}_{timestamp_sec:.1f}s.jpg")
                    cv2.imwrite(frame_path, frame)

                extracted_frames.append({
                    "frame_index": saved_count,
                    "raw_frame_id": current_frame_idx,
                    "timestamp_sec": timestamp_sec,
                    "image_rgb": frame_rgb,
                    "frame_path": frame_path
                })
                saved_count += 1

            current_frame_idx += 1

        cap.release()
        logger.info(f"Video '{os.path.basename(video_path)}': {duration_sec:.1f}s total duration -> Extracted {len(extracted_frames)} sample frames @ {fps_sample_rate} fps.")
        return extracted_frames