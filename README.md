# Neuromarketing Studio V5.0 — Consumer Cognitive & Visual Attention Analytics

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61DAFB?style=flat&logo=react)](https://reactjs.org/)
[![DeepGaze III](https://img.shields.io/badge/DeepGaze-IIE%20%26%20III-7928CA?style=flat)](https://saliency.tuebingen.ai/)
[![XGBoost](https://img.shields.io/badge/XGBoost-CTR%20Regressor-FF6600?style=flat)](https://xgboost.readthedocs.io/)
[![Appwrite](https://img.shields.io/badge/Appwrite-Cloud%20BaaS-FD366E?style=flat&logo=appwrite)](https://appwrite.io/)
[![Upstash](https://img.shields.io/badge/Upstash-Redis%20REST-00E599?style=flat&logo=redis)](https://upstash.com/)

> A distributed, multi-tier computational neuroscience platform that transforms static images and videos into high-precision visual attention density maps, macro-saccadic eye tracking scanpaths, 3D biometric gaze rays, EEG-calibrated cognitive indices, and empirical Click-Through Rate (CTR) forecasts.

---

## 🏛️ System Architecture

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
   ├── Phase 5: Nature / NeuMa (ds004588) FAA & Theta Memory Indices
   └── Phase 6: XGBoost Empirical Expected CTR Regressor
   │
   ▼ (Save Results & Realtime Event)
[Appwrite DB & Realtime WebSockets] ────► [Figma / Web Studio Live Hydration]
```

---

## 🔬 Multi-Tier Neuro-Cognitive Science Foundations

### 1. Spatial Probability Density Function
$$\iint_{\Omega} P(x, y) \, dx \, dy = 1.000000$$
Predicted via Bethge Lab's **DeepGaze IIE** (DenseNet-201 & EfficientNet-B5 backbones pretrained on MIT/Tübingen benchmarks) to model pre-attentive foveal visual capture ($0\text{--}250\text{ms}$).

### 2. Spatial Inhibition of Return (IOR) Macro-Saccade Modeling
Prevents artificial fixation clumping on single faces by suppressing previously fixated regions using a 2D Gaussian suppression kernel ($\sigma = 80\text{px}$), allowing natural saccadic eye hops across competing faces and headline text:
$$\text{IOR}(x, y) = \prod_{i=1}^{k-1} \left( 1 - \gamma \cdot \exp\left( -\frac{(x - x_i)^2 + (y - y_i)^2}{2\sigma_{\text{IOR}}^2} \right) \right), \quad \sigma_{\text{IOR}} = 80\text{px}, \, \gamma = 0.85$$

### 3. Biometric 3D Gaze Vectors & Gaze Cueing
* Evaluates 3D Head Pose and directional eye gaze rays $(x, y, z)$ using OpenCV 3D Anthropometry (`solvePnP`).
* Traces whether subject gaze rays intersect headline copy (**Directional Gaze Cueing**).
* Calculates **Fusiform Face Area (FFA) Attentional Dispersion** to detect multi-face attentional cannibalism.

### 4. Psycholinguistics & Mobile Weber Contrast
* Evaluates headline syntactic load using NLTK Flesch-Kincaid grade formulas.
* Calibrates reading dwell velocity ($200\text{ms} + 45\text{ms}/\text{syllable}$) against the ZuCo eye-tracking cognitive reading corpus.
* Simulates $1.5\text{ inch}$ mobile feed Weber luminance contrast ratio.

### 5. EEG Motivation & Memory Indices (Nature / NeuMa ds004588)
* **Frontal Alpha Asymmetry (FAA)**: Models Approach Motivation vs Withdrawal ($8\text{--}12\text{Hz}$).
* **Frontal Theta Synchronization (SME)**: Models Subsequent Memory Encoding and brand recall ($4\text{--}8\text{Hz}$).

### 6. Empirical CTR Regressor (XGBoost)
* Trained gradient boosting model mapping visual saliency feature vectors $\vec{X} = [\text{s-AUC}, \text{NSS}, \text{CLS}, \text{Hero Share}, \text{FAA}, \text{Theta}, \text{Gaze Cue}, \text{Weber Contrast}]$ into expected Click-Through Rate ($2.0\% \le \hat{y} \le 14.0\%$) and confidence intervals.

---

## 🛡️ Section 8: Failure Tolerances & Edge Cases

* **8.1 The "Middleman" Defense (Client-Direct Storage Uploads)**: The API gateway / Heroku never handles heavy binary payloads. The client uploads directly to Appwrite Storage and passes only a lightweight JSON payload (`< 1KB`) with the `file_id` to the API gateway.
* **8.2 Dynamic GPU VRAM Triage Router**: Generative/diffusion models and analytical vision models never co-exist in GPU memory. Staged sequential execution with `torch.cuda.empty_cache()` and `gc.collect()` prevents CUDA OOM crashes on 16GB/24GB GPUs.
* **8.3 Figma Sandbox / Browser "Zombie State" Hydration**: On UI boot, a `useEffect` hook queries Appwrite for in-flight (`processing`) or recent (`completed`) jobs and reconnects the Realtime WebSocket, preventing duplicate GPU compute billing.

---

## 📂 Repository Structure

```
neuromarketing-engine/
├── .devcontainer/                  # 1-click GitHub Codespaces configuration
│   └── devcontainer.json
├── .env.example                    # Redacted environment variables template
├── .gitignore                      # Secure git exclusions (.env, weights, caches)
├── requirements.txt                # Python dependencies
├── NEUROMARKETING_MASTER_SPEC_V5.md # Full master specification
├── api/
│   └── main.py                     # FastAPI Async Gateway & Client-Direct dispatcher
├── core/
│   ├── appwrite_service.py         # Direct Appwrite Storage & DB client
│   └── vram_manager.py             # Dynamic VRAM memory lifecycle manager
├── scripts/
│   ├── media_processor.py          # Universal static image & video frame extractor
│   ├── saliency_engine.py          # DeepGaze IIE & III + Spatial Gaussian IOR
│   ├── biometrics_engine.py        # 3D Gaze Vectors, FACS Emotion, FFA Dispersion
│   ├── linguistics_engine.py       # ZuCo Reading Dwell Time, Flesch-Kincaid, Weber Contrast
│   ├── neuromarketing_science.py   # NeuMa ds004588 calibrated FAA & Theta Memory
│   ├── ctr_regressor.py            # XGBoost Empirical Expected CTR Regressor
│   ├── n_factorial_engine.py       # 2^3 Combinatoric Matrix Generator + Multi-Factor ANOVA
│   ├── ingest_benchmarks.py        # Zero-screenshot benchmark dataset streamer
│   ├── report_synthesizer.py       # Strategic executive report synthesizer
│   └── run_full_pipeline.py        # Universal pipeline CLI orchestrator
├── studio/                         # Interactive Web Studio (React + Vite + Konva.js)
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── App.tsx                 # Studio Dashboard with State Hydration Hook
│       ├── components/
│       │   ├── CanvasViewer.tsx    # Interactive Canvas with Heatmap/Fog/Gaze overlays
│       │   ├── ComparisonSlider.tsx # Split-Screen A/B Factorial Slider
│       │   ├── MetricsScorecard.tsx # Real-time CTR Forecast & EEG KPIs
│       │   └── ScanpathPlayer.tsx  # 500ms Saccadic Sequence Playback Controller
│       └── styles/
│           └── main.css            # Glassmorphism Dark Mode Design System
└── workers/
    └── camber_worker.py            # Redis Queue Consumer & Camber GPU Daemon
```

---

## 🚀 Quickstart Guide

### 1. Environment Setup
```bash
# Clone the repository
git clone https://github.com/<your-username>/neuromarketing-engine.git
cd neuromarketing-engine

# Copy environment variables template
cp .env.example .env
# Edit .env and supply your Appwrite and Upstash Redis credentials
```

### 2. Install Dependencies
```bash
# Install Python packages
pip install -r requirements.txt

# Install Studio frontend packages
cd studio
npm install
cd ..
```

### 3. Run the Servers
```bash
# Terminal 1: Start FastAPI Backend Gateway
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000

# Terminal 2: Start Web Studio Frontend
cd studio
npm run dev
# Open http://localhost:3000 in your browser
```

### 4. CLI Pipeline Execution
```bash
# Analyze any static image
python scripts/run_full_pipeline.py --input "path/to/ad.jpg"

# Analyze any video (extracting keyframes at 1.0 fps)
python scripts/run_full_pipeline.py --input "path/to/video.mp4" --fps 1.0
```