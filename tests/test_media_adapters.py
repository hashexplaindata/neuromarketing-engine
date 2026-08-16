from pathlib import Path

import pandas as pd
import pytest
from reportlab.pdfgen import canvas

from scripts.media_adapters import UnsupportedMediaError, prepare_media_bundle


def test_pdf_is_rendered_to_analysis_frames(tmp_path: Path):
    pdf_path = tmp_path / "brief.pdf"
    pdf = canvas.Canvas(str(pdf_path))
    pdf.drawString(72, 720, "Neuromarketing Studio test brief")
    pdf.save()

    bundle = prepare_media_bundle(str(pdf_path), str(tmp_path / "output"))
    assert bundle["media_type"] == "pdf"
    assert len(bundle["frames"]) == 1
    assert Path(bundle["frames"][0]["frame_path"]).exists()


def test_spreadsheet_is_available_as_structured_data(tmp_path: Path):
    workbook = tmp_path / "survey.xlsx"
    pd.DataFrame({"variant": ["A", "B"], "click": [0, 1]}).to_excel(workbook, index=False)

    bundle = prepare_media_bundle(str(workbook), str(tmp_path / "output"))
    assert bundle["media_type"] == "spreadsheet"
    assert "variant" in bundle["structured_data"]["columns"]
    assert len(bundle["structured_data"]["rows"]) == 2


def test_eye_tracking_csv_requires_coordinate_and_time_columns(tmp_path: Path):
    csv_path = tmp_path / "gaze.csv"
    pd.DataFrame({"timestamp_ms": [0, 16], "x": [100, 110], "y": [200, 205]}).to_csv(csv_path, index=False)

    bundle = prepare_media_bundle(str(csv_path), str(tmp_path / "output"))
    assert bundle["media_type"] == "eye_tracking"
    assert bundle["structured_data"]["evidence_status"] == "MEASURED_INSTRUMENT_DATA"
    assert bundle["structured_data"]["n_observations"] == 2


def test_powerpoint_is_explicitly_postponed(tmp_path: Path):
    presentation = tmp_path / "deck.pptx"
    presentation.write_bytes(b"not a real deck")
    with pytest.raises(UnsupportedMediaError, match="intentionally postponed"):
        prepare_media_bundle(str(presentation), str(tmp_path / "output"))
