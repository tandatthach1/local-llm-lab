from __future__ import annotations

import html
import json
import shutil
from pathlib import Path
from typing import Any

from .optional import optional_import


def _load(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _svg_bar_chart(items: list[tuple[str, float]], title: str, unit: str) -> str:
    width, height = 860, 360
    margin_left, margin_bottom = 160, 54
    plot_w, plot_h = width - margin_left - 40, height - 90
    max_value = max([value for _, value in items] + [1.0])
    rows = []
    for idx, (label, value) in enumerate(items):
        y = 54 + idx * (plot_h / max(len(items), 1))
        bar_h = min(34, plot_h / max(len(items), 1) * 0.64)
        bar_w = value / max_value * plot_w
        rows.append(
            f'<text x="12" y="{y + bar_h * 0.72:.1f}" font-size="14">{html.escape(label)}</text>'
            f'<rect x="{margin_left}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" rx="4" fill="#2563eb"/>'
            f'<text x="{margin_left + bar_w + 8:.1f}" y="{y + bar_h * 0.72:.1f}" font-size="13">{value:.2f} {html.escape(unit)}</text>'
        )
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<rect width="100%" height="100%" fill="#ffffff"/>',
            f'<text x="20" y="30" font-size="20" font-weight="700">{html.escape(title)}</text>',
            *rows,
            f'<line x1="{margin_left}" y1="{height - margin_bottom}" x2="{width - 32}" y2="{height - margin_bottom}" stroke="#94a3b8"/>',
            "</svg>",
        ]
    )


def _markdown(data: dict[str, Any]) -> str:
    plan = data.get("plan", {})
    bench = data.get("bench", {})
    stress = data.get("stress", {})
    inputs = plan.get("inputs", {})
    model = inputs.get("model", {})
    hw = inputs.get("hardware", {})
    memory = plan.get("memory", {})
    lines = [
        "# local-llm-lab Report",
        "",
        "## Verdict",
        "",
        f"- Verdict: **{plan.get('verdict', 'unknown')}**",
        f"- Risk level: **{plan.get('risk_level', 'unknown')}**",
        f"- Confidence: **{plan.get('confidence', 'unknown')}**",
        f"- Recommended backend: `{plan.get('recommended_backend', 'unknown')}`",
        f"- Recommended quantization: `{plan.get('recommended_quantization', 'unknown')}`",
        "",
        "## Plan Inputs",
        "",
        f"- Model: `{model.get('id', 'unknown')}` ({model.get('params_b', '?')}B)",
        f"- Hardware: `{hw.get('name', 'unknown')}`",
        f"- Context: `{inputs.get('context_tokens', '?')}` tokens",
        f"- Concurrency: `{inputs.get('concurrency', '?')}`",
        "",
        "## Memory Estimate",
        "",
        "| Metric | GiB |",
        "| --- | ---: |",
    ]
    for key in [
        "weights_gib",
        "kv_cache_gib",
        "backend_overhead_gib",
        "activation_gib",
        "runtime_required_gib",
        "available_runtime_gib",
        "margin_gib",
    ]:
        lines.append(f"| {key.replace('_', ' ')} | {memory.get(key, 0)} |")

    scenarios = bench.get("scenarios", [])
    if scenarios:
        lines.extend(["", "## Benchmark", "", "| Scenario | Decode tok/s | P95 latency s | Peak GiB |", "| --- | ---: | ---: | ---: |"])
        for row in scenarios:
            lines.append(
                f"| {row.get('name')} | {row.get('decode_tokens_s')} | {row.get('p95_latency_s')} | {row.get('peak_memory_gib')} |"
            )

    stress_rows = stress.get("scenarios", [])
    if stress_rows:
        lines.extend(["", "## Stress Simulation", "", "| Scenario | Drop % | Pressure | Stability |", "| --- | ---: | ---: | --- |"])
        for row in stress_rows:
            lines.append(
                f"| {row.get('name')} | {row.get('throughput_drop_pct')} | {row.get('memory_pressure_ratio')} | {row.get('stability')} |"
            )

    warnings = plan.get("warnings", [])
    if warnings:
        lines.extend(["", "## Warnings", ""])
        for warning in warnings:
            lines.append(f"- {warning}")
    downgrades = plan.get("downgrade_options", [])
    if downgrades:
        lines.extend(["", "## Downgrade Options", ""])
        for option in downgrades:
            lines.append(f"- {option}")
    lines.append("")
    return "\n".join(lines)


def _html_doc(markdown: str, svg_files: list[str]) -> str:
    escaped = html.escape(markdown)
    sections = []
    for svg in svg_files:
        sections.append(f'<section><img src="{html.escape(svg)}" alt="{html.escape(svg)}"></section>')
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>local-llm-lab report</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    body {{ margin: 0; background: #f8fafc; color: #0f172a; }}
    main {{ max-width: 1040px; margin: 0 auto; padding: 32px 20px 56px; }}
    h1 {{ font-size: 34px; margin: 0 0 10px; }}
    pre {{ white-space: pre-wrap; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; line-height: 1.55; }}
    img {{ max-width: 100%; background: white; border: 1px solid #e2e8f0; border-radius: 8px; margin: 18px 0; }}
  </style>
</head>
<body>
<main>
  <h1>local-llm-lab report</h1>
  {''.join(sections)}
  <pre>{escaped}</pre>
</main>
</body>
</html>
"""


def _matplotlib_chart(items: list[tuple[str, float]], out: Path, title: str) -> None:
    pyplot = optional_import("matplotlib.pyplot")
    if not pyplot:
        return
    labels = [item[0] for item in items]
    values = [item[1] for item in items]
    fig, ax = pyplot.subplots(figsize=(9, 4))
    ax.barh(labels, values, color="#2563eb")
    ax.set_title(title)
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(out)
    pyplot.close(fig)


def generate_report(input_path: str | Path, out_dir: str | Path) -> dict[str, Any]:
    source = _load(input_path)
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)

    report_json = target / "report.json"
    report_json.write_text(json.dumps(source, indent=2, sort_keys=True), encoding="utf-8")

    md = _markdown(source)
    markdown_path = target / "report.md"
    markdown_path.write_text(md, encoding="utf-8")

    svg_files: list[str] = []
    bench_items = [
        (str(row.get("name", "scenario")), float(row.get("decode_tokens_s", 0)))
        for row in source.get("bench", {}).get("scenarios", [])
    ]
    if bench_items:
        path = target / "decode_tokens.svg"
        path.write_text(_svg_bar_chart(bench_items, "Decode throughput", "tok/s"), encoding="utf-8")
        svg_files.append(path.name)
        _matplotlib_chart(bench_items, target / "decode_tokens.png", "Decode throughput")

    stress_items = [
        (str(row.get("name", "scenario")), float(row.get("throughput_drop_pct", 0)))
        for row in source.get("stress", {}).get("scenarios", [])
    ]
    if stress_items:
        path = target / "stress_drop.svg"
        path.write_text(_svg_bar_chart(stress_items, "Stress throughput drop", "%"), encoding="utf-8")
        svg_files.append(path.name)
        _matplotlib_chart(stress_items, target / "stress_drop.png", "Stress throughput drop")

    html_path = target / "index.html"
    html_path.write_text(_html_doc(md, svg_files), encoding="utf-8")
    source_copy = target / "source-input.json"
    if Path(input_path) != source_copy:
        try:
            shutil.copyfile(input_path, source_copy)
        except shutil.SameFileError:
            pass

    return {
        "out_dir": str(target),
        "files": [str(path) for path in sorted(target.iterdir()) if path.is_file()],
    }

