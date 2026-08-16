import os

legal_dir = r"D:\neuromarketing-engine\legal"
os.makedirs(legal_dir, exist_ok=True)

tos_content = """# Neuromarketing Studio — Enterprise Terms of Service (ToS)

**Effective Date:** August 15, 2026  
**Product:** Neuromarketing Studio

---

## 1. Acceptance of Terms
By accessing, installing, or utilizing the Neuromarketing Studio (including the Figma Plugin, REST APIs, and Cloud Processing Services), you ("Client", "Organization", or "User") agree to be legally bound by these Terms of Service.

## 2. Description of Service
Neuromarketing Studio provides computational visual attention modeling, spatial saliency estimation (via DeepGaze III and UMSI neural backbones), cognitive load scoring, and automated executive reporting for digital marketing creatives, packaging designs, and user interfaces.

## 3. Computational Modeling & Scientific Disclaimers
* **Synthetic Predictive Modeling:** Neuromarketing Studio computes predictive visual attention maps using validated artificial neural networks and psychophysics algorithms trained on empirical human eye-tracking benchmark datasets (e.g., MIT Saliency Benchmark).
* **Non-Invasive Architecture:** Neuromarketing Studio does not operate hardware eye-tracking sensors, physical cameras, or physical biometric surveillance on end consumers. All analytics are computed synthetically from visual design assets.
* **Advisory Nature:** Saliency heatmaps, s-AUC, NSS scores, and AI recommendations are advisory design optimization tools and do not constitute absolute guarantees of commercial revenue or market performance.

## 4. Intellectual Property & Customer Asset Ownership
* **Customer Content:** The Client retains 100% full intellectual property ownership, copyright, and title to all design assets, images, copy, and creative files uploaded to Neuromarketing Studio.
* **No Training on Customer IP:** Neuromarketing Studio does NOT use customer proprietary design assets to train public foundation models without explicit written enterprise consent.
* **Platform IP:** The underlying neural network architectures, algorithms, ONNX models, software, APIs, and documentation remain the exclusive property of Neuromarketing Studio.

## 5. Data Security, Multi-Tenancy & Privacy
* Client data is strictly partitioned using Document-Level Security (DLS) and encrypted at rest and in transit through Appwrite BaaS and isolated Modal execution environments. Job records and artifacts remain tenant-scoped in Appwrite.
* Ephemeral processing workspaces are deleted in accordance with the Client's data retention policies.

## 6. Limitation of Liability
To the maximum extent permitted by applicable law, Neuromarketing Studio and its affiliates shall not be liable for indirect, incidental, special, or consequential damages resulting from marketing campaign performance, third-party platform downtime, or advertising outcomes.

## 7. Governing Law
These Terms shall be governed by and construed in accordance with applicable commercial and international software licensing laws.
"""

privacy_content = """# Neuromarketing Studio — Privacy Policy & Data Handling

**Last Updated:** August 15, 2026  

---

## 1. Information We Collect
1. **Account Information:** Email address, user ID, organization name, and role permissions managed securely through Appwrite Authentication.
2. **Creative Assets:** Image files (PNG, JPEG, WebP, SVG) submitted via the Figma Plugin or API for computational attention analysis.
3. **Telemetry & Execution Metrics:** Timestamped job IDs, processing durations, and system health telemetry to ensure SLA compliance.

## 2. How We Use Information
* To execute the deep learning saliency inference pipeline (DeepGaze III + UMSI).
* To generate real-time vector contours and executive PDF/JSON scorecards.
* To deliver push notifications and Realtime WebSocket updates to the client's Figma interface.

## 3. Data Storage & Isolation
* **Storage Location:** Uploaded assets and generated heatmaps are stored in isolated Appwrite Cloud Storage Buckets with strict tenant-level access permissions.
* **Zero Third-Party Resale:** We do not sell, rent, or trade customer creative assets or analysis results to any third party or ad broker.

## 4. Compliance (GDPR & CCPA)
* Clients have the right to request deletion of all stored variants, heatmaps, and experiment histories at any time through the dashboard or API (`DELETE /api/v1/experiments/{id}`).
"""

copywriting_content = """# Neuromarketing Studio — Brand Copywriting & Positioning System

---

## 1. Core Brand Identity
* **Product Name:** Neuromarketing Studio
* **Category:** Enterprise Predictive Visual Attention & Cognitive Neuromarketing Platform
* **Primary Tagline:** *"Predict Consumer Attention Before You Launch."*
* **Secondary Taglines:**
  * *"The Scientific Standard for Visual Saliency & Conversion Optimization."*
  * *"Eliminate Guesswork with Computational Neuroscience in Figma."*

---

## 2. Core Value Pillars (Copy Matrix)

### Pillar 1: Sub-Second Predictive Heatmaps
* **Headline:** See What Your Customers See in the First 250 Milliseconds.
* **Body:** Powered by DeepGaze III and UMSI neural backbones, Neuromarketing Studio models the human visual cortex to predict exact eye fixations, scanpaths, and foveal attention capture with 95%+ benchmark correlation.

### Pillar 2: Psychophysics & Cognitive Load Scoring
* **Headline:** Optimize Visual Hierarchy. Eliminate Decision Fatigue.
* **Body:** Quantify scene clutter, Shannon entropy, and Michelson contrast instantly. Ensure your Call-To-Action, lead headline, and hero product capture immediate focal dominance.

### Pillar 3: SOTA Executive Intelligence
* **Headline:** Executive Scorecards Powered by Gemini 3.
* **Body:** Transform raw saliency vectors into boardroom-ready strategic insights. Receive automated design recommendations, statistical effect sizes (Cohen's d), and actionable conversion tweaks in seconds.

---

## 3. UI Microcopy & Status Strings (Figma Plugin)
* **Initial State:** *"Select a frame in Figma and click Run Neuromarketing Analysis"*
* **Processing State (Stage 01):** *"Normalizing color space & spatial contrast..."*
* **Processing State (Stage 02):** *"Computing neural scanpaths (DeepGaze III + UMSI)..."*
* **Processing State (Stage 03):** *"Evaluating cognitive load & Shannon entropy..."*
* **Completed State:** *"Analysis Complete! Saliency overlay & scorecard active."*
* **Export Action:** *"Export Executive PDF Report"*
"""

with open(os.path.join(legal_dir, "TERMS_OF_SERVICE.md"), "w", encoding="utf-8") as f:
    f.write(tos_content)

with open(os.path.join(legal_dir, "PRIVACY_POLICY.md"), "w", encoding="utf-8") as f:
    f.write(privacy_content)

with open(os.path.join(legal_dir, "COPYWRITING_SYSTEM.md"), "w", encoding="utf-8") as f:
    f.write(copywriting_content)

print("✓ Created TERMS_OF_SERVICE.md, PRIVACY_POLICY.md, and COPYWRITING_SYSTEM.md in D:\\neuromarketing-engine\\legal\\")
