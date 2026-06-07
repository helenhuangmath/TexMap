"""Cell-state projection accuracy (note.txt: projection benchmarking).

Two evaluations:

  * ``accuracy_report`` — given (expected, predicted) label pairs (e.g. an annotated query
    with `expected_label`), compute overall accuracy, per-class precision/recall/F1,
    macro-F1, and a confusion matrix.

  * ``crossval_atlas`` — leave-one-out kNN label transfer *within* the reference atlas in
    Tex-axis space: hide each cell's label, predict it from its neighbours, and measure how
    well the projection recovers known cell states. This is the headline
    "cell-state projection accuracy" number for the atlas.
"""
from __future__ import annotations

import math
from typing import Dict, List, Sequence, Tuple

from texmap.tex_axes import axis_names


def accuracy_report(pairs: Sequence[Tuple[str, str]]) -> dict:
    """pairs: list of (expected_label, predicted_label)."""
    pairs = [(str(a), str(b)) for a, b in pairs if a != "" and a is not None]
    n = len(pairs)
    if n == 0:
        return {"n": 0, "accuracy": None}
    labels = sorted({a for a, _ in pairs} | {b for _, b in pairs})
    correct = sum(1 for a, b in pairs if a == b)
    confusion = {a: {b: 0 for b in labels} for a in labels}
    for a, b in pairs:
        confusion[a][b] += 1

    per_class = {}
    f1s = []
    for lab in labels:
        tp = sum(1 for a, b in pairs if a == lab and b == lab)
        fp = sum(1 for a, b in pairs if a != lab and b == lab)
        fn = sum(1 for a, b in pairs if a == lab and b != lab)
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        support = sum(1 for a, _ in pairs if a == lab)
        if support:
            per_class[lab] = {"precision": round(prec, 3), "recall": round(rec, 3),
                              "f1": round(f1, 3), "support": support}
            f1s.append(f1)
    return {
        "n": n,
        "accuracy": round(correct / n, 4),
        "macro_f1": round(sum(f1s) / len(f1s), 4) if f1s else None,
        "per_class": per_class,
        "labels": labels,
        "confusion": confusion,
    }


def crossval_atlas(atlas, k: int = 15) -> dict:
    """Leave-one-out kNN label transfer in axis space → projection accuracy on the atlas."""
    names = axis_names()
    cells = atlas.cells
    vecs = {c: [atlas.axes.get(c, {}).get(a, 0.0) for a in names] for c in cells}
    pairs: List[Tuple[str, str]] = []
    for c in cells:
        vc = vecs[c]
        dists = []
        for o in cells:
            if o == c:
                continue
            vo = vecs[o]
            d = sum((vc[i] - vo[i]) ** 2 for i in range(len(names)))
            dists.append((d, o))
        dists.sort(key=lambda t: t[0])
        votes: Dict[str, float] = {}
        for d, o in dists[:k]:
            w = 1.0 / (1.0 + math.sqrt(d))
            lab = atlas.labels[o]
            votes[lab] = votes.get(lab, 0.0) + w
        pred = max(votes, key=votes.get) if votes else ""
        pairs.append((atlas.labels[c], pred))
    report = accuracy_report(pairs)
    report["method"] = f"leave-one-out kNN (k={k}) label transfer in {len(names)}-D Tex-axis space"
    return report
