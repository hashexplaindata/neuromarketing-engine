#!/usr/bin/env python3
"""
Full Neuromarketing Pipeline - Universal Multi-Tier Scientific Suite
Accepts ANY image format (.jpg, .png, .webp, .tiff, etc.) or video format (.mp4, .mov, .avi, etc.).

CLI Usage:
  python scripts/run_full_pipeline.py --input /path/to/any_image.jpg
  python scripts/run_full_pipeline.py --input /path/to/any_video.mp4 --fps 1.0
"""

import os
import sys
import json
import logging
import time
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import numpy as np
from PIL import Image, ImageDraw
import cv2
from scipy.ndimage import gaussian_filter

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from core.vram_manager import VRAMManager
from core.appwrite_service import AppwriteService
from scripts.media_processor import MediaProcessor
from scripts.saliency_engine import SaliencyEngine, ObjectDetector, compute_fixation_share, compute_ttff
from scripts.metrics_engine import compute_all_metrics
from scripts.biometrics_engine import BiometricsEngine
from scripts.linguistics_engine import LinguisticsEngine
from scripts.neuromarketing_science import NeuromarketingScienceEngine
from scripts.ctr_regressor import CTRRegressor
from scripts.n_factorial_engine import run_nfactorial_experiment
from scripts.report_synthesizer import synthesize_executive_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("pipeline")


def render_heatmap(image_rgb, saliency_map, output_path, foveal_sigma=26.0, noise_cutoff_pct=32.0, gamma=1.4):
    """Render thermal heatmap overlay from REAL saliency map."""
    h, w = image_rgb.shape[:2]

    if saliency_map.shape != (h, w):
        from scipy.ndimage import zoom
        sal = zoom(saliency_map, (h / saliency_map.shape[0], w / saliency_map.shape[1]), order=1)
    else:
        sal = saliency_map.copy()

    sal = gaussian_filter(sal.astype(np.float64), sigma=foveal_sigma)
    cutoff = np.percentile(sal, noise_cutoff_pct)
    sal[sal < cutoff] = 0.0

    sal_max = sal.max()
    if sal_max > 0:
        sal = sal / sal_max

    sal = np.power(sal, 1.0 / gamma)

    sal_uint8 = (sal * 255).astype(np.uint8)
    heatmap_colored = cv2.applyColorMap(sal_uint8, cv2.COLORMAP_TURBO)
    heatmap_colored = cv2.cvtColor(heatmap_colored, cv2.COLOR_BGR2RGB)

    alpha = 0.55
    overlay = (alpha * heatmap_colored.astype(np.float32) + (1 - alpha) * image_rgb.astype(np.float32))
    overlay = overlay.clip(0, 255).astype(np.uint8)

    Image.fromarray(overlay).save(output_path, quality=95)


def render_focus_map(image_rgb, saliency_map, output_path, foveal_sigma=26.0):
    """Render focus/fog map — first 250ms perception spotlight."""
    h, w = image_rgb.shape[:2]

    if saliency_map.shape != (h, w):
        from scipy.ndimage import zoom
        sal = zoom(saliency_map, (h / saliency_map.shape[0], w / saliency_map.shape[1]), order=1)
    else:
        sal = saliency_map.copy()

    sal = gaussian_filter(sal.astype(np.float64), sigma=foveal_sigma)
    cutoff = np.percentile(sal, 60.0)
    sal[sal < cutoff] = 0.0

    sal_max = sal.max()
    if sal_max > 0:
        sal = sal / sal_max

    darkened = (image_rgb.astype(np.float32) * 0.15).astype(np.uint8)
    focus_mask = sal[..., None]
    result = (image_rgb.astype(np.float32) * focus_mask + darkened.astype(np.float32) * (1 - focus_mask))
    result = result.clip(0, 255).astype(np.uint8)

    Image.fromarray(result).save(output_path, quality=95)


