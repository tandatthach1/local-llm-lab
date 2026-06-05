from __future__ import annotations

import html
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .planner import PlanResult, make_plan
from .report import _svg_bar_chart


DEFAULT_COMPARE_QUANTS = ["Q8_0", "Q6_K", "Q5_K_M", "Q4_K_M", "Q3_K_M", "IQ2_XS"]
DEFAULT_COMPARE_CONTEXTS = [4096, 8192, 16384, 32768]
DEFAULT_COMPARE_BACKENDS = ["auto"]

VERDICT_RANK = {"smooth": 0, "tight": 1, "not-recommended": 2, "does-not-fit": 3}
RISK_RANK = {"low": 0, "medium": 1, "high": 2, "extreme": 3}


@dataclass(frozen=True)
class CompareRequest:
    model_name: str | None
    params: str | None
    quantizations: list[str]
    contexts: list[int]
    backends: list[str]
    concurrency: int
    model_format: str | None
    hardware_fixture: str | None
    layers: int | None = None
    heads: int | None = None
    kv_heads: int | None = None
    head_dim: int | None = None
    kv_dtype_bytes: float = 2.0


def parse_csv(value: str | None, defaults: list[str]) -> list[str]:
    if not value:
        return list(defaults)
    items = [item.strip() for item in value.split(",") if item.strip()]
    if not items:
        raise ValueError("Expected at least one comma-separated value.")
    return items


def parse_int_csv(value: str | None, defaults: list[int]) -> list[int]:
    if not value:
        return list(defaults)
    try:
        items = [int(item.strip()) for item in value.split(",") if item.strip()]
    except ValueError as exc:
        raise ValueError(f"Invalid integer list: {value!r}") from exc
    if not items:
        raise ValueError("Expected at least one comma-separated integer.")
    return items


def _sort_key(plan: PlanResult) -> tuple[float, ...]:
    return (
        VERDICT_RANK.get(plan.verdict, 9),
        RISK_RANK.get(plan.risk_level, 9),
        -plan.inputs.quant.bytes_per_param,
        -float(plan.inputs.context_tokens),
        -plan.expected_decode_tokens_s["mid"],
        -plan.memory.margin_gib,
    )


def compare_plans(request: CompareRequest) -> dict[str, Any]:
    plans: list[PlanResult] = []
    for backend in request.backends:
        for quant in request.quantizations:
            for context in request.contexts:
                plans.append(
                    make_plan(
                        model_name=request.model_name,
                        params=request.params,
                        quant_name=quant,
                        context_tokens=context,
                        concurrency=request.concurrency,
                        backend=backend,
                        model_format=request.model_format,
                        hardware_fixture=request.hardware_fixture,
                        layers=request.layers,
                        heads=request.heads,
                        kv_heads=request.kv_heads,
                        head_dim=request.head_dim,
                        kv_dtype_bytes=request.kv_dtype_bytes,
                    )
                )

    sorted_plans = sorted(plans, key=_sort_key)
    runnable = [plan for plan in sorted_plans if plan.verdict in {"smooth", "tight"}]
    best = runnable[0] if runnable else sorted_plans[0]
    verdict_counts: dict[str, int] = {}
    for plan in plans:
        verdict_counts[plan.verdict] = verdict_counts.get(plan.verdict, 0) + 1

    rows = []
    for plan in sorted_plans:
        rows.append(
            {
                "model": plan.inputs.model.id,
                "backend": plan.recommended_backend,
                "requested_backend": plan.inputs.backend,
                "quantization": plan.inputs.quant.name,
                "context_tokens": plan.inputs.context_tokens,
                "concurrency": plan.inputs.concurrency,
                "verdict": plan.verdict,
                "risk_level": plan.risk_level,
                "runtime_required_gib": plan.memory.runtime_required_gib,
                "available_runtime_gib": plan.memory.available_runtime_gib,
                "margin_gib": plan.memory.margin_gib,
                "weights_gib": plan.memory.weights_gib,
                "kv_cache_gib": plan.memory.kv_cache_gib,
                "decode_tokens_s_mid": plan.expected_decode_tokens_s["mid"],
                "confidence": plan.confidence,
            }
        )

    return {
        "compare": {
            "request": {
                "model": request.model_name,
                "params": request.params,
                "quantizations": request.quantizations,
                "contexts": request.contexts,
                "backends": request.backends,
                "concurrency": request.concurrency,
                "format": request.model_format,
                "hardware": f"fixture:{request.hardware_fixture}" if request.hardware_fixture else "local",
            },
            "summary": {
                "total_plans": len(plans),
                "runnable_plans": len(runnable),
                "verdict_counts": verdict_counts,
                "best": {
                    "backend": best.recommended_backend,
                    "quantization": best.inputs.quant.name,
                    "context_tokens": best.inputs.context_tokens,
                    "verdict": best.verdict,
                    "risk_level": best.risk_level,
                    "margin_gib": best.memory.margin_gib,
                    "decode_tokens_s_mid": best.expected_decode_tokens_s["mid"],
                },
            },
            "rows": rows,
        }
    }


