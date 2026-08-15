# REPORT DESIGN SYSTEM & WEASYPRINT TOKENS

## Typography
- Primary Sans: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif
- Display / Headings: "Outfit", "Inter", sans-serif
- Monospace / Metrics: "JetBrains Mono", "Fira Code", monospace

## Color Tokens
- Canvas Background: `#0B0F17` (Dark Mode Luxury) / `#FFFFFF` (Print Mode)
- Surface Card: `#131B2A` / `#F8FAFC`
- Primary Accent: `#38BDF8` (Electric Cyan)
- Secondary Accent: `#818CF8` (Indigo Glow)
- Attention Heatmap Scale: Jet / Turbo (Blue -> Green -> Yellow -> Red)
- High Confidence: `#10B981` (Emerald)
- Warning / Epistemic Uncertainty: `#F59E0B` (Amber)
- Critical Risk: `#EF4444` (Rose Red)

## Layout & Page Grid
- PDF Target: A4 Landscape / Portrait (210mm x 297mm)
- Margins: 15mm top/bottom, 20mm left/right
- Page Breaks: `page-break-inside: avoid;` on metric cards and score tables.
