"""Reliability metrics.

pass@k answers "can it"; pass^k answers "will it". Reporting the first alone
is the single most common way an agent evaluation overstates what it measured.

The pass@k and pass^k estimators are the unbiased combinatorial forms from
Yao et al. (2024), computed from n trials and c successes rather than by
re-running k times.
"""
from __future__ import annotations

import random
from math import comb


def pass_at_k(n: int, c: int, k: int) -> float:
    """P(at least one of k succeeds). Unbiased from n trials, c successes."""
    if k > n:
        raise ValueError(f"k={k} exceeds n={n}")
    if n - c < k:
        return 1.0
    return 1.0 - comb(n - c, k) / comb(n, k)


def pass_hat_k(n: int, c: int, k: int) -> float:
    """P(all k succeed). The reliability number."""
    if k > n:
        raise ValueError(f"k={k} exceeds n={n}")
    if c < k:
        return 0.0
    return comb(c, k) / comb(n, k)


def majority_at_k(answers: list, key, k: int, trials: int = 2000,
                  rng: random.Random | None = None) -> float:
    """P(the modal answer of k samples is correct). Estimated by resampling."""
    if not answers or k <= 0:
        return 0.0
    rng = rng or random.Random(20260907)
    hits = 0
    for _ in range(trials):
        draw = [rng.choice(answers) for _ in range(k)]
        counts: dict = {}
        for a in draw:
            counts[a] = counts.get(a, 0) + 1
        best = max(counts.values())
        modal = [a for a, v in counts.items() if v == best]
        if rng.choice(modal) == key:
            hits += 1
    return hits / trials


def bootstrap_ci(values: list[float], stat=None, n_boot: int = 2000, alpha: float = 0.05,
                 rng: random.Random | None = None) -> tuple[float, float]:
    """Percentile interval. Resample the CLUSTER (a task), not the rollout —
    rollouts within a task are correlated, and ignoring that understates the
    interval (Miller, 2024)."""
    if not values:
        return (float("nan"), float("nan"))
    stat = stat or (lambda xs: sum(xs) / len(xs))
    rng = rng or random.Random(20260907)
    m = len(values)
    draws = sorted(stat([values[rng.randrange(m)] for _ in range(m)]) for _ in range(n_boot))
    lo = draws[int((alpha / 2) * n_boot)]
    hi = draws[min(n_boot - 1, int((1 - alpha / 2) * n_boot))]
    return (lo, hi)


def per_task_rates(rows: list[tuple[str, bool]]) -> dict[str, float]:
    """rows: (task_id, success). Returns per-task success rate."""
    agg: dict[str, list[bool]] = {}
    for tid, ok in rows:
        agg.setdefault(tid, []).append(ok)
    return {t: sum(v) / len(v) for t, v in agg.items()}


def summarise(by_task: dict[str, list[bool]], k: int = 8, include_errors: bool = True) -> dict:
    """Every reliability number for one solver, with the denominator stated."""
    ks = [1, min(2, k), min(4, k), k]
    out = {"k": k, "errored_in_denominator": include_errors, "tasks": len(by_task)}
    at, hat = [], []
    for tid, oks in by_task.items():
        n, c = len(oks), sum(oks)
        kk = min(k, n)
        at.append(pass_at_k(n, c, kk))
        hat.append(pass_hat_k(n, c, kk))
    rates = [sum(v) / len(v) for v in by_task.values()]
    out["pass_1"] = sum(rates) / len(rates) if rates else 0.0
    out["pass_1_ci"] = bootstrap_ci(rates)
    out[f"pass_at_{k}"] = sum(at) / len(at) if at else 0.0
    out[f"pass_at_{k}_ci"] = bootstrap_ci(at)
    out[f"pass_hat_{k}"] = sum(hat) / len(hat) if hat else 0.0
    out[f"pass_hat_{k}_ci"] = bootstrap_ci(hat)
    out["curve"] = {
        str(j): {
            "pass_at": sum(pass_at_k(len(v), sum(v), min(j, len(v))) for v in by_task.values()) / len(by_task),
            "pass_hat": sum(pass_hat_k(len(v), sum(v), min(j, len(v))) for v in by_task.values()) / len(by_task),
        }
        for j in sorted(set(ks + list(range(1, k + 1))))
    }
    return out
