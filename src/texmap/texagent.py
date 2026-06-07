"""TexAgent — the natural-language interface (note.txt "AI Agent Layer").

Answers questions like:
  * "Show me genes associated with terminal exhaustion."
  * "Which programs drive TOX expression?"
  * "Summarize my uploaded dataset."

TexAgent is **provider-agnostic** and works in real time with whichever LLM API key you
provide — set ONE of these environment variables before `texmap serve`:

  * GEMINI_API_KEY  (or GOOGLE_API_KEY)  -> Google Gemini   (has a free tier: aistudio.google.com/apikey)
  * OPENAI_API_KEY                       -> OpenAI ChatGPT
Force a specific one with TEXMAP_AGENT_PROVIDER = google | openai.
With no key set, TexAgent uses a grounded offline rule-based engine. Every answer is
grounded on real atlas facts that are passed to the model as context.

All calls use the Python standard library (urllib) so there are no extra dependencies.
"""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Dict, List, Optional

from texmap.tex_axes import TEX_AXES, axis_names

# Default models per provider (override with TEXMAP_AGENT_MODEL).
PROVIDER_MODELS = {
    "google": "gemini-2.0-flash",
    "openai": "gpt-4o-mini",
}


def _detect_provider() -> Optional[str]:
    forced = (os.environ.get("TEXMAP_AGENT_PROVIDER") or "").strip().lower()
    have = {
        "google": bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")),
        "openai": bool(os.environ.get("OPENAI_API_KEY")),
    }
    if forced in PROVIDER_MODELS and have.get(forced):
        return forced
    # free-first preference order
    for p in ("google", "openai"):
        if have[p]:
            return p
    return None


def _model_for(provider: str) -> str:
    return os.environ.get("TEXMAP_AGENT_MODEL") or PROVIDER_MODELS[provider]


def backend_name() -> str:
    provider = _detect_provider()
    if provider:
        return f"{provider} ({_model_for(provider)})"
    return "offline (rule-based, grounded on atlas)"


def answer(question, atlas, gene_sets, meta_by_cell, last_projection, network=None,
           accuracy_fn=None, clinical_rows=None) -> dict:
    question = (question or "").strip()
    if not question:
        return {"answer": "Ask me about exhaustion markers, programs driving a gene, or your uploaded data.",
                "backend": backend_name(), "data": {}, "actions": []}

    facts = _gather_facts(question, atlas, gene_sets, meta_by_cell, last_projection, network)
    provider = _detect_provider()

    if provider:
        ctx = {"atlas": atlas, "gene_sets": gene_sets, "meta_by_cell": meta_by_cell,
               "last_projection": last_projection, "network": network,
               "accuracy_fn": accuracy_fn, "clinical_rows": clinical_rows}
        try:
            result = run_agent(question, ctx)        # real tool-using agent loop
            result["data"] = facts
            return result
        except Exception as exc:  # graceful fallback on any network/API error
            fallback = _rule_based_answer(question, facts)
            fallback["answer"] += f"\n\n(Live {provider} agent call failed: {exc}; answered from the atlas directly.)"
            return fallback

    # offline: grounded single-step + synthesized UI actions
    res = _rule_based_answer(question, facts)
    res["actions"] = _offline_actions(facts)
    return res


def _offline_actions(facts) -> list:
    if facts.get("gene"):
        return [{"type": "color_by_gene", "gene": facts["gene"]}]
    if facts.get("matched_axis"):
        return [{"type": "color_by", "field": facts["matched_axis"]}]
    return []


# --------------------------------------------------------------------------- LLM calls

SYSTEM_PROMPT = (
    "You are TexAgent, an assistant for the TexMap CD8 T-cell exhaustion atlas. "
    "Answer ONLY from the grounding facts provided as JSON. If the facts do not contain "
    "the answer, say so and suggest how the user could find it in TexMap. Be concise, use "
    "immunology terminology correctly, and never invent gene names or numbers not in the facts."
)