def render_scanpath(image_rgb, scanpath, biometrics_data, output_path):
    """Draw REAL predicted scanpath trajectory + 3D Gaze Vectors on the image."""
    img = Image.fromarray(image_rgb).convert("RGBA")
    draw = ImageDraw.Draw(img)

    for face in biometrics_data.get("faces", []):
        cx, cy = face["center_coords"]
        dx = face["gaze_vector"]["dx"]
        dy = face["gaze_vector"]["dy"]
        ray_len = 160
        ray_end_x = int(cx + dx * ray_len)
        ray_end_y = int(cy + dy * ray_len)
        draw.line([(cx, cy), (ray_end_x, ray_end_y)], fill=(0, 255, 200, 240), width=5)
        draw.ellipse([ray_end_x - 6, ray_end_y - 6, ray_end_x + 6, ray_end_y + 6], fill=(0, 255, 200, 255))

    for i in range(len(scanpath) - 1):
        x1, y1 = scanpath[i]['x'], scanpath[i]['y']
        x2, y2 = scanpath[i + 1]['x'], scanpath[i + 1]['y']
        draw.line([(x1, y1), (x2, y2)], fill=(255, 200, 0, 220), width=4)

    for fix in scanpath:
        x, y = fix['x'], fix['y']
        r = 22
        draw.ellipse([x - r, y - r, x + r, y + r],
                      fill=(237, 100, 54, 230), outline=(255, 255, 255), width=3)
        num = str(fix['step'])
        draw.text((x - 6, y - 8), num, fill=(255, 255, 255))

    img.convert("RGB").save(output_path, quality=95)


