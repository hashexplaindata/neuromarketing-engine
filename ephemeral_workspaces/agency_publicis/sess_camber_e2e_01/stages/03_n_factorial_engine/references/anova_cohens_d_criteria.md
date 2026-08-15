# ANOVA & COHEN'S D STATISTICAL CRITERIA

## N-Factorial Decomposition
- Multi-way ANOVA Model:
  `Y_ijk = mu + alpha_i (CTA) + beta_j (Headline) + gamma_k (Hero) + (alpha*beta)_ij + epsilon_ijk`
- Significance Threshold: alpha = 0.05 (p-value < 0.05)

## Effect Size Interpretation (Cohen's d)
- `|d| < 0.20`: Negligible effect
- `0.20 <= |d| < 0.50`: Small behavioral shift
- `0.50 <= |d| < 0.80`: Moderate behavioral lift
- `|d| >= 0.80`: Large attention dominance (Recommended production rollout)

## 95% Confidence Intervals
- `CI_95 = Mean +/- 1.96 * (sigma / sqrt(N))`