def _user_prompt(question: str, facts: dict) -> str:
    return f"Grounding facts (JSON):\n{json.dumps(facts, indent=2)}\n\nUser question: {question}"


def _http_json(url: str, payload: dict, headers: dict, timeout: float = 30.0) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **headers},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _call_llm(provider: str, user: str, system: str = SYSTEM_PROMPT) -> str:
    model = _model_for(provider)
    if provider == "google":
        return _call_google(model, user, system)
    if provider == "openai":
        return _call_openai(model, user, system)
    raise ValueError(f"unsupported provider: {provider}")


def _call_google(model: str, user: str, system: str) -> str:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.2},
    }
    data = _http_json(url, payload, {})
    return "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"]).strip()


def _call_openai(model: str, user: str, system: str) -> str:
    key = os.environ["OPENAI_API_KEY"]
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "max_tokens": 1024, "temperature": 0.2,
    }
    data = _http_json("https://api.openai.com/v1/chat/completions", payload,
                      {"Authorization": f"Bearer {key}"})
    return data["choices"][0]["message"]["content"].strip()


# --------------------------------------------------------------------------- tool-using agent

AGENT_SYSTEM = (
    "You are TexAgent, a TOOL-USING agent for the TexMap CD8 T-cell exhaustion atlas. "
    "You can call tools to inspect REAL atlas data and emit UI actions to drive the explorer. "
    "At each step reply with EXACTLY ONE JSON object and nothing else.\n"
    "To call a tool: {\"thought\": \"...\", \"tool\": \"NAME\", \"args\": {...}}\n"
    "When finished: {\"thought\": \"...\", \"final\": \"answer for the user\", \"actions\": [ ... ]}\n\n"
    "TOOLS:\n"
    "- atlas_composition() -> cell counts per state\n"
    "- axis_markers(axis) -> marker genes for an axis (Exhaustion, Stemness, Terminality, Cytotoxicity, Proliferation, ChromatinFixation)\n"
    "- regulators_of(gene) -> recovered TF regulators and targets of a gene\n"
    "- projection_accuracy() -> leave-one-out cell-state accuracy\n"
    "- clinical_benchmark(predictor) -> AUROC / concordance index / hazard ratio for a Tex axis\n"
    "- search_cellxgene(query) -> public CELLxGENE datasets matching a query\n"
    "- summarize_query() -> composition of the user's last uploaded/projected dataset\n\n"
    "UI ACTIONS (put in 'actions'): {\"type\":\"color_by\",\"field\":\"<axis or metadata>\"}, "
    "{\"type\":\"color_by_gene\",\"gene\":\"<GENE>\"}, {\"type\":\"open_network\"}.\n"
    "Ground every claim in tool results. Keep final answers concise."
)


def _parse_step(raw: str):
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):] if "{" in text else text
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


def _execute_tool(name, args, ctx):
    """Return (observation, ui_action_or_None). Operates on REAL atlas data."""
    from texmap import cellxgene, clinical, regulatory
    a = args or {}
    if name == "atlas_composition":
        comp = {}
        for c in ctx["atlas"].cells:
            lab = ctx["atlas"].labels.get(c, "?")
            comp[lab] = comp.get(lab, 0) + 1
        return comp, None
    if name == "axis_markers":
        axis = a.get("axis", "")
        if axis in TEX_AXES:
            return TEX_AXES[axis], {"type": "color_by", "field": axis}
        return {"error": f"unknown axis {axis}"}, None
    if name == "regulators_of":
        gene = (a.get("gene") or "").upper()
        net = ctx.get("network") or {}
        if not net.get("edges"):
            return {"error": "no regulatory network"}, None
        sub = regulatory.focus(net, gene)
        return {"regulators": sub["regulators"][:6], "targets": sub["targets"][:6]}, \
               {"type": "color_by_gene", "gene": gene}
    if name == "projection_accuracy":
        fn = ctx.get("accuracy_fn")
        return (fn() if fn else {"error": "unavailable"}), None
    if name == "clinical_benchmark":
        rows = ctx.get("clinical_rows") or []
        if not rows:
            return {"error": "no clinical cohort"}, None
        return clinical.evaluate(rows, a.get("predictor", "Exhaustion")), None
    if name == "search_cellxgene":
        res = cellxgene.search_datasets(a.get("query", ""))
        return {"source": res["source"],
                "results": [{"title": r["title"], "organism": r["organism"]} for r in res["results"][:5]]}, None
    if name == "summarize_query":
        lp = ctx.get("last_projection")
        return (lp.get("summary") if lp else {"error": "no dataset projected yet"}), None
    if name in ("color_by", "color_by_gene", "open_network"):
        return {"ok": True}, {"type": name, **a}
    return {"error": f"unknown tool {name}"}, None


