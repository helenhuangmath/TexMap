# TexAgent (AI agent)

TexAgent is a **tool-using agent**, not just a chatbot. With an LLM key it runs a reasoning–action
loop, calling real TexMap tools and driving the interface; without a key it falls back to a
grounded, atlas-only engine that still drives the UI.

## Connect a model

In the **TexAgent** panel open **Connect a model**, pick a provider, and paste a key:

- **Google Gemini** — has a [free tier](https://aistudio.google.com/apikey)
- **OpenAI**

Or set an environment variable before serving:

```bash
export GEMINI_API_KEY=...        # or OPENAI_API_KEY
texmap serve --config examples/tex_atlas/config.yaml
```

Force a provider with `TEXMAP_AGENT_PROVIDER=google|openai`.

## Tools the agent can call

`atlas_composition` · `axis_markers` · `regulators_of` · `projection_accuracy` ·
`clinical_benchmark` · `search_cellxgene` · `summarize_query`

It also emits UI actions — recolor by an axis or gene, open the regulatory network — and shows its
tool trace in the chat.

## Try

> *"Project the demo query, then tell me which programs drive its top state."*
>
> *"Which transcription factors regulate TOX, and color the map by TOX."*

```bash
curl -X POST http://127.0.0.1:8000/api/agent \
  -H "Content-Type: application/json" \
  -d '{"question": "which programs drive TOX?"}'
```