def compare_markdown(data: dict[str, Any]) -> str:
    compare = data["compare"]
    summary = compare["summary"]
    best = summary["best"]
    lines = [
        "# local-llm-lab Compare Report",
        "",
        "## Best Candidate",
        "",
        f"- Backend: `{best['backend']}`",
        f"- Quantization: `{best['quantization']}`",
        f"- Context: `{best['context_tokens']}` tokens",
        f"- Verdict: **{best['verdict']}**",
        f"- Risk: **{best['risk_level']}**",
        f"- Margin: `{best['margin_gib']} GiB`",
        f"- Estimated decode: `{best['decode_tokens_s_mid']} tok/s`",
        "",
        "## Matrix",
        "",
        "| Backend | Quant | Context | Verdict | Risk | Runtime GiB | Margin GiB | Decode tok/s |",
        "| --- | --- | ---: | --- | --- | ---: | ---: | ---: |",
    ]
    for row in compare["rows"]:
        lines.append(
            "| {backend} | {quantization} | {context_tokens} | {verdict} | {risk_level} | "
            "{runtime_required_gib} | {margin_gib} | {decode_tokens_s_mid} |".format(**row)
        )
    lines.append("")
    return "\n".join(lines)


def _verdict_class(verdict: str) -> str:
    return {
        "smooth": "ok",
        "tight": "warn",
        "not-recommended": "bad",
        "does-not-fit": "fail",
    }.get(verdict, "neutral")


