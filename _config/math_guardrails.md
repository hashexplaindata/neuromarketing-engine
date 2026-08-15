# MATHEMATICAL & NEUROSCIENCE GUARDRAILS

1. SPATIAL PROBABILITY DENSITY (True Softmax):
   P(x,y) = exp(Z(x,y)) / sum_{i,j}(exp(Z(i,j)))
   Saliency maps MUST integrate to 1.0 across spatial dimensions.

2. SHUFFLED AUC (s-AUC):
   Positive distribution: Fixations on current image.
   Negative distribution: Fixations sampled from all OTHER dataset images.
   Eliminates central fixation bias artifact.

3. NORMALIZED SCANPATH SALIENCY (NSS):
   NSS = (1/N) * sum_i [ (P(x_i, y_i) - mu(P)) / sigma(P) ]
   Where Q^B is the binary ground-truth fixation map.

4. GROUND-TRUTH STANDARDIZATION (1-Degree Gaussian):
   Continuous Ground Truth G = Q^B * Gaussian2D(sigma = 1 visual degree).

5. COGNITIVE LOAD SCORE (CLS):
   CLS = ( -sum_{x,y} S(x,y) log2 S(x,y) ) + sum_{k=1}^K 1_{max(S_k) > tau}
