# NEUROMARKETING ATTENTION PREDICTION PLATFORM
## Complete Commercial & Computational Blueprint
### Version 4.0 | Scientifically Rigorous Execution & API Arbitrage Integration
*(Note: Video module excluded for phase 1 capital efficiency)*

---

## 1. THE PRODUCT ARCHITECTURE & THE FIGMA MOAT

If you are not embedded in the designer's workflow, your churn rate will be 100%. The product is not a standalone web app; it is a **Figma Plugin** backed by a **Pre-Processing Heuristic Engine** and an **Ensemble Model API**.

### System Architecture
1.  **Distribution Layer:** Headless Figma Plugin (React/TypeScript). Extracts frames directly from the designer's canvas.
2.  **API Router & Billing:** FastAPI server that meters usage via Stripe.
3.  **Early Visual Cortex (OpenCV):** The pre-processing layer that normalizes assets, handles color-space corrections, and computes low-level cognitive stress markers (edge complexity, visual entropy) *before* deep learning inference.
4.  **Ensemble Confidence Scorer:** Runs inputs through quantized models (DeepGaze III, UMSI). Flags epistemic uncertainty ($<70\%$ agreement).
5.  **ROI Extractor:** Bounding box integration engine.

```text
┌─────────────────────────────────────────────────────────────────┐
│                     DISTRIBUTION LAYER                          │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │                Headless Figma Plugin (React/TS)             │ │
│ │  • Frame Extraction • ROI Bounding Boxes • N-Factorial UI   │ │
│ └─────────────────────────────┬───────────────────────────────┘ │
└───────────────────────────────┼─────────────────────────────────┘
                                │ (Payload + Metadata)
┌───────────────────────────────▼─────────────────────────────────┐
│                     API ROUTER & BILLING                        │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │                  FastAPI Server (ARM/CPU)                   │ │
│ │  • Stripe Metering • Request Validation • Celery Task Queue │ │
│ └─────────────────────────────┬───────────────────────────────┘ │
└───────────────────────────────┼─────────────────────────────────┘
                                │ (Raw Assets)
┌───────────────────────────────▼─────────────────────────────────┐
│              EARLY VISUAL CORTEX (OPENCV PRE-PROCESSOR)         │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ • Normalization & Aspect Ratio Cropping                     │ │
│ │ • Low-Level Stress Markers (Text Density, Edge Contrast)    │ │
│ └─────────────────────────────┬───────────────────────────────┘ │
└───────────────────────────────┼─────────────────────────────────┘
                                │ (Processed Tensors)
┌───────────────────────────────▼─────────────────────────────────┐
│                   ENSEMBLE GPU WORKERS (ONNX)                   │
│ ┌─────────────────────────┐       ┌───────────────────────────┐ │
│ │ BASE SALIENCY ENGINES   │       │     DETECTOR SUITE        │ │
│ │ • DeepGaze III (FP16)   ├───────┤ • YOLOv10 (UI/RICO)       │ │
│ │ • UMSI (FP16)           │       │ • RetinaFace / YOLOv8     │ │
│ └─────────────────────────┘       └───────────────────────────┘ │
└───────────────────────────────┬─────────────────────────────────┘
                                │ (Tensors & Coordinates)
┌───────────────────────────────▼─────────────────────────────────┐
│            POST-PROCESSING & SCIENTIFIC EVALUATION              │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ • pysaliency Benchmark Engine (s-AUC, NSS, CC, KLD)         │ │
│ │ • True Softmax Spatial Normalization Guardrail              │ │
│ │ • ROI Analytics Engine (CTA Index, Brand Visibility, SSS)   │ │
│ └─────────────────────────────┬───────────────────────────────┘ │
└───────────────────────────────┼─────────────────────────────────┘
                                │ (JSON Metrics)
┌───────────────────────────────▼─────────────────────────────────┐
│                  REPORT GENERATION PIPELINE                     │
│ ┌───────────────┐   ┌─────────────────┐   ┌───────────────────┐ │
│ │ Claude 3.5    │──▶│ GPT-4o-mini     │──▶│ WeasyPrint PDF    │ │
│ │ (Strategy)    │   │ (HTML Tables)   │   │ (Final Dashboard) │ │
│ └───────────────┘   └─────────────────┘   └───────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. THE MATHEMATICAL OPTIMIZATION & GUARDRAIL LAYER

Do not let an LLM hallucinate loss functions or rescaling logic. All evaluations must be handled by the industry-standard `pysaliency` library.

### STRICT PROGRAMMATIC GUARDRAILS
1.  **Guardrail A (True Softmax):** Saliency models expect valid probability distributions. The AI must normalize the output array using a True Softmax function across spatial dimensions so the entire heatmap integrates to 1. Basic image scaling filters will destroy the probability density.
2.  **Guardrail B (Ground Truth Standardization):** When comparing predictions against validation data, do not leave ground truth as raw $(x,y)$ pixel points. Programmatically apply a 2D Gaussian blur with a standard deviation ($\sigma$) corresponding to **1 degree of visual angle** to generate a continuous fixation map.
3.  **Guardrail C (Continuous Metric Logging):** If a variant's NSS score drops below $1.5$, automatically flag the variant as "Visually Scattered" in the backend logs.

### CORE EVALUATION METRICS (`pysaliency`)
*   **A. Shuffled AUC (s-AUC):** 
    Treats the generated heatmap as a binary classifier, but strictly uses human fixations from *other* images as the negative control group. This mathematically strips out center-bias cheating.
*   **B. Normalized Scanpath Saliency (NSS):** 
    $$NSS(P, Q^B) = \frac{1}{N} \sum_i \frac{P_i - \mu(P)}{\sigma(P)} \cdot Q^B_i$$
    Rescales heatmap to $\mu=0, \sigma=1$ and samples at true fixation coordinates. Heavily penalizes blurry false positives.
*   **C. Linear Correlation Coefficient (CC):** 
    $$CC(P, G) = \frac{Cov(P, G)}{\sigma_P \sigma_Q}$$
    Measures the global linear "flow" of the heatmaps against ground truth.
*   **D. Kullback-Leibler Divergence (KLD):** 
    $$KLD(P, G) = \sum_i G_i \log\left(\frac{G_i}{P_i + \epsilon}\right)$$ ($\epsilon = 1e-7$)
*   **E. Information Gain (IG):** 
    $$IG = \frac{LL_{model} - LL_{centerbias}}{\ln(2)}$$

---

## 3. THE DOMAIN MODULES

### Module 1: UI/UX Design (The Wedge)
*   **Early Cortex (OpenCV):** Extracts visual entropy and edge complexity before inference.
*   **Ensemble Base:** DeepGaze III + UMSI.
*   **Detector Layer:** YOLOv10 (trained on RICO) for UI components.
*   **Core Metrics:**
    *   **Cognitive Load Score (CLS):** 
        $$CLS = \left( -\sum_{x,y} S(x,y) \log_2 S(x,y) \right) + \sum_{k=1}^{K} \mathbf{1}_{ \{ \max(S_k) > \tau \} }$$

### Module 2: Image Ads & Creatives
*   **Early Cortex (OpenCV):** Computes text density and exact aspect ratio alignment.
*   **Ensemble Base:** DeepGaze III + MSDB.
*   **Detector Layer:** RetinaFace (faces) + EAST/CRAFT (text) + YOLOv8 (logos).
*   **Core Metrics:**
    *   **Brand Attention %:** 
        $$BA = \frac{\int\int_{logo} saliency(x,y) dx dy}{\int\int_{image} saliency(x,y) dx dy} \times 100$$
    *   **Visual Clutter Index (VCI):** $VCI = -\sum(p_i \times \log_2(p_i))$

### Module 3: Shop Experience & Packaging
*   **Ensemble Base:** DeepGaze III.
*   **Detector Layer:** YOLOv8 trained on CPG products.
*   **Core Metrics:**
    *   **Shelf Standout Score (SSS):** 
        $$SSS = \frac{\mu(S_{Target Product})}{\mu(S_{Surrounding Shelf})}$$ *(Ratio > 1.5 = Excellent)*.

### Module 4: Content Creation
*   **Ensemble Base:** DeepGaze III.
*   **Detector Layer:** Google MediaPipe (Face Mesh/Gaze Vectoring).
*   **Core Metrics:**
    *   **Face-Text Gaze Alignment:** 
        $$Alignment = \cos(\theta) = \frac{\vec{gaze} \cdot \vec{text}}{\|\vec{gaze}\| \|\vec{text}\|}$$

---

## 4. THE N-FACTORIAL EXPERIMENT ENGINE (THE COMMERCIAL MOAT)

Standard A/B testing is mathematically inefficient. The N-Factorial engine acts as an Autonomous Creative Optimization Engine.

### The Combinatoric Pipeline
1.  **Inputs:** User provides variants (e.g., 3 backgrounds $\times$ 3 headlines $\times$ 2 buttons = 18 variants).
2.  **Stitching:** OpenCV programmatically generates all 18 variations in milliseconds via matrix manipulation (Bounding Box Swapping).
3.  **Neuro-Pass:** Feeds all 18 variants through the DeepGaze III pipeline to simulate human eye scanpaths (Fixation 1, 2, 3 mapping).
4.  **Ranking:** Output is ranked by predictive superiority (e.g., which design forces the most "First 2-Second Fixations" onto the CTA).

---

## 5. LLM INSIGHTS & REPORT GENERATION

1.  **Strategy Engine (Claude 3.5 Sonnet):** Ingests JSON (SSS, VCI, s-AUC, ANOVA arrays).
2.  **Formatter (GPT-4o-mini):** Structures Claude’s narrative into Markdown/HTML tables.
3.  **Compilation (WeasyPrint):** Renders HTML to a branded PDF containing the 5-section executive scorecard.

---

## 6. COMMERCIALIZATION & HYBRID API ARBITRAGE STRATEGY

To bypass millions of dollars in GPU clustering and data acquisition, use **Open-Source Layering** (hosting free models) or **API Arbitrage** (Wholesale to Retail).

### Strategy A: Open-Source Layering (Primary)
*   **Cost:** $50–$200/mo (AWS/Render). Model weights (DeepGaze III, UMSI) are $0.
*   **Execution:** Quantized models run locally on your cloud infrastructure.

### Strategy B: Commercial API Arbitrage (Fallback)
If scaling local compute becomes a bottleneck, route the backend through existing commercial APIs (e.g., EyeQuant, Brainsight) while maintaining ownership of the Figma UI.
*   **Pipeline:** Figma UI $\rightarrow$ Your API Router $\rightarrow$ Commercial API $\rightarrow$ Processed JSON $\rightarrow$ Your UI.
*   **Cost:** $200–$1000/mo API subscription.

### Subscription Tiers (Stripe Integration)
| Tier | Price | Monthly Limit | N-Factorial Limits | Target Audience |
|------|-------|---------------|--------------------|-----------------|
| **Free** | $0 | 15 tests | 1 factor only | Solo designers (lead gen) |
| **Pro** | $39/mo | 200 tests | Up to 3 factors | Freelancers / UX Designers |
| **Team** | $99/mo | Unlimited | Unlimited | Agencies / Product Teams |

---

## 7. VIBE CODING GUARDRAILS (LIMITATIONS)

You cannot write this system blind. AI coding assistants are syntax engines, not scientists.

### What Vibe Coding CAN Do:
*   Scaffold the FastAPI router and Stripe webhooks.
*   Build the React frontend for the Figma plugin.
*   Write OpenCV matrix combinatorics for the N-Factorial engine.

### What Vibe Coding CANNOT Do (Requires Human Enforcement):
*   **Loss Functions & Evaluation:** It will default to raw AUC. You must explicitly prompt it to import `pysaliency` and calculate **s-AUC**.
*   **Normalization:** It will use basic image resizing (Min-Max scaling). You must force it to apply **True Softmax**.
*   **Ground Truth Formatting:** It will leave ground truth as raw pixels. You must force the **1-degree Gaussian blur**.
