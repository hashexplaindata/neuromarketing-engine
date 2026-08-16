# NEUROMARKETING MASTER SPECIFICATION (V5.0 - PRODUCTION BULLETPROOF)

## 1. System Architecture Overview
Neuromarketing Studio is a distributed, multi-tier creative-diagnostics and visual-attention analytics platform.
It combines pretrained spatial saliency models, geometric gaze/head-pose diagnostics, psycholinguistic and visual-complexity analysis, controlled creative comparisons, and explicitly bounded model-derived conversion proxies. It does not infer neural or psychological states from image-only input.

```
[Figma Plugin / React Studio]
   │ (Direct Binary Upload)
   ▼
[Appwrite Cloud Storage Bucket] ────► [Returns File ID]
   │                                         │
   ▼                                         ▼
[FastAPI Gateway] ◄─── (Tiny JSON Payload: File ID)
   │
   ▼ (Modal async function call)
[Modal L4 GPU Worker: process_job]
   ├── Phase 1: Dynamic Triage / Staged VRAM Lifecycle
   ├── Phase 2: DeepGaze IIE & III + Spatial IOR (sigma=80px)
   ├── Phase 3: Geometric Gaze/Head-Pose & Gaze Cueing
   ├── Phase 4: NLTK / Copy Analysis / Mobile Contrast
   └── Phase 5: Model-Derived Visual Proxies & CTR Proxy
   │
   ▼ (Save Results & Realtime Event)
[Appwrite TablesDB, Storage & Realtime] ────► [Figma / Web Studio Live Hydration]
```

---

## 2. Mathematical & Neuro-Cognitive Foundations
1. **Spatial Probability Density Function**:
   $$\iint_{\Omega} P(x, y) \, dx \, dy = 1.000000$$
   Predicted via Bethge Lab's **DeepGaze IIE** (EfficientNet-B5 & DenseNet-201 backbone pretrained on MIT1003).

2. **Spatial Inhibition of Return (IOR) Macro-Saccade Modeling**:
   For fixation step $k \in \{1, \dots, N\}$ at coordinate $(x_k, y_k)$:
   $$\text{IOR}(x, y) = \prod_{i=1}^{k-1} \left( 1 - \gamma \cdot \exp\left( -\frac{(x - x_i)^2 + (y - y_i)^2}{2\sigma_{\text{IOR}}^2} \right) \right), \quad \sigma_{\text{IOR}} = 80\text{px}, \, \gamma = 0.85$$

3. **Model-Derived Visual Engagement Proxy**:
   A transparent weighted combination of visual saliency discrimination, focal-region share, copy legibility, visual expression contrast, and detected-person competition. The output is a model-derived visual proxy and is not an EEG or motivation measure.

4. **Model-Derived Visual Encoding-Related Proxy**:
   A bounded diagnostic based on predicted saliency statistics, visual hierarchy, legibility, and face-competition geometry. It is not a measure of memory encoding, recall, or frontal theta synchronization.

---

## 3. Geometric Gaze, Head Pose & Visual Face Competition
* **3D Head Pose & Gaze Vector**: Evaluated via OpenCV 3D Anthropometric model (`solvePnP`) to compute $(x, y, z)$ ray direction.
* **Directional Gaze Cueing**: Evaluates whether subjects' gaze rays intersect headline copy to channel viewer saccades.
* **Visual face-competition index**: Summarizes detected-person geometry as a layout diagnostic; it does not measure FFA activity, neural localization, emotion, or attentional state.

---

## 4. Cognitive Linguistics & Mobile Scale Legibility
* **Flesch-Kincaid Grade Level & Reading Ease**: Evaluates headline syntactic load.
* **ZuCo Reading Velocity**: Dwell time calculated at $200\text{ms} + 45\text{ms}/\text{syllable}$.
* **Mobile 1.5-inch Feed Weber Luminance Contrast**:
   $$C_W = \frac{L_{\text{text}} - L_{\text{bg}}}{L_{\text{bg}} + \epsilon}$$

---