def upload_to_cloud(image_path, heatmap_path, experiment_id, experiment_data, report_data):
    """Upload results to Appwrite Storage & Database matching schema."""
    endpoint = os.getenv("VITE_APPWRITE_ENDPOINT", "")
    project_id = os.getenv("VITE_APPWRITE_PROJECT_ID", "")
    api_key = os.getenv("APPWRITE_API_KEY", "")
    db_id = os.getenv("APPWRITE_DATABASE_ID", "NeuromarketingDB")
    bucket_id = os.getenv("APPWRITE_STORAGE_BUCKET_ID", "neuromarketing-assets")

    if not all([endpoint, project_id, api_key]):
        return None

    try:
        from appwrite.client import Client
        from appwrite.services.storage import Storage
        from appwrite.services.databases import Databases
        from appwrite.input_file import InputFile
        from appwrite.id import ID

        client = Client()
        client.set_endpoint(endpoint)
        client.set_project(project_id)
        client.set_key(api_key)

        storage = Storage(client)
        databases = Databases(client)

        raw_id = ID.unique()
        file_result = storage.create_file(
            bucket_id=bucket_id,
            file_id=raw_id,
            file=InputFile.from_path(image_path)
        )
        file_id = getattr(file_result, 'id', getattr(file_result, '$id', raw_id))

        heatmap_file_id = None
        if os.path.exists(heatmap_path):
            hm_raw_id = ID.unique()
            hm_result = storage.create_file(
                bucket_id=bucket_id,
                file_id=hm_raw_id,
                file=InputFile.from_path(heatmap_path)
            )
            heatmap_file_id = getattr(hm_result, 'id', getattr(hm_result, '$id', hm_raw_id))

        exp_doc_data = {
            "experiment_id": experiment_id,
            "team_id": "team_general",
            "created_by_user": "user_production",
            "status": "completed",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        databases.create_document(
            database_id=db_id,
            collection_id="experiments",
            document_id=ID.unique(),
            data=exp_doc_data
        )

        winner_id = report_data.get('n_factorial', {}).get('winner', 'Baseline') if report_data.get('n_factorial') else 'Baseline'
        var_doc_data = {
            "variant_id": f"{experiment_id}_winner_{winner_id}",
            "experiment_id": experiment_id,
            "image_bucket_id": file_id,
            "heatmap_bucket_id": heatmap_file_id or file_id,
            "metrics_json": json.dumps(experiment_data)
        }
        databases.create_document(
            database_id=db_id,
            collection_id="variants",
            document_id=ID.unique(),
            data=var_doc_data
        )
        return {'asset_file_id': file_id, 'heatmap_file_id': heatmap_file_id, 'experiment_id': experiment_id}

    except Exception as e:
        logger.warning(f"Appwrite upload note: {e}")
        return None


def analyze_single_image(
    image_path: str,
    saliency_eng: SaliencyEngine,
    detector: ObjectDetector,
    biometrics_eng: BiometricsEngine,
    linguistics_eng: LinguisticsEngine,
    neuro_eng: NeuromarketingScienceEngine,
    ctr_regressor: CTRRegressor,
    output_dir: str
) -> Dict[str, Any]:
    """Analyzes any single image format with the complete multi-tier science stack."""
    image_rgb = MediaProcessor.load_image(image_path)
    orig_h, orig_w = image_rgb.shape[:2]

    # Saliency & Scanpath
    with VRAMManager.vram_stage("saliency_and_scanpath"):
        saliency_map = saliency_eng.predict_saliency(image_rgb)
        scanpath = saliency_eng.predict_scanpath(image_rgb, num_fixations=8, ior_sigma=80.0)

    # Object & Text Detection
    detections = detector.detect(image_path)
    text_blocks = [d for d in detections if d.get("source") == "EasyOCR"]
    person_blocks = [d for d in detections if d.get("source") == "YOLOv8" and d.get("label") == "person"]

    for d in detections:
        share = compute_fixation_share(saliency_map, d['bbox'])
        ttff = compute_ttff(scanpath, d['bbox'])
        d['fixation_share_pct'] = round(share, 1)
        d['ttff_ms'] = ttff

    # Biometrics (MediaPipe 3D Gaze + FACS)
    biometrics = biometrics_eng.analyze_faces(image_rgb, detected_persons=person_blocks, text_bboxes=text_blocks)

    # Linguistics (NLTK / ZuCo)
    linguistics = linguistics_eng.evaluate_copy(text_blocks, image_rgb)

    # Metrics
    metrics = compute_all_metrics(saliency_map, scanpath, saliency_eng.centerbias_template, image_rgb)

    # Neuromarketing Conversion & EEG Indices (NeuMa ds004588)
    hero_share = max([d.get("fixation_share_pct", 0) for d in person_blocks] or [40.0])
    neuro_indices = neuro_eng.compute_neuro_indices(
        s_auc=metrics["s_auc"],
        nss=metrics["nss"],
        cognitive_load_index=metrics["cognitive_load"]["cognitive_load_index"],
        hero_attention_share=hero_share,
        biometrics_data=biometrics,
        linguistics_data=linguistics
    )

    # Empirical CTR Regressor (XGBoost)
    has_gaze_cue = any(f.get("gaze_vector", {}).get("channels_into_headline") for f in biometrics.get("faces", []))
    ctr_forecast = ctr_regressor.predict_ctr(
        s_auc=metrics["s_auc"],
        nss=metrics["nss"],
        cognitive_load_index=metrics["cognitive_load"]["cognitive_load_index"],
        hero_attention_share=hero_share,
        faa_score=neuro_indices["frontal_alpha_asymmetry_faa"]["score"],
        theta_memory_pct=neuro_indices["frontal_theta_memory_encoding"]["score_pct"],
        gaze_cued_headline=has_gaze_cue,
        weber_contrast_ratio=linguistics["mobile_weber_contrast_ratio"]
    )

    # 2^3 Factorial Experiment
    hero_det = None
    if person_blocks:
        hero_det = person_blocks[0]
    elif len(detections) > 0:
        hero_det = max(detections, key=lambda x: x.get('fixation_share_pct', 0))

    if hero_det:
        with VRAMManager.vram_stage("n_factorial_matrix"):
            nfact = run_nfactorial_experiment(
                image_rgb, hero_det['bbox'], text_blocks, saliency_eng,
                output_dir=os.path.join(output_dir, "variants")
            )
    else:
        nfact = None

    # Render Visualizations
    heatmap_path = os.path.join(output_dir, "heatmap.png")
    focus_path = os.path.join(output_dir, "focus_map.png")
    scanpath_path = os.path.join(output_dir, "scanpath.png")

    render_heatmap(image_rgb, saliency_map, heatmap_path)
    render_focus_map(image_rgb, saliency_map, focus_path)
    render_scanpath(image_rgb, scanpath, biometrics, scanpath_path)

    return {
        "resolution": f"{orig_w}x{orig_h}",
        "metrics": metrics,
        "biometrics": biometrics,
        "linguistics": linguistics,
        "neuromarketing_indices": neuro_indices,
        "ctr_forecast": ctr_forecast,
        "detections": detections,
        "scanpath": scanpath,
        "n_factorial": nfact,
        "visual_artifacts": {
            "original_image": image_path,
            "thermal_heatmap": heatmap_path,
            "focus_map": focus_path,
            "scanpath_map": scanpath_path
        }
    }


def run_full_pipeline(input_media_path: str, fps_sample_rate: float = 1.0) -> dict:
    """Universal entrypoint for ANY static image or video asset."""
    start_time = time.time()
    output_dir = os.path.join(PROJECT_ROOT, "output", "analysis_results")
    os.makedirs(output_dir, exist_ok=True)

    job_id = f"job_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    experiment_id = f"exp_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    print("=" * 85)
    print("NEUROMARKETING STUDIO — UNIVERSAL MULTI-TIER SCIENTIFIC PIPELINE")
    print(f"Target Media:  {input_media_path}")
    print(f"Experiment ID: {experiment_id}")
    print("=" * 85)

    is_video = MediaProcessor.is_video(input_media_path)
    media_type = "VIDEO" if is_video else "IMAGE"
    print(f"\n[STAGE 1] INGESTION -> Media Type: {media_type}")

    # Initialize Core Engines
    saliency_eng = SaliencyEngine()
    detector = ObjectDetector()
    biometrics_eng = BiometricsEngine()
    linguistics_eng = LinguisticsEngine()
    neuro_eng = NeuromarketingScienceEngine()
    ctr_regressor = CTRRegressor()

    if not is_video:
        analysis_res = analyze_single_image(input_media_path, saliency_eng, detector, biometrics_eng, linguistics_eng, neuro_eng, ctr_regressor, output_dir)
        
        # Executive Scorecard Synthesis
        report_metrics = {
            's_auc': analysis_res["metrics"]['s_auc'],
            'nss_score': analysis_res["metrics"]['nss'],
            'cognitive_load_score': analysis_res["metrics"]['cognitive_load']['cognitive_load_index'],
            'winning_variant': analysis_res["n_factorial"]['winner'] if analysis_res["n_factorial"] else 'Baseline',
            'cohens_d_lift': analysis_res["n_factorial"]['cohens_d'] if analysis_res["n_factorial"] else 0.0,
            'faa_approach_score': analysis_res["neuromarketing_indices"]['frontal_alpha_asymmetry_faa']['score'],
            'memory_encoding_score': analysis_res["neuromarketing_indices"]['frontal_theta_memory_encoding']['score_pct'],
            'predicted_ctr': analysis_res["ctr_forecast"]["predicted_ctr_pct"],
            'viral_ctr_grade': analysis_res["neuromarketing_indices"]['viral_ctr_potential']['grade'],
            'mobile_legibility': analysis_res["linguistics"]['mobile_legibility_score'],
            'ffa_dispersion': analysis_res["biometrics"]['ffa_attentional_dispersion_index'],
            'detections': [{k: v for k, v in d.items() if k != 'saliency_map'} for d in analysis_res["detections"]],
            'scanpath_sequence': analysis_res["scanpath"]
        }
        scorecard = synthesize_executive_report(experiment_id, report_metrics)

        elapsed = time.time() - start_time
        final_report = {
            "status": "SUCCESS",
            "media_type": "STATIC_IMAGE",
            "pipeline_version": "5.0.0-master-scientific",
            "job_id": job_id,
            "experiment_id": experiment_id,
            "processing_time_seconds": round(elapsed, 1),
            "asset": {
                "filename": os.path.basename(input_media_path),
                "resolution": analysis_res["resolution"]
            },
            "metrics": analysis_res["metrics"],
            "biometrics": analysis_res["biometrics"],
            "linguistics": analysis_res["linguistics"],
            "neuromarketing_indices": analysis_res["neuromarketing_indices"],
            "ctr_forecast": analysis_res["ctr_forecast"],
            "detections": analysis_res["detections"],
            "scanpath": analysis_res["scanpath"],
            "n_factorial": analysis_res["n_factorial"],
            "scorecard": scorecard,
            "visual_artifacts": analysis_res["visual_artifacts"]
        }

        upload_to_cloud(input_media_path, analysis_res["visual_artifacts"]["thermal_heatmap"], experiment_id, analysis_res["metrics"], final_report)

    else:
        frames_dir = os.path.join(output_dir, "video_frames")
        frames = MediaProcessor.extract_video_frames(input_media_path, fps_sample_rate=fps_sample_rate, max_frames=20, output_dir=frames_dir)
        
        temporal_timeline = []
        for f in frames:
            f_res = analyze_single_image(f["frame_path"], saliency_eng, detector, biometrics_eng, linguistics_eng, neuro_eng, ctr_regressor, frames_dir)
            temporal_timeline.append({
                "timestamp_sec": f["timestamp_sec"],
                "frame_index": f["frame_index"],
                "viral_ctr_score": f_res["neuromarketing_indices"]["viral_ctr_potential"]["composite_score"],
                "predicted_ctr_pct": f_res["ctr_forecast"]["predicted_ctr_pct"],
                "faa_approach_score": f_res["neuromarketing_indices"]["frontal_alpha_asymmetry_faa"]["score"],
                "cognitive_load": f_res["metrics"]["cognitive_load"]["cognitive_load_index"],
                "face_count": f_res["biometrics"]["face_count"]
            })

        hook_scores = [t["predicted_ctr_pct"] for t in temporal_timeline if t["timestamp_sec"] <= 3.0]
        avg_hook_ctr = float(np.mean(hook_scores)) if hook_scores else 6.5

        elapsed = time.time() - start_time
        final_report = {
            "status": "SUCCESS",
            "media_type": "VIDEO",
            "pipeline_version": "5.0.0-master-scientific",
            "job_id": job_id,
            "experiment_id": experiment_id,
            "processing_time_seconds": round(elapsed, 1),
            "asset": {
                "filename": os.path.basename(input_media_path),
                "total_frames_analyzed": len(frames),
                "sample_rate_fps": fps_sample_rate
            },
            "video_temporal_analytics": {
                "initial_3s_hook_ctr_pct": round(avg_hook_ctr, 2),
                "second_by_second_timeline": temporal_timeline
            }
        }

    report_path = os.path.join(output_dir, "full_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(final_report, f, indent=2, default=str)

    print("\n" + "=" * 85)
    print(f"PIPELINE COMPLETE in {elapsed:.1f}s")
    print(f"Predicted Expected CTR: {final_report.get('ctr_forecast', {}).get('predicted_ctr_pct', 'N/A')}%")
    print("=" * 85)

    return final_report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Neuromarketing Universal Analysis Pipeline")
    parser.add_argument("--input", type=str, default=os.path.join(PROJECT_ROOT, "input_assets", "user_test_thumbnail.jpg"), help="Path to ANY image or video file")
    parser.add_argument("--fps", type=float, default=1.0, help="Sample rate for video frame extraction (default: 1.0 fps)")
    args = parser.parse_args()

    run_full_pipeline(args.input, fps_sample_rate=args.fps)