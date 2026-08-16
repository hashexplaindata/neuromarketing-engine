"""Media adapters for Neuromarketing Studio.

The adapter layer normalizes marketer assets into either visual frames or
structured observations. It does not infer attention, emotion, memory, EEG,
or conversion from a file merely because the file is accepted.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from pdf2image import convert_from_path

from scripts.media_processor import MediaProcessor


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif", ".avif"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
PDF_EXTENSIONS = {".pdf"}
DOCUMENT_EXTENSIONS = {".doc", ".docx", ".odt", ".rtf", ".txt", ".html", ".htm"}
SPREADSHEET_EXTENSIONS = {".xls", ".xlsx", ".xlsm", ".ods", ".csv", ".tsv"}
SURVEY_EXTENSIONS = {".json", ".jsonl", ".csv", ".tsv", ".xlsx", ".xls"}
EYE_TRACKING_EXTENSIONS = {".asc", ".tsv", ".csv", ".txt", ".json", ".jsonl"}
EEG_EXTENSIONS = {".edf", ".bdf", ".fif", ".set", ".vhdr", ".eeg"}
PRESENTATION_EXTENSIONS = {".ppt", ".pptx", ".odp", ".key"}


class UnsupportedMediaError(ValueError):
    """Raised when a file type is intentionally unsupported or needs an optional parser."""


def detect_media_type(path: str) -> str:
    extension = Path(path).suffix.lower()
    if extension in IMAGE_EXTENSIONS:
        return "image"
    if extension in VIDEO_EXTENSIONS:
        return "video"
    if extension in PDF_EXTENSIONS:
        return "pdf"
    if extension in DOCUMENT_EXTENSIONS:
        return "document"
    if extension in SPREADSHEET_EXTENSIONS:
        return "spreadsheet"
    if extension in EEG_EXTENSIONS:
        return "eeg"
    if extension in PRESENTATION_EXTENSIONS:
        return "presentation"
    return "structured"


def _require_file(path: str) -> Path:
    candidate = Path(path)
    if not candidate.exists() or not candidate.is_file():
        raise FileNotFoundError(f"Media asset not found: {path}")
    return candidate


def render_pdf_pages(path: str, output_dir: str, dpi: int = 150, max_pages: int = 30) -> List[Dict[str, Any]]:
    """Render PDF pages into RGB analysis frames with page metadata."""
    source = _require_file(path)
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    pages = convert_from_path(str(source), dpi=dpi, first_page=1, last_page=max_pages)
    frames: List[Dict[str, Any]] = []
    for index, page in enumerate(pages):
        frame_path = target / f"page_{index + 1:03d}.png"
        page.convert("RGB").save(frame_path, format="PNG")
        frames.append({
            "frame_index": index,
            "page_number": index + 1,
            "timestamp_sec": None,
            "frame_path": str(frame_path),
            "source_type": "pdf_page",
        })
    return frames


def render_office_document(path: str, output_dir: str, max_pages: int = 30) -> List[Dict[str, Any]]:
    """Convert an Office/OpenDocument file to PDF with LibreOffice, then render pages."""
    source = _require_file(path)
    if not shutil.which("libreoffice") and not shutil.which("soffice"):
        raise UnsupportedMediaError("LibreOffice is required to render this document type")
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="neuromarketing-office-") as temporary:
        command = [
            shutil.which("libreoffice") or shutil.which("soffice"),
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            temporary,
            str(source),
        ]
        completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=120)
        pdf_path = Path(temporary) / f"{source.stem}.pdf"
        if completed.returncode != 0 or not pdf_path.exists():
            raise UnsupportedMediaError(
                f"Office rendering failed for {source.name}: {completed.stderr[-500:]}"
            )
        return render_pdf_pages(str(pdf_path), str(target), max_pages=max_pages)


def _read_structured(path: str) -> Any:
    source = _require_file(path)
    extension = source.suffix.lower()
    if extension in {".csv", ".tsv"}:
        return pd.read_csv(source, sep="\t" if extension == ".tsv" else ",")
    if extension in {".xls", ".xlsx", ".xlsm", ".ods"}:
        sheets = pd.read_excel(source, sheet_name=None)
        return {name: frame for name, frame in sheets.items()}
    if extension == ".jsonl":
        with source.open("r", encoding="utf-8") as handle:
            return pd.DataFrame([json.loads(line) for line in handle if line.strip()])
    if extension == ".json":
        with source.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, list):
            return pd.DataFrame(payload)
        if isinstance(payload, dict) and all(isinstance(value, list) for value in payload.values()):
            return pd.DataFrame(payload)
        return payload
    raise UnsupportedMediaError(f"No structured parser for {source.suffix}")


def _frame_structured_data(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, pd.DataFrame):
        return data.head(1000).where(pd.notna(data), None).to_dict(orient="records")
    if isinstance(data, dict) and all(isinstance(value, pd.DataFrame) for value in data.values()):
        rows: List[Dict[str, Any]] = []
        for sheet_name, frame in data.items():
            for row in frame.head(1000).where(pd.notna(frame), None).to_dict(orient="records"):
                rows.append({"sheet_name": sheet_name, **row})
        return rows
    if isinstance(data, dict):
        return [data]
    return []


def _columns(rows: List[Dict[str, Any]]) -> List[str]:
    names = set()
    for row in rows:
        names.update(row.keys())
    return sorted(str(name) for name in names)


def normalize_eye_tracking(path: str) -> Dict[str, Any]:
    """Normalize common eye-tracking exports without claiming neural measurement."""
    data = _read_structured(path)
    rows = _frame_structured_data(data)
    if not rows:
        raise ValueError("Eye-tracking file contains no rows")
    columns = {name.lower(): name for name in _columns(rows)}
    x_name = next((columns[name] for name in ("x", "gaze_x", "fixation_x", "x_position") if name in columns), None)
    y_name = next((columns[name] for name in ("y", "gaze_y", "fixation_y", "y_position") if name in columns), None)
    time_name = next((columns[name] for name in ("timestamp", "timestamp_ms", "time", "time_ms", "start_time") if name in columns), None)
    if not x_name or not y_name or not time_name:
        raise ValueError("Eye-tracking data requires x, y, and timestamp-like columns")
    return {
        "data_type": "eye_tracking_observations",
        "evidence_status": "MEASURED_INSTRUMENT_DATA",
        "columns": _columns(rows),
        "coordinate_columns": {"x": x_name, "y": y_name, "time": time_name},
        "n_observations": len(rows),
        "observations": rows,
        "interpretation_boundary": "These are instrument-exported gaze observations; calibration quality, sampling rate, missingness, AOIs, and participant/session identifiers must be validated before group inference.",
    }


def normalize_eeg(path: str) -> Dict[str, Any]:
    """Read EEG metadata only when MNE is installed; no neural interpretation is performed."""
    source = _require_file(path)
    try:
        import mne
    except ImportError as exc:
        raise UnsupportedMediaError("Install the optional 'mne' dependency to ingest EEG files") from exc
    raw = mne.io.read_raw(str(source), preload=False, verbose="ERROR")
    return {
        "data_type": "eeg_recording_metadata",
        "evidence_status": "MEASURED_INSTRUMENT_DATA",
        "filename": source.name,
        "channel_names": list(raw.ch_names),
        "sampling_frequency_hz": float(raw.info["sfreq"]),
        "duration_seconds": float(raw.n_times / raw.info["sfreq"]),
        "n_channels": len(raw.ch_names),
        "interpretation_boundary": "EEG ingestion does not by itself establish FAA, theta, emotion, memory, or clinical/psychological state. A preregistered preprocessing and analysis plan is required.",
    }


def prepare_media_bundle(path: str, output_dir: str, max_frames: int = 30) -> Dict[str, Any]:
    """Normalize one asset into visual frames, structured observations, or both."""
    source = _require_file(path)
    media_type = detect_media_type(str(source))
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    if media_type == "image":
        return {
            "media_type": media_type,
            "filename": source.name,
            "evidence_status": "MODEL_INPUT_ASSET",
            "frames": [{"frame_index": 0, "frame_path": str(source), "source_type": "image"}],
            "structured_data": None,
        }
    if media_type == "video":
        frames = MediaProcessor.extract_video_frames(str(source), max_frames=max_frames, output_dir=str(target / "frames"))
        return {
            "media_type": media_type,
            "filename": source.name,
            "evidence_status": "MODEL_INPUT_ASSET",
            "frames": [{key: value for key, value in frame.items() if key != "image_rgb"} for frame in frames],
            "structured_data": None,
        }
    if media_type == "pdf":
        return {"media_type": media_type, "filename": source.name, "evidence_status": "MODEL_INPUT_ASSET", "frames": render_pdf_pages(str(source), str(target / "pages")), "structured_data": None}
    if media_type == "document":
        return {"media_type": media_type, "filename": source.name, "evidence_status": "MODEL_INPUT_ASSET", "frames": render_office_document(str(source), str(target / "pages"), max_pages=max_frames), "structured_data": None}
    if media_type == "spreadsheet":
        structured = _read_structured(str(source))
        structured_rows = _frame_structured_data(structured)
        structured_columns = {name.lower() for name in _columns(structured_rows)}
        has_gaze_coordinates = (
            {"x", "y"}.issubset(structured_columns)
            or {"gaze_x", "gaze_y"}.issubset(structured_columns)
            or {"fixation_x", "fixation_y"}.issubset(structured_columns)
        )
        has_time = any(name in structured_columns for name in {"timestamp", "timestamp_ms", "time", "time_ms", "start_time"})
        if has_gaze_coordinates and has_time:
            normalized = normalize_eye_tracking(str(source))
            normalized["observations"] = structured_rows
            return {"media_type": "eye_tracking", "filename": source.name, "frames": [], "structured_data": normalized}
        try:
            frames = render_office_document(str(source), str(target / "pages"), max_pages=max_frames)
        except UnsupportedMediaError:
            frames = []
        return {
            "media_type": media_type,
            "filename": source.name,
            "evidence_status": "MIXED_MEASURED_DATA_AND_MODEL_INPUT",
            "frames": frames,
            "structured_data": {"columns": _columns(structured_rows), "rows": structured_rows},
        }
    if media_type == "eeg":
        return {"media_type": media_type, "filename": source.name, "frames": [], "structured_data": normalize_eeg(str(source))}
    if media_type == "presentation":
        raise UnsupportedMediaError("PowerPoint/presentation adapters are intentionally postponed per product scope")

    structured = _read_structured(str(source))
    rows = _frame_structured_data(structured)
    columns = {name.lower() for name in _columns(rows)}
    if {"x", "y"}.issubset(columns) or any(name in columns for name in {"gaze_x", "gaze_y", "fixation_x", "fixation_y"}):
        structured_data = normalize_eye_tracking(str(source))
        structured_data["observations"] = rows
        return {"media_type": "eye_tracking", "filename": source.name, "frames": [], "structured_data": structured_data}
    return {
        "media_type": "structured",
        "filename": source.name,
        "evidence_status": "MEASURED_STRUCTURED_DATA",
        "frames": [],
        "structured_data": {"columns": _columns(rows), "rows": rows},
    }
