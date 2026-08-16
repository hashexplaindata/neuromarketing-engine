# NEUROMARKETING STUDIO — PREDICTIVE CREATIVE DIAGNOSTICS PLATFORM

## THE CLOUD ARCHITECTURE FLOW
┌─────────────────────────────────────────────────────────────────┐
│                    DISTRIBUTION LAYER                           │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │                Headless Figma Plugin (React/TS)             │ │
│ │  • Frame Extraction • ROI Bounding Boxes • WebSocket UI     │ │
│ └─────────────────────────────┬───────────────────────────────┘ │
└───────────────────────────────┼─────────────────────────────────┘
                                │ (HTTP POST + Appwrite JWT)
┌───────────────────────────────▼─────────────────────────────────┐
│                    API GATEWAY (HEROKU)                         │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │                  FastAPI Server (Always-On)                 │ │
│ │  • Validates Auth • Drops Payload to Redis • Returns job_id │ │
│ └─────────────────────────────┬───────────────────────────────┘ │
└───────────────────────────────┼─────────────────────────────────┘
                                │ (Upstash Redis Queue)
┌───────────────────────────────▼─────────────────────────────────┐
│               GPU WORKERS (CAMBER CLOUD L4 NODES)               │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 1. EARLY CORTEX (OpenCV): Normalization, Visual Entropy     │ │
│ │ 2. ENSEMBLE BASE (ONNX): DeepGaze III + UMSI (FP16)         │ │
│ │ 3. DETECTOR LAYER: YOLOv10 (UI) / YOLOv8 (Logos/CPG)        │ │
│ └─────────────────────────────┬───────────────────────────────┘ │
└───────────────────────────────┼─────────────────────────────────┘
                                │ (Tensors & Coordinates)
┌───────────────────────────────▼─────────────────────────────────┐
│           POST-PROCESSING & SCIENTIFIC EVALUATION               │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ • pysaliency Benchmark (s-AUC, NSS, CC, KLD)                │ │
│ │ • True Softmax Spatial Normalization & 1-Degree Gauss Blur  │ │
│ │ • ROI Analytics Engine (Pushing JSON to Appwrite DB)        │ │
│ └─────────────────────────────┬───────────────────────────────┘ │
└───────────────────────────────┼─────────────────────────────────┘
                                │ (JSON Metrics)
┌───────────────────────────────▼─────────────────────────────────┐
│                   REPORT GENERATION PIPELINE                    │
│ ┌───────────────┐   ┌─────────────────┐   ┌───────────────────┐ │
│ │ Gemini 2.0    │──▶│ HTML Scorecard  │──▶│ Appwrite Realtime │ │
│ │ (Flash API)   │   │ (Insights)      │   │ (Figma Websocket) │ │
│ └───────────────┘   └─────────────────┘   └───────────────────┘ │
└─────────────────────────────────────────────────────────────────┘

## Master Engineering & Production Specification | Version 5.0
**Target Execution Environment:** Google Antigravity IDE (Gemini 3.5 Flash)
**Monetization Status:** Deferred (Phase 2). Focus strictly on core AI value proposition and multi-tenant isolation.

---

## 1. GLOBAL CLOUD TOPOLOGY
The platform operates on a decoupled, asynchronous microservices architecture to prevent HTTP timeouts and isolate heavy GPU compute from the client interface.

1.  **Frontend (Figma Plugin):** React + TypeScript. Communicates strictly via Appwrite Realtime WebSockets and HTTP calls to Heroku.
2.  **API Gateway (Heroku):** FastAPI Python server. Validates JWTs, routes requests, and pushes inference jobs to Redis. ZERO heavy compute occurs here.
3.  **Async Queue (Upstash Redis):** Serverless message broker. Holds the `job_id` and image payloads.
4.  **GPU Workers (Camber Cloud):** NVIDIA L4 nodes running Dockerized Python/ONNX workers. Pulls from Redis, crunches DeepGaze III math, and pushes JSON to Appwrite.
5.  **BaaS / State Layer (Appwrite):** Handles User Auth, Teams API (RBAC), Document Database, Storage Buckets, and Realtime WebSocket events.

---

