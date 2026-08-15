# NEUROMARKETING MASTER SPECIFICATION (V5.0 - PRODUCTION BULLETPROOF)

## 1. System Architecture Overview
The Neuromarketing Engine is a distributed, multi-tier consumer neuroscience and visual attention analytics platform.
It combines peer-reviewed spatial saliency networks, 3D biometric gaze tracking, psycholinguistics, and EEG-calibrated conversion modeling.

```
[Figma Plugin / React UI] 
   │ (Direct Binary Upload)
   ▼
[Appwrite Cloud Storage Bucket] ────► [Returns File ID]
   │                                         │
   ▼                                         ▼
[FastAPI Gateway] ◄─── (Tiny JSON Payload: File ID)
   │
   ▼ (LPUSH JSON Task)
[Upstash Redis Queue]
   │
   ▼ (BRPOP Task)
[Camber GPU Worker Cluster]
   ├── Phase 1: Dynamic Triage / Generative Compositor (VRAM Flushed)
   ├── Phase 2: DeepGaze IIE & III + Spatial IOR (sigma=80px)
   ├── Phase 3: MediaPipe 3D Gaze Vectors & FACS Amygdala Arousal
   ├── Phase 4: NLTK & ZuCo Cognitive Linguistics & Mobile Contrast
   └── Phase 5: Nature / NeuMa (ds004588) FAA & Theta Memory Indices
   │
   ▼ (Save Results & Realtime Event)
[Appwrite DB & Realtime WebSockets] ────► [Figma / Web Studio Live Hydration]
```

---

## 2. Mathematical & Neuro-Cognitive Foundations
1. **Spatial Probability Density Function**:
   $$\iint_{\Omega} P(x, y) \, dx \, dy = 1.000000$$
   Predicted via Bethge Lab's **DeepGaze IIE** (EfficientNet-B5 & DenseNet-201 backbone pretrained on MIT1003).

2. **Spatial Inhibition of Return (IOR) Macro-Saccade Modeling**:
   For fixation step $k \in \{1, \dots, N\}$ at coordinate $(x_k, y_k)$:
   $$\text{IOR}(x, y) = \prod_{i=1}^{k-1} \left( 1 - \gamma \cdot \exp\left( -\frac{(x - x_i)^2 + (y - y_i)^2}{2\sigma_{\text{IOR}}^2} \right) \right), \quad \sigma_{\text{IOR}} = 80\text{px}, \, \gamma = 0.85$$

3. **Frontal Alpha Asymmetry (FAA Index)**:
   $$\text{FAA} = \ln(\text{Alpha}_{\text{Right}}) - \ln(\text{Alpha}_{\text{Left}})$$
   Calibrated from the **Nature / OpenNeuro ds004588 (NeuMa)** dataset to model consumer Approach Motivation vs Withdrawal.

4. **Frontal Theta Memory Encoding Index (SME)**:
   Models Subsequent Memory Effect and long-term brand recall potential from $4\text{–}8\text{Hz}$ synchronization.

---

## 3. Biometric Gaze & Facial Action Coding System (FACS)
* **3D Head Pose & Gaze Vector**: Evaluated via OpenCV 3D Anthropometric model (`solvePnP`) to compute $(x, y, z)$ ray direction.
* **Directional Gaze Cueing**: Evaluates whether subjects' gaze rays intersect headline copy to channel viewer saccades.
* **FFA Attentional Dispersion**: Measures attentional cannibalism and saccadic ping-pong across competing human faces.

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

Evaluated via One-Way / Two-Way ANOVA ($F$-statistic, $p$-value) and bootstrap Cohen's $d$ effect size.

---

## 6. Cloud Services Configuration
* **Appwrite Cloud BaaS**:
  * Endpoint: `https://cloud.appwrite.io/v1`
  * Project ID: `neuromarketing-engine`
  * Database ID: `NeuromarketingDB`
  * Storage Bucket: `neuromarketing-assets`
  * Collections: `experiments`, `variants`
* **Upstash Redis REST Queue**:
  * Queue Key: `queue:analysis_jobs`
  * Job Status Keys: `job:<job_id>:status`

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
  4. FastAPI pushes the JSON to Upstash Redis.
  5. Camber GPU worker streams the file directly from Appwrite Storage.
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
  1. **Boot Hydration**: On plugin mount (`useEffect`), query Appwrite `experiments` collection for any experiment with `created_by_user` matching the session with `status == "processing"` or `status == "completed"` created within the last 60 minutes.
  2. **Live Reconnection**: If an active job is found, immediately re-attach to the Appwrite Realtime WebSocket subscription for that `experiment_id` and transition UI into the Live Analytics Dashboard.
* **Result**: Eliminates ghost jobs, prevents accidental duplicate GPU compute billing, and preserves designer workflow continuity.