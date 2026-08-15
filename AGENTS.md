# NEUROMARKETING ENGINE AGENT ARCHITECTURE & CLOUD STACK DIRECTIVES

## Cloud Production Infrastructure
The Neuromarketing Production Engine is architected on the following cloud stack:
1. **API Router & WebSocket Gateway**: **Heroku** (`Procfile`, `runtime.txt`, `api/main.py`)
2. **Backend-as-a-Service (BaaS)**: **Appwrite**
   - **Auth**: Appwrite User Account JWT verification (`core/appwrite_service.py`)
   - **Database**: Appwrite Document Collections for Jobs and Session records
   - **Storage**: Appwrite Storage Buckets for creative assets and deliverables
3. **Task Queue & Real-Time Event Bus**: **Upstash Redis** (`core/upstash_queue.py`)
   - Instant task enqueuing via `RPUSH queue:camber_gpu_jobs` (< 5ms response time)
   - Real-time progress broadcasting via Redis Pub/Sub channel `job_progress:{job_id}`
4. **Accelerated Inference Workers**: **Camber Cloud** (`workers/camber_worker.py`)
   - Dedicated GPU instances executing DeepGaze III, UMSI, YOLOv10/RetinaFace, and ANOVA tests
5. **Monetization & Billing**: **NONE** (Zero Stripe/billing gates; direct execution for authenticated designers)

---

## Interpretable Context Methodology (ICM) Directives

### 1. Mandatory Ephemeral Multi-Tenancy Isolation
- Every job operates in a dynamic, tenant-isolated ephemeral workspace:
  `${EPHEMERAL_ROOT}/${tenant_id}/${session_id}/stages/01_..06_/`
- Never write intermediate outputs to global shared directory paths to prevent concurrency collisions.

### 2. Sequential 6-Stage Progression
- **Stage 01 (`01_asset_ingestion`)**: Asset normalization, Shannon entropy, Michelson contrast, Canny edge density.
- **Stage 02 (`02_ensemble_saliency`)**: DeepGaze III + UMSI TensorRT inference with 2D Softmax & YOLOv10/RetinaFace ROI detection.
- **Stage 03 (`03_n_factorial_engine`)**: 18 N-Factorial permutation generation & ANOVA / Cohen's d statistical evaluation.
- **Stage 04 (`04_domain_roi_analytics`)**: CTA Visibility Index, Cognitive Load Score, Brand Attention Share %, and Dwell Times.
- **Stage 05 (`05_epistemic_validation`)**: Model correlation coefficient (CC) and KL-Divergence (KLD) confidence audit.
- **Stage 06 (`06_strategic_synthesis`)**: Lightweight Figma vector contour isolines, 8-bit alpha mask, and executive synthesis.

### 3. Figma Canvas Optimization
- Never stream heavy raster images back to Figma. Deliver lightweight vector contour polygons (SVG vertices) and compressed 8-bit alpha overlays (< 15KB) to prevent sandboxed canvas memory crashes.
