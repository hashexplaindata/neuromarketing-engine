"""Empirical experimental analysis for Neuromarketing Studio.

The functions in this module operate on observed experimental units, such as
participants, sessions, impressions, or users. They must not be fed synthetic
saliency resamples and must not be used to turn model predictions into causal
claims. The returned metadata records whether randomization and independent
units were supplied by the caller.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations
from typing import Any, Dict, Iterable, List, Mapping, Sequence

import numpy as np
from scipy.stats import f, t, ttest_ind, ttest_rel


def _finite(values: Iterable[float]) -> np.ndarray:
    array = np.asarray(list(values), dtype=float)
    return array[np.isfinite(array)]


def _mean_ci(values: Sequence[float], bootstrap_samples: int, seed: int) -> List[float]:
    observed = _finite(values)
    if observed.size < 2:
        return [None, None]
    rng = np.random.default_rng(seed)
    boot = rng.choice(observed, size=(bootstrap_samples, observed.size), replace=True).mean(axis=1)
    return [round(float(np.percentile(boot, 2.5)), 6), round(float(np.percentile(boot, 97.5)), 6)]


def _difference_ci(control: Sequence[float], treatment: Sequence[float], bootstrap_samples: int, seed: int) -> List[float]:
    control_array = _finite(control)
    treatment_array = _finite(treatment)
    if control_array.size < 2 or treatment_array.size < 2:
        return [None, None]
    rng = np.random.default_rng(seed)
    control_boot = rng.choice(control_array, size=(bootstrap_samples, control_array.size), replace=True).mean(axis=1)
    treatment_boot = rng.choice(treatment_array, size=(bootstrap_samples, treatment_array.size), replace=True).mean(axis=1)
    difference = treatment_boot - control_boot
    return [round(float(np.percentile(difference, 2.5)), 6), round(float(np.percentile(difference, 97.5)), 6)]


def _cohens_d(control: np.ndarray, treatment: np.ndarray) -> float:
    pooled_variance = ((control.size - 1) * np.var(control, ddof=1) + (treatment.size - 1) * np.var(treatment, ddof=1)) / (control.size + treatment.size - 2)
    pooled_sd = float(np.sqrt(max(pooled_variance, 0.0)))
    return float((np.mean(treatment) - np.mean(control)) / pooled_sd) if pooled_sd > 1e-12 else 0.0


def analyze_ab(
    observations: Sequence[Mapping[str, Any]],
    outcome: str,
    variant: str,
    control: str,
    randomized: bool = False,
    unit_key: str | None = None,
    bootstrap_samples: int = 2000,
    seed: int = 42,
) -> Dict[str, Any]:
    """Analyze an independent-unit or paired A/B study using observed outcomes."""
    groups: Dict[str, List[float]] = defaultdict(list)
    for row in observations:
        try:
            groups[str(row[variant])].append(float(row[outcome]))
        except (KeyError, TypeError, ValueError):
            continue
    if control not in groups:
        raise ValueError(f"Control variant '{control}' is absent")
    treatments = [name for name in groups if name != control]
    if not treatments:
        raise ValueError("At least one treatment variant is required")

    results: Dict[str, Any] = {}
    control_values = _finite(groups[control])
    for index, treatment_name in enumerate(treatments):
        treatment_values = _finite(groups[treatment_name])
        if control_values.size < 2 or treatment_values.size < 2:
            raise ValueError("Each A/B arm requires at least two finite observations")
        test = ttest_ind(treatment_values, control_values, equal_var=False)
        results[treatment_name] = {
            "n_control": int(control_values.size),
            "n_treatment": int(treatment_values.size),
            "control_mean": round(float(np.mean(control_values)), 6),
            "treatment_mean": round(float(np.mean(treatment_values)), 6),
            "absolute_difference": round(float(np.mean(treatment_values) - np.mean(control_values)), 6),
            "relative_lift_pct": round(float((np.mean(treatment_values) / np.mean(control_values) - 1.0) * 100.0), 6) if np.mean(control_values) != 0 else None,
            "cohens_d": round(_cohens_d(control_values, treatment_values), 6),
            "confidence_interval_95": _difference_ci(control_values, treatment_values, bootstrap_samples, seed + index),
            "welch_t_statistic": round(float(test.statistic), 6),
            "p_value_uncorrected": round(float(test.pvalue), 8),
        }

    p_values = sorted((value["p_value_uncorrected"], name) for name, value in results.items())
    m = len(p_values)
    previous = 0.0
    for rank, (p_value, name) in enumerate(p_values, start=1):
        adjusted = min(1.0, max(previous, (m - rank + 1) * p_value))
        results[name]["p_value_holm"] = round(float(adjusted), 8)
        previous = adjusted

    unit_count = len({str(row.get(unit_key)) for row in observations if unit_key and row.get(unit_key) is not None}) if unit_key else None
    return {
        "analysis_type": "A/B",
        "analysis_mode": "EMPIRICAL_OBSERVED_OUTCOMES",
        "outcome": outcome,
        "variant_column": variant,
        "control_variant": control,
        "randomized": bool(randomized),
        "experimental_unit_column": unit_key,
        "n_observations": int(sum(len(values) for values in groups.values())),
        "n_experimental_units": unit_count,
        "comparisons": results,
        "interpretation_boundary": "Causal lift is only supportable when assignment, unit independence, exposure, outcome definition, and missing-data handling are documented and defensible.",
    }


def _interaction_terms(factors: Sequence[str]) -> List[tuple[str, ...]]:
    terms: List[tuple[str, ...]] = []
    for size in range(1, len(factors) + 1):
        terms.extend(combinations(factors, size))
    return terms


def _design_matrix(records: Sequence[Mapping[str, Any]], factors: Sequence[str], include_terms: Sequence[tuple[str, ...]]) -> np.ndarray:
    columns = [np.ones(len(records), dtype=float)]
    for term in include_terms:
        values = np.ones(len(records), dtype=float)
        for factor in term:
            values *= np.where(np.asarray([str(row[factor]) for row in records]) == "1", 0.5, -0.5)
        columns.append(values)
    return np.column_stack(columns)


def _ols_sse(design: np.ndarray, outcome: np.ndarray) -> tuple[float, np.ndarray, int]:
    beta, _, rank, _ = np.linalg.lstsq(design, outcome, rcond=None)
    residuals = outcome - design @ beta
    return float(np.sum(residuals**2)), beta, int(rank)


def _holm_adjust(p_values: Mapping[str, float]) -> Dict[str, float]:
    ordered = sorted(p_values.items(), key=lambda item: item[1])
    adjusted: Dict[str, float] = {}
    previous = 0.0
    m = len(ordered)
    for rank, (name, p_value) in enumerate(ordered, start=1):
        value = min(1.0, max(previous, (m - rank + 1) * p_value))
        adjusted[name] = round(float(value), 8)
        previous = value
    return adjusted


def analyze_factorial(
    observations: Sequence[Mapping[str, Any]],
    outcome: str,
    factors: Sequence[str],
    randomized: bool = False,
    unit_key: str | None = None,
    bootstrap_samples: int = 2000,
    seed: int = 42,
) -> Dict[str, Any]:
    """Analyze a balanced/two-level factorial study using observed outcomes.

    Factor levels are encoded as strings ``0`` and ``1``. The function reports
    main effects and interactions from a full factorial OLS model, Welch-style
    uncertainty is not substituted for replication, and Holm correction is
    applied across tested terms.
    """
    if len(factors) < 2:
        raise ValueError("At least two factors are required")
    records = []
    for row in observations:
        try:
            value = float(row[outcome])
            levels = [str(row[factor]) for factor in factors]
        except (KeyError, TypeError, ValueError):
            continue
        if not np.isfinite(value) or any(level not in {"0", "1"} for level in levels):
            continue
        record = dict(row)
        record[outcome] = value
        records.append(record)
    if not records:
        raise ValueError("No valid factorial observations supplied")

    cells = Counter(tuple(str(row[factor]) for factor in factors) for row in records)
    if min(cells.values()) < 2:
        raise ValueError("Every factorial cell requires at least two observed experimental units")

    terms = _interaction_terms(factors)
    full_design = _design_matrix(records, factors, terms)
    y = np.asarray([row[outcome] for row in records], dtype=float)
    full_sse, beta, full_rank = _ols_sse(full_design, y)
    residual_df = len(records) - full_rank
    if residual_df <= 0 or full_sse <= 1e-12:
        raise ValueError("Factorial model has no residual degrees of freedom or zero residual variance")

    term_results: Dict[str, Any] = {}
    p_values: Dict[str, float] = {}
    for index, term in enumerate(terms, start=1):
        reduced_terms = [candidate for candidate in terms if candidate != term]
        reduced_design = _design_matrix(records, factors, reduced_terms)
        reduced_sse, _, reduced_rank = _ols_sse(reduced_design, y)
        df_term = full_rank - reduced_rank
        numerator = max(0.0, (reduced_sse - full_sse) / max(df_term, 1))
        denominator = full_sse / residual_df
        f_statistic = numerator / denominator if denominator > 0 else 0.0
        p_value = float(f.sf(f_statistic, max(df_term, 1), residual_df))
        ss_term = max(0.0, reduced_sse - full_sse)
        partial_eta = ss_term / (ss_term + full_sse) if ss_term + full_sse > 0 else 0.0
        term_name = ":".join(term)
        p_values[term_name] = p_value
        term_results[term_name] = {
            "estimate": round(float(beta[index]), 6),
            "f_statistic": round(float(f_statistic), 6),
            "p_value_uncorrected": round(p_value, 8),
            "partial_eta_squared": round(float(partial_eta), 6),
            "df_term": int(df_term),
        }

    for name, adjusted in _holm_adjust(p_values).items():
        term_results[name]["p_value_holm"] = adjusted

    unit_count = len({str(row.get(unit_key)) for row in records if unit_key and row.get(unit_key) is not None}) if unit_key else None
    return {
        "analysis_type": "FULL_FACTORIAL_ANOVA",
        "analysis_mode": "EMPIRICAL_OBSERVED_OUTCOMES",
        "outcome": outcome,
        "factors": list(factors),
        "factor_levels": {factor: ["0", "1"] for factor in factors},
        "randomized": bool(randomized),
        "experimental_unit_column": unit_key,
        "n_observations": len(records),
        "n_experimental_units": unit_count,
        "cell_counts": {"|".join(cell): count for cell, count in cells.items()},
        "residual_degrees_of_freedom": int(residual_df),
        "terms": term_results,
        "interpretation_boundary": "ANOVA describes observed outcome differences under the supplied design. Causal interpretation requires defensible randomization or a justified observational design and independent experimental units.",
    }
