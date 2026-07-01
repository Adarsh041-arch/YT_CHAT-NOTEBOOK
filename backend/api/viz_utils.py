"""Visualization classifier and spec generator for YTChatBot."""
from __future__ import annotations

import json
import os
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from src.config import LLMConfig, VizConfig
from src.tracing import traceable
from .models import VizChart, VizGraph, VizSimulation, VizDiagram, VizCustom


def _get_viz_llm(model_override: str | None = None, max_tokens: int = 10, temperature: float = 0.0):
    from langchain_openai import ChatOpenAI
    if LLMConfig.LLM_PROVIDER == "nvidia":
        return ChatOpenAI(
            base_url=LLMConfig.NVIDIA_BASE_URL,
            api_key=LLMConfig.NVIDIA_API_KEY or os.environ.get("NVIDIA_API_KEY", ""),
            model=model_override or VizConfig.CLASSIFIER_MODEL,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    elif LLMConfig.LLM_PROVIDER == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        # Google's Gemini API has a bug where passing a very small max_output_tokens (like 10)
        # causes it to return an empty string. Keep it at least 100 to avoid empty responses.
        adjusted_max_tokens = max(max_tokens, 100) if max_tokens is not None else None
        return ChatGoogleGenerativeAI(
            google_api_key=LLMConfig.GOOGLE_API_KEY or os.environ.get("GOOGLE_API_KEY", ""),
            model=model_override or VizConfig.CLASSIFIER_MODEL,
            temperature=temperature,
            max_output_tokens=adjusted_max_tokens,
        )
    return ChatOpenAI(
        base_url=LLMConfig.OPENROUTER_BASE_URL,
        api_key=LLMConfig.OPENROUTER_API_KEY or os.environ.get("OPENROUTER_API_KEY", ""),
        model=model_override or VizConfig.CLASSIFIER_MODEL,
        temperature=temperature,
        max_tokens=max_tokens,
    )


CLASSIFIER_PROMPT = (
    "You are deciding whether a visualization would help answer this question.\n\n"
    "User query: {query}\n"
    "Retrieved context: {context}\n\n"
    "Categories:\n"
    "- none: factual/definitional question, text explanation is sufficient\n"
    "- chart: comparing numbers/values, time trends, distributions, percentages, numeric data sets\n"
    "- graph: networks, connections, ontologies, hierarchies, node-link relations, family trees\n"
    "- custom: dynamic step-by-step processes, algorithm executions/simulations (e.g. backpropagation, sorting), physical movements, custom canvas drawings\n"
    "- diagram: software architecture, state diagrams, logical flow charts, sequence diagrams\n\n"
    "Rules:\n"
    "1. Categorize strictly. Output exactly one word from ('none', 'chart', 'graph', 'custom', 'diagram').\n"
    "2. If the user explicitly asks to 'simulate', 'show a simulation', 'animate', 'draw', 'chart', 'graph', 'diagram', 'flowchart', or 'visualize' a process/algorithm/data, classify it under the appropriate category (e.g. 'custom' for simulations/animations, 'diagram' for flowcharts/sequence diagrams, 'chart' for charts, 'graph' for network graphs) instead of 'none'.\n"
    "3. If it is a basic factual or text-only query without any explicit request for visualization or process flow, classify as 'none'.\n\n"
    "Examples:\n"
    "Query: 'Can you show the percentage of views by country?' -> chart\n"
    "Query: 'Draw a dependency network of these classes.' -> graph\n"
    "Query: 'How does backpropagation change weights step-by-step?' -> custom\n"
    "Query: 'Create a process flow of RAG pipeline.' -> diagram\n"
    "Query: 'Show a simulation of neural network training steps.' -> custom\n"
    "Query: 'What is a neural network?' -> none\n\n"
    "Respond with only the category name (one of: none, chart, graph, custom, diagram) in lowercase, nothing else."
)


@traceable(run_type="chain", name="classify_visualization")
async def classify_visualization(query: str, context_chunks: list[str]) -> str:
    """Returns one of: none, chart, graph, simulation, diagram, custom."""
    context_str = "\n\n".join(c[:800] for c in context_chunks[:5])
    llm = _get_viz_llm(max_tokens=VizConfig.CLASSIFIER_MAX_TOKENS, temperature=VizConfig.CLASSIFIER_TEMPERATURE)
    messages = [
        SystemMessage(content="You are a classifier. Output exactly one word."),
        HumanMessage(content=CLASSIFIER_PROMPT.format(query=query, context=context_str)),
    ]
    try:
        response = await llm.ainvoke(messages)
        category = response.content.strip().lower()
        if category in ("chart", "graph", "simulation", "diagram", "custom"):
            return category
        return "none"
    except Exception as e:
        print(f"[viz] Classifier error: {e}")
        return "none"


SPEC_PROMPTS = {
    "chart": (
        "Given the user query and context below, create a chart visualization spec.\n"
        "Output ONLY valid JSON matching this schema (no markdown, no explanation):\n"
        '{{"type": "chart", "chartType": "bar|line|scatter|pie", "title": "string", '
        '"data": [{{"label": "string", "value": number}}], "xLabel": "string", "yLabel": "string"}}\n\n'
        "CRITICAL: Keep data labels very short (under 12 characters) to prevent overlapping on the graph axis.\n\n"
        "Query: {query}\nContext: {context}"
    ),
    "graph": (
        "Given the user query and context below, create a graph visualization spec.\n"
        "Output ONLY valid JSON matching this schema (no markdown, no explanation):\n"
        '{{"type": "graph", "title": "string", '
        '"nodes": [{{"id": "string", "label": "string"}}], '
        '"edges": [{{"source": "string", "target": "string", "label": "string (optional)"}}], '
        '"layout": "force|tree|radial"}}\n\n'
        "CRITICAL: Keep node labels very short (under 12 characters) to prevent overlapping.\n\n"
        "Query: {query}\nContext: {context}"
    ),
    "simulation": (
        "Given the user query and context below, create a simulation visualization spec.\n"
        "Output ONLY valid JSON matching this schema (no markdown, no explanation):\n"
        '{{"type": "simulation", "simType": "particles|physics|algorithm-steps", '
        '"title": "string", "params": {{...}}, '
        '"steps": [{{"description": "string", "state": {{}}}}]}}\n\n'
        "CRITICAL: For 'algorithm-steps', keep step descriptions concise (under 75 characters) so they wrap cleanly.\n"
        "Keep state dictionary keys (variable names) short (under 10 characters). Values must be numbers (e.g. weights, biases, gradients) representing quantitative metrics at each step.\n\n"
        "Query: {query}\nContext: {context}"
    ),
    "diagram": (
        "Given the user query and context below, create a diagram visualization spec.\n"
        "Output ONLY valid JSON matching this schema (no markdown, no explanation):\n"
        '{{"type": "diagram", "diagramType": "flowchart|sequence", '
        '"mermaidSyntax": "string"}}\n\n'
        "RULES FOR mermaidSyntax:\n"
        "- First line must be exactly 'flowchart TD' or 'sequenceDiagram'.\n"
        "- Use only simple node links: 'A --> B' or 'A --- B'.\n"
        "- Node labels inside brackets [] must be short, plain text, no special chars.\n"
        "- NO trailing semicolons on any line.\n"
        "- NO curly/smart quotes, NO emoji, NO unicode symbols.\n"
        "- Each line must have exactly one arrow or connection.\n"
        "- For sequences: 'Alice->>Bob: Short message' (use ->> arrows only).\n"
        "- Keep total lines under 15.\n\n"
        "VALID flowchart example:\n"
        "flowchart TD\n"
        "A[Start] --> B[Process]\n"
        "B --> C[End]\n\n"
        "VALID sequence example:\n"
        "sequenceDiagram\n"
        "Alice->>Bob: Hello\n"
        "Bob-->>Alice: Response\n\n"
        "Query: {query}\nContext: {context}"
    ),
    "custom": (
        "You are generating a custom p5.js animation to visually explain a concept for a student.\n\n"
        "Topic: {query}\n"
        "Context from source material: {context}\n\n"
        "Requirements:\n"
        "- Write ONLY the JavaScript statements inside the body of a buildSketch(p, container) function using p5.js instance mode.\n"
        "- Do NOT wrap it in JSON. Do NOT write `function buildSketch(p, container) {{` wrapper. Only return the statements to be executed.\n"
        "- Must define setup and draw on p instance. Setup should create canvas inside container.\n"
        "  For example: p.setup = () => {{ const w = container.clientWidth || 400; p.createCanvas(w, 280); ... }}\n"
        "- CRITICAL: Always declare all global animation variables (such as timers, current steps, weights, costs, arrays, or epoch counters) at the very top of the script using 'let' or 'const'. Never write to undeclared variables (e.g. assigning to a cost variable without declaring it first at the top), or it will fail with a ReferenceError.\n"
        "- Design the simulation sequence to be concise: the full sequence or loop of steps should complete and repeat (or restart) within about 10-15 seconds (e.g., at 60fps, limit the main loop sequence to around 600-900 frames). Keep states/steps snappy and transition quickly.\n"
        "- Do NOT require user interaction (like mouse clicks or key presses) to start the animation. The simulation must start playing and animating automatically as soon as it loads.\n"
        "- The visualization must make the underlying mechanism visible and intuitive (e.g. show state updating over time, weights changing, values moving).\n"
        "- Must use colors fitting a dark theme (dark background #0f0f1e, high-contrast labels/drawings).\n"
        "- Include readable canvas labels using p.text() for key values.\n"
        "- Keep it performant: avoid O(n^2)+ complexity in draw() loops.\n"
        "- Do NOT reference window, document, fetch, XMLHttpRequest, eval, localStorage, sessionStorage, parent, top, or browser APIs outside the 'p' object and 'container'.\n\n"
        "Output ONLY the clean, raw JavaScript code, with no markdown fences, no prose, and no explanation."
    ),
}

SCHEMA_MAP = {
    "chart": VizChart,
    "graph": VizGraph,
    "simulation": VizSimulation,
    "diagram": VizDiagram,
    "custom": VizCustom,
}


@traceable(run_type="chain", name="generate_viz_spec")
async def generate_viz_spec(category: str, query: str, context_chunks: list[str]) -> dict[str, Any] | None:
    """Generate and validate a visualization spec. Returns validated dict or None."""
    if category not in SPEC_PROMPTS:
        return None

    context_str = "\n\n".join(c[:800] for c in context_chunks[:5])
    prompt = SPEC_PROMPTS[category].format(query=query, context=context_str)

    llm = _get_viz_llm(
        model_override=VizConfig.SPEC_GEN_MODEL,
        max_tokens=VizConfig.SPEC_GEN_MAX_TOKENS,
        temperature=0.1,
    )

    try:
        if category == "custom":
            response = await llm.ainvoke([
                SystemMessage(content="You output only the raw JavaScript code body. No markdown formatting, no code blocks (do not use ```), and no comments/explanations outside the code."),
                HumanMessage(content=prompt),
            ])
            raw_code = response.content.strip()
            # Remove any leading/trailing backticks or markdown code fences
            if raw_code.startswith("```"):
                lines = raw_code.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                raw_code = "\n".join(lines).strip()
            
            title = f"Simulation: {query}"
            if len(title) > 50:
                title = title[:47] + "..."
                
            data = {
                "type": "custom",
                "title": title,
                "code": raw_code
            }
            model = SCHEMA_MAP[category](**data)
            return model.model_dump()

        response = await llm.ainvoke([
            SystemMessage(content="You output only valid JSON. No markdown, no commentary."),
            HumanMessage(content=prompt),
        ])
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.strip("`").strip()
            if raw.startswith("json"):
                raw = raw[4:].strip()
        data = json.loads(raw)
        model = SCHEMA_MAP[category](**data)
        return model.model_dump()
    except Exception as e:
        print(f"[viz] Spec generation/validation error ({category}): {e}")
        return None


@traceable(run_type="chain", name="regenerate_viz_spec")
async def regenerate_viz_spec(category: str, query: str, failed_code: str, error_message: str) -> dict[str, Any] | None:
    """Regenerate a spec using error feedback from a previous generation failure."""
    llm = _get_viz_llm(
        model_override=VizConfig.SPEC_GEN_MODEL,
        max_tokens=VizConfig.SPEC_GEN_MAX_TOKENS,
        temperature=0.1,
    )

    try:
        if category == "custom":
            system_msg = (
                "You are an expert p5.js programmer and debugger correcting a buggy visualization script.\n"
                "You output ONLY corrected raw JavaScript code statements. No markdown formatting, no JSON, no code blocks (do not use ```), and no commentary/prose."
            )
            feedback = (
                f"Your previously generated p5.js code for the topic '{query}' failed with the following error:\n"
                f"Error: {error_message}\n\n"
                f"Buggy Code:\n"
                f"```javascript\n{failed_code}\n```\n\n"
                f"Requirements to fix it:\n"
                f"1. Analyze the failure and correct the bug (such as missing variable definitions, invalid syntax, or references to forbidden globals).\n"
                f"2. Ensure all state/global variables are explicitly declared at the very top of the script using 'let' or 'const' (e.g. declare any cost or array variables there first).\n"
                f"3. Make sure to assign both setup and draw on the 'p' instance (e.g. p.setup = () => {{ ... }}; p.draw = () => {{ ... }};).\n"
                f"4. Design the simulation sequence to be concise: the full sequence or loop of steps should complete and repeat (or restart) within about 10-15 seconds (e.g., at 60fps, limit the main loop sequence to around 600-900 frames). Keep states/steps snappy and transition quickly.\n"
                f"5. Do NOT require user interaction (like mouse clicks or key presses) to start the animation. The simulation must start playing and animating automatically as soon as it loads.\n"
                f"6. Do NOT wrap your output in JSON or write standard function buildSketch wrapper. Output only the body statements."
            )
            
            response = await llm.ainvoke([
                SystemMessage(content=system_msg),
                HumanMessage(content=feedback),
            ])
            raw_code = response.content.strip()
            if raw_code.startswith("```"):
                lines = raw_code.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                raw_code = "\n".join(lines).strip()
            
            title = f"Simulation: {query}"
            if len(title) > 50:
                title = title[:47] + "..."
                
            data = {
                "type": "custom",
                "title": title,
                "code": raw_code
            }
            model = SCHEMA_MAP[category](**data)
            return model.model_dump()
            
        else:
            # For JSON categories (chart, graph, diagram)
            system_msg = (
                "You are an expert data visualizer debugging a malformed JSON specification.\n"
                "You output ONLY corrected valid JSON. No markdown formatting, no code blocks, and no commentary."
            )
            feedback = (
                f"Your previously generated JSON visualization spec for the topic '{query}' failed validation with the following error:\n"
                f"Error: {error_message}\n\n"
                f"Buggy JSON Spec:\n"
                f"{failed_code}\n\n"
                f"Please fix the schema or format error and output ONLY the corrected JSON string matching the expected schema."
            )
            response = await llm.ainvoke([
                SystemMessage(content=system_msg),
                HumanMessage(content=feedback),
            ])
            raw = response.content.strip()
            if raw.startswith("```"):
                raw = raw.strip("`").strip()
                if raw.startswith("json"):
                    raw = raw[4:].strip()
            data = json.loads(raw)
            model = SCHEMA_MAP[category](**data)
            return model.model_dump()
            
    except Exception as e:
        print(f"[viz] Spec regeneration error ({category}): {e}")
        return None

