#!/usr/bin/env python3
"""
N-Factorial Permutation Compositor
ICM Neuromarketing Pipeline - Stage 03 Combinatorial Matrix Engine
"""

import os
import sys
import json
import argparse
import itertools
import numpy as np

def generate_permutations(bboxes_path: str, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    
    # Define Factorial Design Variables
    factors = {
        "CTA_Position": ["Bottom_Center", "Bottom_Right", "Sticky_Footer"],
        "Headline_Emphasis": ["High_Contrast_Light", "Electric_Cyan", "Bold_Dark"],
        "Hero_Composition": ["Centered_Hero", "Left_Aligned_Face_Gaze"]
    }
    
    factor_names = list(factors.keys())
    combinations = list(itertools.product(*factors.values()))
    
    permutations_manifest = {
        "total_variants": len(combinations),
        "factorial_factors": factors,
        "variants": []
    }
    
    # Generate variant densities
    densities = []
    for idx, combo in enumerate(combinations):
        variant_id = f"VAR_{idx+1:02d}"
        var_dict = dict(zip(factor_names, combo))
        
        # Simulate variant attention density
        h, w = 1024, 1024
        y, x = np.ogrid[:h, :w]
        
        # Base headline weight
        head_boost = 1.35 if "Electric_Cyan" in combo else 1.10
        # CTA weight
        cta_x = 0.75 if "Bottom_Right" in combo else 0.50
        cta_boost = 1.45 if "Bottom_Right" in combo else 1.25
        # Hero weight
        hero_x = 0.35 if "Left_Aligned_Face_Gaze" in combo else 0.50
        hero_boost = 1.30 if "Left_Aligned_Face_Gaze" in combo else 1.15
        
        logits = (
            head_boost * 2.8 * np.exp(-((x - 0.5*w)**2 + (y - 0.22*h)**2)/(2.0*(0.12*w)**2)) +
            hero_boost * 3.1 * np.exp(-((x - hero_x*w)**2 + (y - 0.50*h)**2)/(2.0*(0.18*w)**2)) +
            cta_boost * 3.3 * np.exp(-((x - cta_x*w)**2 + (y - 0.80*h)**2)/(2.0*(0.10*w)**2))
        )
        
        # True Softmax
        shifted = logits - np.max(logits)
        exp_m = np.exp(shifted)
        density = exp_m / (np.sum(exp_m) + 1e-12)
        densities.append(density.astype(np.float16))
        
        permutations_manifest["variants"].append({
            "variant_id": variant_id,
            "configuration": var_dict,
            "estimated_kpi_weight": round(float(head_boost * cta_boost * hero_boost), 3)
        })
        
    perm_file = os.path.join(out_dir, "permutations_manifest.json")
    with open(perm_file, "w", encoding="utf-8") as f:
        json.dump(permutations_manifest, f, indent=2)
        
    npy_file = os.path.join(out_dir, "variant_densities.npy")
    np.save(npy_file, np.array(densities, dtype=np.float16))
    
    print(f"[Stage 03 Compositor] Generated {len(combinations)} factorial combinations.")
    print(f"[Stage 03 Compositor] Manifest written to: {perm_file}")
    print(f"[Stage 03 Compositor] Densities written to: {npy_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 03 N-Factorial Combinatorial Compositor")
    parser.add_argument("--bboxes", required=True, help="Path to detected_bboxes.json")
    parser.add_argument("--out", required=True, help="Output directory for permutations")
    args = parser.parse_args()
    generate_permutations(args.bboxes, args.out)
