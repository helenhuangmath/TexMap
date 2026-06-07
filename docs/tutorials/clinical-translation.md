# Clinical translation

Ask whether a TexMap-derived predictor (e.g. the Stemness or Exhaustion axis) predicts a clinical
outcome: immunotherapy response, infection severity, CAR-T persistence, or survival.

## Metrics

| Metric | Outcome type | Implementation |
| --- | --- | --- |
| **AUROC** | binary (response) | rank-based Mann-Whitney, tie-aware |
| **Concordance index** | time-to-event | Harrell's C |
| **Hazard ratio** | time-to-event | single-covariate Cox (Newton-Raphson, Breslow ties) + Wald p |

All are implemented from first principles — no numpy / lifelines.

## In the explorer

**Benchmarks → choose a predictor → Clinical translation** runs the metrics on the bundled
cohort (`clinical_cohort.csv`).

## Programmatically / REST

```python
from texmap import TexMap
tm = TexMap.from_config("examples/tex_atlas/config.yaml")
tm.clinical_benchmark("examples/tex_atlas/clinical_cohort.csv", "Stemness")
```

```bash
curl "http://127.0.0.1:8000/api/clinical?predictor=Exhaustion"
```

On the demo cohort, **Stemness is protective** (HR < 1) and **Exhaustion is adverse** (HR > 1),
recapitulating the stem-like-predicts-response biology.

## Your own cohort

Provide a CSV with the predictor column plus any of `response` (0/1), `time`, `event`:

```python
from texmap import clinical
clinical.evaluate(rows, predictor="Exhaustion")
```
