# STAGE 02 CONTRACT: ENSEMBLE SALIENCY & DETECTION

## Inputs
- Layer 4 (working): `../01_asset_ingestion/output/manifest.json`
- Layer 3 (reference): `../../_config/onnx_tensorrt_spec.md`
- Layer 3 (reference): `../../_config/math_guardrails.md`

## Process
1. Run local inference worker:
   `python ../../scripts/onnx_inference_runner.py --manifest ../01_asset_ingestion/output/manifest.json --out output/`
2. Enforce Guardrail A: Apply spatial 2D Softmax across HxW dimensions on DeepGaze III and UMSI raw logits to ensure true probability density (integral = 1.0).
3. Execute detector suite (YOLOv10 for UI/RICO, RetinaFace for gaze, YOLOv8 for CPG/Logos).
4. Export raw density matrices as compressed `.npy` and bounding boxes as JSON.

## Outputs
- `output/raw_saliency_density.npy` -> Quantized FP16 probability arrays
- `output/detected_bboxes.json` -> Identified components with normalized [ymin, xmin, ymax, xmax] coordinates
