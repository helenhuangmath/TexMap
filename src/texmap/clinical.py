"""Clinical translation benchmark (note.txt: clinical translation).

Evaluates how well a TexMap-derived predictor (e.g. the per-sample Exhaustion or
Terminality axis score) predicts clinical outcomes:

  * Immunotherapy (ICB) response     -> binary  -> AUROC
  * Chronic infection severity        -> binary/ordinal -> AUROC
  * CAR-T persistence                 -> binary  -> AUROC
  * Survival / progression            -> time-to-event -> concordance index + hazard ratio

All three metrics are implemented from scratch (no numpy/lifelines) so the package stays
dependency-free:

  * AUROC               — rank-based (Mann-Whitney U), handles ties.
  * Concordance index   — Harrell's C over comparable, uncensored-aware pairs.
  * Hazard ratio        — exp(beta) from a single-covariate Cox partial-likelihood fit
                          (Newton-Raphson, Breslow ties), with a Wald p-value.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence


# --------------------------------------------------------------------------- AUROC

def auroc(scores: Sequence[float], labels: Sequence[int]) -> Optional[float]:
    """Area under the ROC curve via the Mann-Whitney U statistic (tie-aware)."""
    pos = [s for s, y in zip(scores, labels) if y == 1]
    neg = [s for s, y in zip(scores, labels) if y == 0]
    if not pos or not neg:
        return None
    # rank all scores (average ranks for ties)
    paired = sorted(zip(scores, range(len(scores))), key=lambda t: t[0])
    ranks = [0.0] * len(scores)
    i = 0
    while i < len(paired):
        j = i
        while j + 1 < len(paired) and paired[j + 1][0] == paired[i][0]:
            j += 1
        avg = (i + j) / 2.0 + 1.0  # 1-based average rank
        for k in range(i, j + 1):
            ranks[paired[k][1]] = avg
        i = j + 1
    rank_pos = sum(ranks[idx] for idx, y in enumerate(labels) if y == 1)
    n_pos, n_neg = len(pos), len(neg)
    u = rank_pos - n_pos * (n_pos + 1) / 2.0
    return u / (n_pos * n_neg)


# --------------------------------------------------------------- concordance index

def concordance_index(scores: Sequence[float], times: Sequence[float],
                      events: Sequence[int]) -> Optional[float]:
    """Harrell's C: fraction of comparable pairs whose risk order matches outcome order.

    `scores` are risk scores (higher = higher risk / earlier event expected).
    """
    n = len(times)
    concordant = permissible = 0.0
    for i in range(n):
        for j in range(n):
            if times[i] >= times[j]:
                continue
            # i fails before j; comparable only if i had an event
            if not events[i]:
                continue
            permissible += 1
            if scores[i] > scores[j]:
                concordant += 1
            elif scores[i] == scores[j]:
                concordant += 0.5
    if permissible == 0:
        return None
    return concordant / permissible


# ----------------------------------------------------------------- Cox hazard ratio

def cox_hazard_ratio(x: Sequence[float], times: Sequence[float], events: Sequence[int],
                     iters: int = 50, tol: float = 1e-8) -> dict:
    """Single-covariate Cox proportional-hazards fit (Breslow ties) via Newton-Raphson.

    Returns {beta, hazard_ratio, se, z, p, n_events}. hazard_ratio = exp(beta) is the
    multiplicative change in hazard per one-unit increase in x.
    """
    order = sorted(range(len(times)), key=lambda i: times[i])
    xs = [x[i] for i in order]
    ts = [times[i] for i in order]
    ev = [events[i] for i in order]
    n = len(xs)
    n_events = sum(ev)
    if n_events == 0:
        return {"beta": None, "hazard_ratio": None, "se": None, "z": None, "p": None, "n_events": 0}

    beta = 0.0
    for _ in range(iters):
        grad = 0.0
        hess = 0.0
        # risk set accumulators computed by iterating; for each event, risk set = those with time >= t_i
        for i in range(n):
            if not ev[i]:
                continue
            # risk set: all j with ts[j] >= ts[i]
            s0 = s1 = s2 = 0.0
            ti = ts[i]
            for j in range(n):
                if ts[j] >= ti:
                    w = math.exp(beta * xs[j])
                    s0 += w
                    s1 += w * xs[j]
                    s2 += w * xs[j] * xs[j]
            mean = s1 / s0
            grad += xs[i] - mean
            hess += (s2 / s0) - mean * mean
        if hess <= 0:
            break
        step = grad / hess
        beta += step
        if abs(step) < tol:
            break

    # complete/monotone separation: the partial-likelihood MLE diverges (|beta| -> inf).
    if abs(beta) >= 15:
        return {"beta": None, "hazard_ratio": None, "se": None, "z": None, "p": None,
                "n_events": n_events, "separation": True,
                "note": "covariate perfectly separates outcomes; hazard ratio is unbounded"}

    se = math.sqrt(1.0 / hess) if hess > 0 else float("nan")
    z = beta / se if se and not math.isnan(se) else float("nan")
    p = _normal_two_sided_p(z) if not math.isnan(z) else None
    return {
        "beta": round(beta, 4),
        "hazard_ratio": round(math.exp(beta), 4),
        "se": round(se, 4) if not math.isnan(se) else None,
        "z": round(z, 4) if not math.isnan(z) else None,
        "p": p,
        "n_events": n_events,
        "separation": False,
    }


def _normal_two_sided_p(z: float) -> float:
    # two-sided p-value from standard normal via erf
    return round(2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(z) / math.sqrt(2.0)))), 5)


# --------------------------------------------------------------------------- driver

def evaluate(samples: List[dict], predictor: str,
             response_col: str = "response",
             time_col: str = "time", event_col: str = "event") -> dict:
    """Run the available clinical metrics for one predictor over a cohort table.

    Each sample dict carries the `predictor` value and any of: `response` (0/1),
    `time` + `event` (survival). Missing outcome columns are skipped.
    """
    scores = [_f(s.get(predictor)) for s in samples]
    out: Dict[str, object] = {"predictor": predictor, "n_samples": len(samples)}

    if all(response_col in s and s[response_col] != "" for s in samples):
        labels = [int(float(s[response_col])) for s in samples]
        out["auroc"] = _round(auroc(scores, labels))
        out["n_responders"] = sum(labels)

    has_surv = all(time_col in s and event_col in s and s[time_col] != "" for s in samples)
    if has_surv:
        times = [_f(s[time_col]) for s in samples]
        events = [int(float(s[event_col])) for s in samples]
        out["concordance_index"] = _round(concordance_index(scores, times, events))
        out["cox"] = cox_hazard_ratio(scores, times, events)
    return out


def _f(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _round(v):
    return round(v, 4) if isinstance(v, float) else v