## 2. APPWRITE DATABASE SCHEMA & MULTI-TENANCY
The IDE must use the `appwrite` Python Server SDK to initialize this exact database (`NeuromarketingDB`) and these collections. Strict Document-Level Security (DLS) using `Role.team({team_id})` is mandatory to prevent data bleeding between agencies.

### Collection: `user_profiles`
*Tracks individual designer preferences.*
*   **Permissions:** Document Security Enabled. Read/Write: `Role.user({user_id})`.
*   **Attributes:**
    *   `user_id` (String, Required, Primary Key via ID.custom)
    *   `default_module` (String, Default: "UI/UX")
    *   `ui_theme` (String, Default: "dark")

### Collection: `org_settings`
*The Factory Configurations. Tracks agency-specific heuristics.*
*   **Permissions:** Document Security Enabled. Read: `Role.team({team_id})`. Write: `Role.team({team_id}, "admin")`.
*   **Attributes:**
    *   `team_id` (String, Required, Primary Key via ID.custom)
    *   `custom_domain_boosts` (String, Optional) - *Stringified JSON of heuristic multipliers.*
    *   `report_branding` (String, Optional) - *Stringified JSON for PDF hex codes/logos.*
    *   `monthly_quota_remaining` (Integer, Default: 50) - *Protects server costs in Phase 1.*

### Collection: `experiments`
*The Master Job tracking the N-Factorial matrix.*
*   **Permissions:** Document Security Enabled. Read/Write: `Role.team({team_id})`.
*   **Attributes:**
    *   `experiment_id` (String, Required, Primary Key)
    *   `team_id` (String, Required)
    *   `created_by_user` (String, Required)
    *   `status` (String, Required) - *Must be ENUM: `queued`, `processing`, `completed`, `failed`.*
    *   `created_at` (Datetime, Required)

### Collection: `variants`
*The specific generated layouts and their analytical scores.*
*   **Permissions:** Document Security Enabled. Read/Write: `Role.team({team_id})`.
*   **Attributes:**
    *   `variant_id` (String, Required, Primary Key)
    *   `experiment_id` (String, Required) - *Relates to `experiments` collection.*
    *   `image_bucket_id` (String, Required) - *Appwrite Storage file ID of the raw image.*
    *   `heatmap_bucket_id` (String, Optional) - *Appwrite Storage file ID of the generated heatmap.*
    *   `metrics_json` (String, Optional) - *Stringified JSON containing `s-AUC`, `NSS`, `CC` scores.*

---

## 3. FIGMA PLUGIN REAL-TIME STATE MACHINE (REACT)
The frontend must never use polling (e.g., `setInterval`) to check if the GPU is finished. It must use Appwrite's native WebSocket Realtime API.

*   **State 1: Selection & ROI Canvas:** User selects Figma frames, draws bounding boxes, and clicks "Run Experiment". Plugin POSTs to Heroku FastAPI.
*   **State 2: The Async Wait:** UI displays a loading state. Plugin subscribes to the Appwrite Realtime channel: 
    `client.subscribe('databases.[NeuromarketingDB].collections.[experiments].documents.[experiment_id]')`
*   **State 3: Execution Trigger:** When the Camber GPU worker finishes, it updates the Appwrite `experiments` document `status` to `completed`.
*   **State 4: Analytics Dashboard:** The WebSocket event instantly triggers the React UI to fetch the `variants` data, rendering the heatmap overlays and LLM scorecards over the Figma canvas.

---

## 4. MATHEMATICAL & NEUROSCIENCE KERNEL (GPU WORKERS)
The Python worker running on Camber Cloud MUST adhere strictly to these computational methodologies.

### Pre-Processing (OpenCV)
Before AI inference, run structural heuristics:
*   Extract Visual Entropy: $H = -\sum (p \times \log_2(p))$
*   Extract Canny edge density and Michelson contrast ratios.

### Base Saliency Execution (ONNX Runtime)
*   Execute quantized DeepGaze III and UMSI models in FP16 precision.
*   **GUARDRAIL A (True Softmax):** Output tensors must be normalized via spatial 2D Softmax across HxW dimensions to ensure a true probability density where the integral equals 1.0. 