def run_agent(question, ctx, max_steps: int = 5) -> dict:
    provider = _detect_provider()
    scratch, trace, actions = [], [], []
    for _ in range(max_steps):
        prompt = (f"User question: {question}\n\nScratchpad (your prior tool calls and results):\n"
                  + ("\n".join(scratch) if scratch else "(empty)")
                  + "\n\nReply with the next single JSON step.")
        raw = _call_llm(provider, prompt, system=AGENT_SYSTEM)
        step = _parse_step(raw)
        if step is None:
            return {"answer": raw.strip(), "actions": actions, "trace": trace, "backend": backend_name()}
        if "final" in step:
            actions += step.get("actions", []) or []
            return {"answer": step["final"], "actions": actions, "trace": trace, "backend": backend_name()}
        tool = step.get("tool")
        obs, action = _execute_tool(tool, step.get("args", {}), ctx)
        if action:
            actions.append(action)
        trace.append({"tool": tool, "args": step.get("args", {})})
        scratch.append(f"CALL {tool}({json.dumps(step.get('args', {}))}) -> {json.dumps(obs)[:700]}")
    return {"answer": "Reached the step limit. " + (scratch[-1] if scratch else ""),
            "actions": actions, "trace": trace, "backend": backend_name()}


# --------------------------------------------------------------------------- facts

def _gather_facts(question, atlas, gene_sets, meta_by_cell, last_projection, network=None) -> dict:
    q = question.lower()
    facts: Dict[str, object] = {
        "n_reference_cells": len(atlas.cells),
        "axes": axis_names(),
        "pathways": list(gene_sets.keys()),
    }

    comp: Dict[str, int] = {}
    for cell in atlas.cells:
        comp[atlas.labels.get(cell, "?")] = comp.get(atlas.labels.get(cell, "?"), 0) + 1
    facts["atlas_composition"] = dict(sorted(comp.items(), key=lambda t: -t[1]))

    matched_axis = _match_axis(q)
    if matched_axis:
        facts["matched_axis"] = matched_axis
        facts["axis_markers"] = TEX_AXES[matched_axis]

    gene = _match_gene(question, gene_sets)
    if gene:
        facts["gene"] = gene
        facts["gene_in_pathways"] = [p for p, gs in gene_sets.items()
                                     if gene.upper() in {g.upper() for g in gs}]
        facts["gene_in_axes"] = [
            a for a, prog in TEX_AXES.items()
            if gene.upper() in {g.upper() for d in prog.values() for g in d}
        ]
        if network and network.get("edges"):
            from texmap.regulatory import focus
            sub = focus(network, gene)
            facts["inferred_regulators"] = [
                {"tf": e["source"], "r": e["r"], "sign": e["sign"]} for e in sub["regulators"][:6]
            ]
            facts["inferred_targets"] = [
                {"target": e["target"], "r": e["r"], "sign": e["sign"]} for e in sub["targets"][:6]
            ]

    if last_projection:
        facts["projection_summary"] = last_projection.get("summary", {})
        facts["projection_n_cells"] = last_projection.get("n_cells", 0)

    return facts