def compare_html(data: dict[str, Any], chart_files: list[str]) -> str:
    compare = data["compare"]
    summary = compare["summary"]
    best = summary["best"]
    rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(str(row['backend']))}</td>"
        f"<td>{html.escape(str(row['quantization']))}</td>"
        f"<td>{row['context_tokens']}</td>"
        f"<td><span class=\"badge {_verdict_class(str(row['verdict']))}\">{html.escape(str(row['verdict']))}</span></td>"
        f"<td>{html.escape(str(row['risk_level']))}</td>"
        f"<td>{row['runtime_required_gib']}</td>"
        f"<td>{row['margin_gib']}</td>"
        f"<td>{row['decode_tokens_s_mid']}</td>"
        "</tr>"
        for row in compare["rows"]
    )
    charts = "\n".join(f'<img src="{html.escape(name)}" alt="{html.escape(name)}">' for name in chart_files)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>local-llm-lab compare</title>
  <style>
    :root {{ font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #111827; background: #f7f8fb; }}
    body {{ margin: 0; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 28px 20px 56px; }}
    h1 {{ margin: 0 0 6px; font-size: 34px; letter-spacing: 0; }}
    .subtle {{ color: #5b6472; margin: 0 0 22px; }}
    .hero {{ border: 1px solid #d9dee8; background: #fff; border-radius: 8px; padding: 20px; margin-bottom: 18px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; }}
    .metric {{ border: 1px solid #e1e6ef; border-radius: 8px; padding: 13px 14px; background: #fff; }}
    .metric strong {{ display: block; font-size: 22px; margin-top: 5px; }}
    .label {{ color: #667085; font-size: 12px; text-transform: uppercase; letter-spacing: 0; }}
    .badge {{ display: inline-block; border-radius: 999px; padding: 3px 10px; font-size: 12px; font-weight: 700; }}
    .ok {{ color: #065f46; background: #d1fae5; }}
    .warn {{ color: #92400e; background: #fef3c7; }}
    .bad {{ color: #991b1b; background: #fee2e2; }}
    .fail {{ color: #7f1d1d; background: #fecaca; }}
    .neutral {{ color: #334155; background: #e2e8f0; }}
    .section {{ margin-top: 20px; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d9dee8; border-radius: 8px; overflow: hidden; }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid #eef1f6; text-align: left; font-size: 14px; }}
    th {{ background: #f1f4f9; color: #344054; font-size: 12px; text-transform: uppercase; letter-spacing: 0; }}
    img {{ max-width: 100%; background: #fff; border: 1px solid #d9dee8; border-radius: 8px; margin: 10px 0; }}
  </style>
</head>
<body>
<main>
  <h1>Compare Report</h1>
  <p class="subtle">Quantization, context length, and backend tradeoffs for a local LLM run.</p>
  <section class="hero">
    <div class="grid">
      <div class="metric"><span class="label">Best backend</span><strong>{html.escape(str(best['backend']))}</strong></div>
      <div class="metric"><span class="label">Best quant</span><strong>{html.escape(str(best['quantization']))}</strong></div>
      <div class="metric"><span class="label">Context</span><strong>{best['context_tokens']}</strong></div>
      <div class="metric"><span class="label">Verdict</span><strong><span class="badge {_verdict_class(str(best['verdict']))}">{html.escape(str(best['verdict']))}</span></strong></div>
      <div class="metric"><span class="label">Margin</span><strong>{best['margin_gib']} GiB</strong></div>
      <div class="metric"><span class="label">Decode</span><strong>{best['decode_tokens_s_mid']} tok/s</strong></div>
    </div>
  </section>
  <section class="section">{charts}</section>
  <section class="section">
    <table>
      <thead><tr><th>Backend</th><th>Quant</th><th>Context</th><th>Verdict</th><th>Risk</th><th>Runtime GiB</th><th>Margin GiB</th><th>Decode tok/s</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </section>
</main>
</body>
</html>
"""


def write_compare_outputs(data: dict[str, Any], out_dir: str | Path) -> dict[str, Any]:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    json_path = target / "compare.json"
    json_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    md_path = target / "compare.md"
    md_path.write_text(compare_markdown(data), encoding="utf-8")

    rows = data["compare"]["rows"]
    chart_files: list[str] = []
    decode_items = [
        (f"{row['quantization']} {row['context_tokens']}", float(row["decode_tokens_s_mid"]))
        for row in rows[:12]
    ]
    if decode_items:
        decode_svg = target / "compare_decode.svg"
        decode_svg.write_text(_svg_bar_chart(decode_items, "Estimated decode throughput", "tok/s"), encoding="utf-8")
        chart_files.append(decode_svg.name)

    margin_items = [
        (f"{row['quantization']} {row['context_tokens']}", max(float(row["margin_gib"]), 0.0))
        for row in rows[:12]
    ]
    if margin_items:
        margin_svg = target / "compare_margin.svg"
        margin_svg.write_text(_svg_bar_chart(margin_items, "Positive runtime memory margin", "GiB"), encoding="utf-8")
        chart_files.append(margin_svg.name)

    html_path = target / "index.html"
    html_path.write_text(compare_html(data, chart_files), encoding="utf-8")
    return {"out_dir": str(target), "files": [str(path) for path in sorted(target.iterdir()) if path.is_file()]}
