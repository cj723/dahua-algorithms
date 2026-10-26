#!/usr/bin/env python3
"""
Trace health audit for the static demo site.

This script does not modify files. It gives a quick, repeatable picture of
whether the generated JSON can support the beginner-facing debugger UI.
"""

from __future__ import annotations

import json
import statistics
from collections import Counter
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent
TRACE_DIR = BASE / "data" / "traces"
SRC_DIR = BASE.parent / "随书源代码"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def has_step_value(trace: dict, name: str, kind: str) -> bool:
    for step in trace.get("steps", []):
        value = (step.get("vars") or {}).get(name)
        if kind == "grid" and isinstance(value, list) and value and isinstance(value[0], list):
            return True
        if kind == "bipartite" and isinstance(value, dict) and "left" in value and "right" in value and "edges" in value:
            return True
        if kind == "graph" and isinstance(value, dict) and "nodes" in value and "edges" in value:
            return True
        if kind == "tree" and is_tree_snapshot(value):
            return True
        if kind in {"array", "list"} and isinstance(value, list):
            return True
    return False


def is_tree_snapshot(value) -> bool:
    if value is None:
        return True
    if not isinstance(value, list) or len(value) != 3:
        return False
    return (
        not isinstance(value[0], list)
        and is_tree_snapshot(value[1])
        and is_tree_snapshot(value[2])
    )


def renderer_type(trace: dict) -> str:
    classes = trace.get("meta", {}).get("var_classes", {})
    for kind in ("bipartite", "graph", "grid", "tree", "list", "array"):
        for name, info in classes.items():
            if isinstance(info, dict) and info.get("type") == kind and has_step_value(trace, name, kind):
                return kind
    initial = trace.get("meta", {}).get("initial_data", {})
    for value in initial.values():
        if isinstance(value, list) and value and isinstance(value[0], list):
            return "grid"
        if isinstance(value, list):
            return "array"
    for step in trace.get("steps", []):
        for name, value in (step.get("vars") or {}).items():
            if isinstance(value, list):
                continue
            info = classes.get(name, {})
            if not isinstance(info, dict) or info.get("category") != "hidden":
                return "scalar"
    return "none"


def has_large_suspicious_scalar(trace: dict) -> bool:
    pointer_words = (
        "ptr", "node", "root", "head", "tail", "curr", "current", "prev", "next",
        "queue", "stack", "graph", "parent", "result", "res", "return", "word",
        "pattern", "uf", "pq",
    )
    classes = trace.get("meta", {}).get("var_classes", {})
    for step in trace.get("steps", [])[:100]:
        for name, value in (step.get("vars") or {}).items():
            if name == "_return":
                continue
            if not isinstance(value, int) or abs(value) < 1_000_000:
                continue
            lower = name.lower()
            if any(word in lower for word in pointer_words):
                return True
    return False


def main() -> None:
    traces = sorted(TRACE_DIR.glob("*.json"))
    source_names = {p.stem for p in SRC_DIR.rglob("*.c")}
    trace_names = {p.stem for p in traces}

    step_counts = []
    renderer_counts = Counter()
    empty_initial = []
    suspicious_scalars = []
    no_renderer = []
    synthetic = []

    for path in traces:
        trace = read_json(path)
        if trace.get("meta", {}).get("synthetic"):
            synthetic.append(path.name)
        steps = len(trace.get("steps", []))
        step_counts.append(steps)
        rtype = renderer_type(trace)
        renderer_counts[rtype] += 1
        if rtype == "none":
            no_renderer.append(path.name)
        if not trace.get("meta", {}).get("initial_data"):
            empty_initial.append(path.name)
        if has_large_suspicious_scalar(trace):
            suspicious_scalars.append(path.name)

    print("Trace health")
    print("============")
    print(f"sources: {len(source_names)}")
    print(f"traces:  {len(traces)}")
    missing = sorted(source_names - trace_names)
    if missing:
        print(f"missing traces: {', '.join(missing)}")
    if step_counts:
        print(
            "steps: "
            f"min={min(step_counts)} "
            f"median={statistics.median(step_counts)} "
            f"max={max(step_counts)}"
        )
    print(f"renderer coverage: {dict(renderer_counts)}")
    print(f"empty initial_data: {len(empty_initial)}")
    print(f"no renderer data: {len(no_renderer)}")
    print(f"synthetic fallback traces: {len(synthetic)}")
    print(f"suspicious raw-address scalars: {len(suspicious_scalars)}")

    if no_renderer:
        print("\nExamples without renderer data:")
        for name in no_renderer[:20]:
            print(f"  - {name}")

    if suspicious_scalars:
        print("\nExamples with pointer-like raw numbers:")
        for name in suspicious_scalars[:20]:
            print(f"  - {name}")

    if synthetic:
        print("\nSynthetic fallback traces:")
        for name in synthetic[:20]:
            print(f"  - {name}")


if __name__ == "__main__":
    main()
