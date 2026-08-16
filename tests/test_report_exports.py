from pathlib import Path

from scripts.report_exports import export_all, validate_exports


def test_export_all_validates_json_csv_xlsx_html_and_pdf(tmp_path: Path):
    report = {
        "experiment_id": "test-export",
        "evidence_status": "MODEL_PREDICTED",
        "metrics": {"s_auc": 0.8, "nss": 2.4},
        "ctr_forecast": {"predicted_ctr_pct": 6.0},
        "neuromarketing_indices": {
            "visual_approach_proxy": {"score": 0.1, "not_measured": ["EEG", "memory"]},
            "visual_encoding_proxy": {"score_pct": 55.0},
            "viral_ctr_potential": {"composite_score": 60.0, "grade": "B"},
        },
        "n_factorial": {
            "variant_results": {
                "A": {"nss": 2.4, "cognitive_load": 45.0, "hero_attention_share": 51.0},
                "B": {"nss": 2.7, "cognitive_load": 41.0, "hero_attention_share": 56.0},
            }
        },
        "limitations": ["Model-predicted only"],
    }
    paths = export_all(report, str(tmp_path), stem="report")
    validation = validate_exports(paths)
    assert set(validation) == {"json", "csv", "xlsx", "html", "pdf"}
    assert all(item["valid"] for item in validation.values())
    assert all(Path(item["path"]).exists() for item in validation.values())
