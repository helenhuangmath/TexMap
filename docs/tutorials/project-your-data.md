# Project your data

## Input format

A counts matrix CSV with **cells as rows, genes as columns**:

```csv
cell,PDCD1,TOX,TCF7,GZMB,SELL
TIL_1,12,8,0,3,0
TIL_2,1,2,9,0,7
```

## In the explorer

1. In **Project your data**, choose an **Integration method** (default scVI) and a **Query mode**.
2. Click **Choose File** and select your CSV — or click **Use demo query**.
3. Your cells appear on the map (white-ringed), and a **composition** summary lists the Tex-state
   breakdown and mean confidence.

## Query modes

| Mode | What it returns |
| --- | --- |
| **Project new query to TexAtlas** | per-cell coordinates, predicted state, confidence |
| **Integrate all datasets** | combined reference + query counts/summary |
| **Label transfer** | per-cell transferred label + confidence |
| **Find nearest Tex states** | each cell's nearest reference states |
| **Compare conditions** | query mean axes vs. the atlas (delta per axis) |

## Programmatically

```python
from texmap import TexMap
tm = TexMap.from_config("examples/tex_atlas/config.yaml")
res = tm.project({"TIL_1": {"PDCD1": 12, "TOX": 8, "TCF7": 0}})
print(res["summary"]["composition_percent"])
```

See also: [Integration methods & TexBench](integration-methods.md).
