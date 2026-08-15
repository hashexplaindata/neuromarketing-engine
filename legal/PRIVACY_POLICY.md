# Neuromarketing Suite — Privacy Policy & Data Handling

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
