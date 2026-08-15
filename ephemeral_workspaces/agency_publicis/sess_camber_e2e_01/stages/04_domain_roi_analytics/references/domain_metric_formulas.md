# DOMAIN METRIC FORMULAS & CALCULATION REFERENCE

## 1. UI/UX Domain
- **CTA Visibility Index (CVI)**:
  `CVI = ( integral_{CTA} S(x,y) dx dy / Area(CTA) ) / ( integral_{Total} S(x,y) dx dy / Area(Total) )`
  *Benchmark Target*: > 2.20
- **Cognitive Load Score (CLS)**:
  `CLS = ( -sum_{x,y} S(x,y) log2 S(x,y) ) + sum_{k=1}^K 1_{max(S_k) > tau}`
  *Benchmark Target*: < 8.50

## 2. Image Ads Domain
- **Brand Attention Capture %**:
  `Brand_Attn = ( integral_{Logo} S(x,y) dx dy / integral_{Total} S(x,y) dx dy ) * 100%`
  *Benchmark Target*: > 8.0% within 0-500ms fixation window.

## 3. Shelf & Packaging Domain
- **Shelf Standout Score (SSS)**:
  `SSS = mean(S_{Target_SKU}) / mean(S_{Competitor_Surround})`
  *Benchmark Target*: > 1.45

## 4. Content & Social Domain
- **Face-to-Text Gaze Alignment (theta)**:
  `cos(theta) = (v_{pupil} . v_{headline}) / (||v_{pupil}|| * ||v_{headline}||)`
  *Multiplier*: Boost x1.3 when theta < 15 degrees.