## 5. $2^3$ N-Factorial Multivariate Combinatorics & Multi-Way ANOVA
Generates all 8 structural creative combinations:
* **Factor A (Subject Density)**: Multi-Person Panel vs 1-Person Hero Solo Crop
* **Factor B (Typography)**: Baseline Low-Contrast vs High-Luminance Viral Yellow (`#FFE600`)
* **Factor C (Lighting & Contrast)**: Baseline Lighting vs High-Separation Silhouette

The predictive engine reports model-derived diagnostic intervals and an explicit `NO_EMPIRICAL_PARTICIPANT_INFERENCE` status. Separate empirical A/B and factorial analysis functions accept observed experimental-unit outcomes, require replicated cells, report effect sizes and bootstrap confidence intervals, apply Holm correction across terms, and preserve the boundary between prediction and inference.

---

## 6. Cloud Services Configuration
* **Appwrite Cloud BaaS**:
  * Endpoint: `https://cloud.appwrite.io/v1`
  * Project ID: `neuromarketing-engine`
  * Database ID: `NeuromarketingDB`
  * Storage Bucket: `neuromarketing-assets`
  * Tables: `jobs`, `analysis_results`, `experiments`, `variants`, and tenant-scoped profile/settings tables.
* **Modal GPU execution**:
  * App: `neuromarketing-studio`
  * Function: `process_job`
  * GPU: NVIDIA L4
  * Runtime Secret: `neuromarketing-studio-runtime`

---

## 7. Client & Backend Specifications
* **FastAPI Server**: Lightweight async API gateway for queuing jobs and status telemetry.
* **React / Figma Frontend**: Interactive canvas with AOI polygon tools, split-screen A/B comparison slider, and animated scanpath playback.

---

## 8. Failure Tolerances & Critical Edge Cases

### 8.1. The Payload Bottleneck (The "Middleman" Defense)
* **Constraint**: The API Gateway / Heroku must **NEVER** handle raw image/video binary payloads.
* **Architecture**:
  1. Client uploads binary asset **directly to Appwrite Cloud Storage** (`neuromarketing-assets`) via Appwrite Client SDK.
  2. Appwrite returns a lightweight unique `file_id`.
  3. Client dispatches a **micro-payload JSON** (`< 1KB`) containing `{ "file_id": "...", "experiment_id": "..." }` to the FastAPI gateway.
  4. FastAPI creates an Appwrite job row and submits the JSON payload asynchronously to Modal.
  5. The Modal GPU worker streams the file directly from Appwrite Storage.
* **Result**: Zero H12 request timeouts, zero gateway bandwidth bottlenecks.

### 8.2. GPU VRAM Exhaustion (Dynamic VRAM Triage Router)
* **Constraint**: Generative diffusion models (FLUX/SD) and analytical vision models (DeepGaze, DenseNet, YOLO) must **NEVER** co-exist in GPU memory.
* **Architecture**:
  1. **Phase 1 (Generative Triage)**: If generating variant assets, load Generative Model $\to$ Synthesize variants $\to$ Write output to Appwrite $\to$ Explicitly delete model and execute `torch.cuda.empty_cache()` + `gc.collect()`.
  2. **Phase 2 (Analytical Saliency & Neuro)**: Load DeepGaze IIE & III + YOLO + MediaPipe $\to$ Run inference and psychophysics $\to$ Flush cache.
* **Result**: Prevents CUDA Out-Of-Memory (OOM) fatal crashes on 16GB/24GB GPUs (NVIDIA L4 / T4).

### 8.3. Figma Sandbox "Zombie State" (Resilient State Hydration)
* **Constraint**: User closing or refreshing the Figma plugin / browser window must **NEVER** lose in-flight analysis or trigger duplicate compute jobs.
* **Architecture**:
  1. **Boot Hydration**: On plugin mount (`useEffect`), query the Appwrite `experiments` table for any experiment with `created_by_user` matching the session with `status == "processing"` or `status == "completed"` created within the last 60 minutes.
  2. **Live Reconnection**: If an active job is found, immediately re-attach to the Appwrite Realtime WebSocket subscription for that `experiment_id` and transition UI into the Live Analytics Dashboard.
* **Result**: Eliminates ghost jobs, prevents accidental duplicate GPU compute billing, and preserves designer workflow continuity.