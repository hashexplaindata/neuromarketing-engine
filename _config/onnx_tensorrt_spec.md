# ONNX & TENSORRT RUNTIME SPECIFICATIONS

## Model Quantization & Hardware Targets
- Target Precision: FP16 (Half-Precision Float)
- Execution Providers:
  1. `TensorrtExecutionProvider` (Primary, CUDA compute >= 7.5)
  2. `CUDAExecutionProvider` (Fallback GPU)
  3. `CPUExecutionProvider` (Deterministic baseline)

## Inference Constraints
- Maximum VRAM Allocation: 6.0 GB per session
- Batch Size Limits:
  * DeepGaze III Saliency Engine: Max Batch = 4
  * UMSI (Unified Model for Saliency Prediction): Max Batch = 8
  * Object / Face / Logo Detectors (YOLOv10 / RetinaFace): Max Batch = 16
- Input Resolution Standardization:
  * Standard Aspect: 1024 x 1024 or Native 16:9 / 9:16 padded tensors
  * Normalization: ImageNet Mean [0.485, 0.456, 0.406] and Std [0.229, 0.224, 0.225]
