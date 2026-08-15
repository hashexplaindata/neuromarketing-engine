#!/usr/bin/env python3
"""
SOTA Neuromarketing Thermal Heatmap & Focus Map Renderer (Neurons.ai Grade)
Applies:
1. 2-Degree Foveal Gaussian Spatial Filtering (Simulating human visual cortex pooling)
2. Contrast Gamma Shaping & Dynamic Noise Floor Cutoff
3. Professional Turbo/Jet Infrared Colormap with Smooth Alpha Gradient
4. Focus / Fog Map Generator (Illuminates only conscious foveal fixations)
"""

import os
import sys
import numpy as np
from PIL import Image, ImageFilter
from scipy.ndimage import gaussian_filter

def render_sota_heatmap(
    orig_image_path: str,
    raw_saliency_density: np.ndarray,
    output_heatmap_path: str,
    output_focus_map_path: str = None,
    foveal_sigma: float = 24.0,
    noise_cutoff_pct: float = 40.0,
    gamma: float = 1.6
):
    orig = Image.open(orig_image_path).convert("RGBA")
    w, h = orig.size

    # 1. Resize raw density to original canvas resolution
    sal_img = Image.fromarray(raw_saliency_density.astype(np.float32)).resize((w, h), Image.Resampling.BICUBIC)
    density = np.array(sal_img, dtype=np.float32)

    # 2. Apply Foveal Gaussian Smoothing (Human Eye Fixation Spread)
    smoothed = gaussian_filter(density, sigma=foveal_sigma)

    # 3. Dynamic Noise Floor Cutoff (Eliminate background green haze)
    p_cutoff = np.percentile(smoothed, noise_cutoff_pct)
    clipped = np.maximum(0, smoothed - p_cutoff)
    
    # 4. Non-Linear Contrast Normalization (Gamma curve to pop focal hotspots)
    max_val = np.max(clipped) + 1e-12
    normalized = np.power(clipped / max_val, gamma)

    # 5. Turbo / Jet Professional Infrared Colormap
    # Normalized [0, 1] -> Color (R, G, B) + Alpha
    r = np.clip(1.5 * normalized - 0.2, 0.0, 1.0)
    g = np.clip(1.0 - 2.0 * np.abs(normalized - 0.5), 0.0, 1.0)
    b = np.clip(1.5 - 2.0 * normalized, 0.0, 1.0)
    
    # Quadratic Alpha ramp: 0% at background, up to 75% at peak hot spots
    alpha = np.power(normalized, 1.3) * 0.78 * 255.0

    # Ensure background below cutoff is 100% transparent
    alpha[normalized < 0.04] = 0.0

    rgb_array = np.stack([r * 255, g * 255, b * 255, alpha], axis=-1).astype(np.uint8)
    heatmap_overlay = Image.fromarray(rgb_array, mode="RGBA")

    # Composite Heatmap over original
    blended_heatmap = Image.alpha_composite(orig, heatmap_overlay)
    blended_heatmap.convert("RGB").save(output_heatmap_path, quality=95)

    # 6. Generate Neurons.ai-Grade Fog / Focus Map
    if output_focus_map_path:
        # Darken background by 75%
        dark_base = Image.fromarray((np.array(orig)[:, :, :3] * 0.22).astype(np.uint8))
        dark_base = dark_base.convert("RGBA")
        
        # Spotlight mask from normalized saliency
        mask_alpha = np.clip(normalized * 2.2, 0.0, 1.0) * 255.0
        mask_img = Image.fromarray(mask_alpha.astype(np.uint8), mode="L")
        
        focus_map = Image.composite(orig, dark_base, mask_img)
        focus_map.convert("RGB").save(output_focus_map_path, quality=95)

    return output_heatmap_path, output_focus_map_path

if __name__ == "__main__":
    import json
    demo_dir = r"D:\neuromarketing-engine\output\demo_analysis"
    img_path = os.path.join(demo_dir, "sample_marketing_ad.png")
    
    # Generate high-contrast focal saliency distribution across key visual elements
    w, h = 800, 800
    canvas_density = np.zeros((h, w), dtype=np.float32)
    
    # Focal Hotspot 1: Headline Typography (Top)
    canvas_density[160:200, 120:680] += 0.85
    # Focal Hotspot 2: Hero Product Center (Center)
    y, x = np.ogrid[:h, :w]
    dist_from_center = np.sqrt((x - 400)**2 + (y - 420)**2)
    canvas_density[dist_from_center < 140] += 1.25
    # Focal Hotspot 3: CTA Button (Bottom)
    canvas_density[650:710, 280:520] += 1.10
    # Focal Hotspot 4: Brand Logo
    canvas_density[45:85, 55:195] += 0.70

    heatmap_file = os.path.join(demo_dir, "neurons_grade_heatmap.png")
    focus_file = os.path.join(demo_dir, "neurons_grade_focus_map.png")
    
    render_sota_heatmap(
        orig_image_path=img_path,
        raw_saliency_density=canvas_density,
        output_heatmap_path=heatmap_file,
        output_focus_map_path=focus_file,
        foveal_sigma=26.0,
        noise_cutoff_pct=35.0,
        gamma=1.5
    )
    print("✓ Successfully generated Neurons.ai grade Heatmap and Focus Map!")
