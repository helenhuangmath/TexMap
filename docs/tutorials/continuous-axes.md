# Continuous exhaustion axes

TexMap's core idea: represent exhaustion as continuous, interpretable coordinates rather than
discrete cluster labels.

| Axis | Meaning | Up markers (examples) |
| --- | --- | --- |
| Exhaustion | Memory ←→ Exhaustion | PDCD1, HAVCR2, LAG3, TIGIT, TOX |
| Stemness | Differentiated ←→ Stem/progenitor | TCF7, SELL, IL7R, LEF1 |
| Terminality | Plastic ←→ Terminal | GZMB, PRF1, KLRG1, PRDM1, TBX21 |
| Cytotoxicity | Quiescent ←→ Cytotoxic | GZMB, GZMK, PRF1, GNLY, IFNG |
| Proliferation | Resting ←→ Proliferative | MKI67, TOP2A, PCNA |
| ChromatinFixation | Open ←→ Locked (ATAC-refined) | TOX, NR4A1/2/3, EGR2, DNMT3A |

Each axis is min-max scaled to 0–1 across the input. A discrete `tex_state` is also derived for
convenience.

## Score a matrix

```python
from texmap.tex_axes import score_tex_axes
axes = score_tex_axes(normalized_expression)   # cell -> {axis: 0..1, tex_state}
```

In the batch pipeline these are written to `tables/tex_axes.csv` and merged into the integrated
embedding, so the explorer can **Color by** any axis.

!!! note
    The axes are deliberately model-agnostic: the marker-program basis can be replaced by
    foundation-model latent dimensions without changing the rest of the stack.
