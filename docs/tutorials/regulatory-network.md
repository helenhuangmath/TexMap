# Regulatory networks

TexMap recovers a transcription-factor → target regulatory network from reference co-expression
(a GENIE3/SCENIC-style approach), signs each edge (activation / repression), and groups edges
into exhaustion programs by axis — a STRING-style interactive view.

![Regulatory network](../figures/screenshot_regulatory_network.png)

## In the explorer

Open **Regulatory network → Show network graph**. Nodes are colored by program; TFs are larger
and labeled; blue edges are activating, red repressive (width ∝ |correlation|). Use the
**gene focus** box to isolate one gene's regulators and targets, and **Export** to download the
network as JSON or the graph as PNG.

## Programmatically / REST

```python
from texmap import TexMap
tm = TexMap.from_config("examples/tex_atlas/config.yaml")
net = tm.regulatory_network()       # {nodes, edges, programs, ...}
tm.regulators_of("TOX")             # regulators + targets of TOX
```

```bash
curl "http://127.0.0.1:8000/api/regulatory?gene=TOX"
```

On the demo atlas this recovers, e.g., **TOX → PDCD1 / LAG3 / TIGIT / ENTPD1** (the
inhibitory-receptor program) and **TBX21 ⊣ TOX**.

!!! note
    Edges are co-expression based. Link them to ATAC accessibility and TF motifs (the
    [multiomic tutorial](multiomic-crossspecies.md)) to move from association toward
    gene→enhancer→TF mechanism.