def _match_axis(q: str) -> Optional[str]:
    synonyms = {
        "Exhaustion": ["exhaust", "exhausted", "tex", "dysfunction"],
        "Stemness": ["stem", "progenitor", "tpex", "memory-like", "stemness"],
        "Terminality": ["terminal", "terminality", "end-stage"],
        "Cytotoxicity": ["cytotox", "killing", "effector", "cytotoxic"],
        "Proliferation": ["prolifer", "cycling", "dividing"],
        "ChromatinFixation": ["chromatin", "epigenet", "fixation", "locked", "fixed"],
    }
    for axis, words in synonyms.items():
        if any(w in q for w in words):
            return axis
    return None


def _match_gene(question: str, gene_sets) -> Optional[str]:
    import re

    known = {g.upper() for gs in gene_sets.values() for g in gs}
    known |= {g.upper() for prog in TEX_AXES.values() for d in prog.values() for g in d}
    for token in re.split(r"[^A-Za-z0-9]+", question):
        if token and token.upper() in known:
            return token.upper()
    return None


# --------------------------------------------------------------------------- offline

def _rule_based_answer(question, facts) -> dict:
    parts: List[str] = []
    data: Dict[str, object] = {}

    if "gene" in facts:
        gene = facts["gene"]
        axes = facts.get("gene_in_axes", [])
        paths = facts.get("gene_in_pathways", [])
        parts.append(f"**{gene}** participates in the exhaustion axes: "
                     f"{', '.join(axes) or 'none directly'}.")
        if paths:
            parts.append(f"It is a member of these regulatory programs / pathways: {', '.join(paths)}.")
        regs = facts.get("inferred_regulators", [])
        tgts = facts.get("inferred_targets", [])
        if regs:
            parts.append("Recovered regulatory network — top inferred regulators (TF, co-expression r): "
                         + ", ".join(f"{r['tf']} ({r['r']:+}, {r['sign']})" for r in regs) + ".")
        if tgts:
            parts.append(f"{gene} co-regulates: " +
                         ", ".join(f"{t['target']} ({t['r']:+})" for t in tgts) + ".")
        parts.append("Link these edges to accessible enhancers / TF occupancy (ATAC + CUT&Tag) "
                     "to build a gene→enhancer→TF→chromatin-program hypothesis.")
        data["gene_axes"] = axes
        data["gene_pathways"] = paths
        data["inferred_regulators"] = regs
        data["inferred_targets"] = tgts

    elif "matched_axis" in facts:
        axis = facts["matched_axis"]
        markers = facts["axis_markers"]
        parts.append(f"Genes associated with the **{axis}** axis:")
        parts.append(f"- Up (drives the score higher): {', '.join(markers['up'])}")
        if markers["down"]:
            parts.append(f"- Down (opposes the score): {', '.join(markers['down'])}")
        parts.append(f"Color the atlas by **{axis}** to see where these states sit in the map.")
        data["axis"] = axis
        data["markers"] = markers

    elif "projection_summary" in facts and facts["projection_summary"]:
        s = facts["projection_summary"]
        comp = s.get("composition_percent", {})
        comp_str = ", ".join(f"{k}: {v}%" for k, v in comp.items())
        parts.append(f"Your uploaded dataset ({facts.get('projection_n_cells', 0)} cells) projects as: {comp_str}.")
        parts.append("Mean exhaustion axes: " +
                     ", ".join(f"{a}={v}" for a, v in s.get("mean_axes", {}).items()) + ".")
        parts.append(f"Mean projection confidence: {s.get('mean_confidence', 0)}.")
        data["summary"] = s

    else:
        comp = facts.get("atlas_composition", {})
        comp_str = ", ".join(f"{k} ({v})" for k, v in comp.items())
        parts.append(f"The reference atlas holds {facts['n_reference_cells']} cells across: {comp_str}.")
        parts.append(f"Continuous axes available: {', '.join(facts['axes'])}.")
        parts.append(f"Regulatory programs / pathways: {', '.join(facts['pathways'])}.")
        parts.append("Try: \"genes for terminal exhaustion\", \"which programs drive TOX\", "
                     "or upload a dataset and ask me to summarize it.")

    return {"answer": "\n\n".join(parts), "backend": backend_name(), "data": data}