### Benchmark Evaluation (`pysaliency` library)
*   **s-AUC (Shuffled AUC):** Must use human fixations from off-target dataset images as the negative control group to mathematically strip out center-bias.
*   **NSS (Normalized Scanpath Saliency):** Heatmap rescaled to $\mu=0, \sigma=1$ and sampled at true fixation coordinates.
*   **GUARDRAIL B (Ground Truth):** Raw $(x,y)$ pixel validation points must be transformed via a 2D Gaussian blur ($\sigma = 1$ degree of visual angle).
*   **GUARDRAIL C (Logging):** Any variant scoring an NSS $< 1.5$ must be flagged with `is_scattered: true` in the `metrics_json`.

---

## 5. THE LLM REPORTING ENGINE
Because we are utilizing the Google ecosystem (GitHub Student Pack/Google One):
*   **SDK:** `google-generativeai`
*   **Model:** `gemma-4-31b-it`
*   **Execution:** Triggered locally by the Python worker at the end of the pipeline. Injects the computed JSON metrics into a strict system prompt to output the Executive Scorecard (Strengths, Risks, Fixes) in HTML format for the PDF compiler.

---

## 6. THE ICM FOLDER DIRECTORY (THE EXECUTION ENGINE)
The Antigravity IDE must construct this exact filesystem to handle the local workflow routing:

```text
neuromarketing-engine/
├── AGENTS.md                                    # Layer 0: Global Identity & Protocol
├── CONTEXT.md                                   # Layer 1: Workspace Routing
├── _config/                                     # Layer 3: The Factory
│   └── NEUROMARKETING_MASTER_SPEC_V5.md         # THIS FILE
├── scripts/                                     # Mechanical Python CLI tools
│   ├── appwrite_init.py                         # SDK script to build the DB schema
│   ├── opencv_preprocessor.py                   
│   ├── onnx_worker.py                           
│   └── report_synthesizer.py                    # Gemini API execution
└── stages/
    ├── 01_asset_ingestion/
    ├── 02_ensemble_saliency/
    ├── 03_n_factorial_engine/
    ├── 04_domain_roi_analytics/
    ├── 05_epistemic_validation/
    └── 06_strategic_synthesis/
```
## 7. THE DOMAIN MODULES & PIPELINES

### Module 1: UI/UX Design (The Wedge)
*   **Early Cortex (OpenCV):** Extracts visual entropy and edge complexity before inference.
*   **Ensemble Base:** DeepGaze III + UMSI.
*   **Detector Layer:** YOLOv10 (trained on RICO dataset) for UI components.
*   **Core Metric - Cognitive Load Score (CLS):** 
    $$CLS = \left( -\sum_{x,y} S(x,y) \log_2 S(x,y) \right) + \sum_{k=1}^{K} \mathbf{1}_{ \{ \max(S_k) > \tau \} }$$

### Module 2: Image Ads & Creatives
*   **Early Cortex (OpenCV):** Computes text density and exact aspect ratio alignment.
*   **Ensemble Base:** DeepGaze III + MSDB.
*   **Detector Layer:** RetinaFace (faces) + EAST/CRAFT (text) + YOLOv8 (logos).
*   **Core Metric - Brand Attention % (BA):** 
    $$BA = \frac{\int\int_{logo} saliency(x,y) dx dy}{\int\int_{image} saliency(x,y) dx dy} \times 100$$
    *Also computes Visual Clutter Index (VCI):* $VCI = -\sum(p_i \times \log_2(p_i))$

### Module 3: Shop Experience & Packaging
*   **Ensemble Base:** DeepGaze III.
*   **Detector Layer:** YOLOv8 trained on CPG products.
*   **Core Metric - Shelf Standout Score (SSS):** 
    $$SSS = \frac{\mu(S_{Target Product})}{\mu(S_{Surrounding Shelf})}$$ 
    *(Rule: Ratio > 1.5 triggers an "Excellent" classification).*

### Module 4: Content Creation
*   **Ensemble Base:** DeepGaze III.
*   **Detector Layer:** Google MediaPipe (Face Mesh/Gaze Vectoring).
*   **Core Metric - Face-Text Gaze Alignment:** 
    $$\cos(\theta) = \frac{\vec{gaze} \cdot \vec{text}}{\|\vec{gaze}\| \|\vec{text}\|}$$    