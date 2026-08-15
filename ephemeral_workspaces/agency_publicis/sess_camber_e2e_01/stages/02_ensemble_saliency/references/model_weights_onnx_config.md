# MODEL WEIGHT PATHS & ONNX RUNTIME CONFIG

## Checkpoint Paths
- DeepGaze III ONNX: `models/deepgaze_iii_fp16.onnx` (Input: `1x3x1024x1024`, Output: `1x1x1024x1024` raw logits)
- UMSI Saliency ONNX: `models/umsi_v2_fp16.onnx` (Input: `1x3x1024x1024`, Output: `1x1x1024x1024` logits)
- YOLOv10-UI Elements: `models/yolov10_ui_rico.onnx` (Labels: `Headline`, `CTA_Button`, `Hero_Image`, `Logo`, `Navigation`)
- RetinaFace 3D Gaze: `models/retinaface_gaze.onnx` (Labels: `Face_Mesh`, `Pupil_Vector_2D`, `Gaze_Direction_Deg`)

## Execution Parameters
- Precision: FP16
- Softmax Dimension: 2D Spatial over (-2, -1) axes
- Bounding Box Format: Normalized `[ymin, xmin, ymax, xmax]` in range [0.0, 1.0]
