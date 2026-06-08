from __future__ import annotations

import json
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .compare import CompareRequest, compare_plans
from .planner import make_plan


@dataclass(frozen=True)
class RecommendRequest:
    compare_request: CompareRequest
    target: str = "tight"


def _acceptable_verdicts(target: str) -> set[str]:
    if target == "smooth":
        return {"smooth"}
    if target == "tight":
        return {"smooth", "tight"}
    raise ValueError("target must be 'smooth' or 'tight'")


def _recommend_command(request: RecommendRequest) -> str:
    compare_request = request.compare_request
    command = ["python3", "-m", "local_llm_lab", "recommend"]
    if compare_request.model_name:
        command.extend(["--model", compare_request.model_name])
    elif compare_request.params:
        command.extend(["--params", compare_request.params])
    if compare_request.hardware_label and compare_request.hardware_label != "local":
        command.extend(["--hardware", compare_request.hardware_label])
    command.extend(["--quants", ",".join(compare_request.quantizations)])
    command.extend(["--contexts", ",".join(str(item) for item in compare_request.contexts)])
    command.extend(["--backends", ",".join(compare_request.backends)])
    command.extend(["--target", request.target])
    return " ".join(shlex.quote(part) for part in command)


def _plan_for_row(request: RecommendRequest, row: dict[str, Any]):
    compare_request = request.compare_request
    return make_plan(
        model_name=compare_request.model_name,
        params=compare_request.params,
        quant_name=str(row["quantization"]),
        context_tokens=int(row["context_tokens"]),
        concurrency=compare_request.concurrency,
        backend=str(row["backend"]),
        model_format=compare_request.model_format,
        hardware_fixture=compare_request.hardware_fixture,
        hardware=compare_request.hardware_profile,
        layers=compare_request.layers,
        heads=compare_request.heads,
        kv_heads=compare_request.kv_heads,
        head_dim=compare_request.head_dim,
        kv_dtype_bytes=compare_request.kv_dtype_bytes,
    )


def _why(status: str, target: str, best: dict[str, Any], total: int, matched: int) -> list[str]:
    if status == "recommended":
        return [
            f"Meets the requested target ({target}) within the scanned quantization/context/backend matrix.",
            f"Selected from {matched} acceptable candidates out of {total} total plans.",
            f"Estimated runtime memory margin is {best['margin_gib']} GiB with {best['decode_tokens_s_mid']} tok/s mid decode.",
        ]
    return [
        f"No candidate met the requested target ({target}) in the scanned matrix.",
        f"Least risky candidate is {best['quantization']} at {best['context_tokens']} context, but verdict is {best['verdict']} with {best['risk_level']} risk.",
        f"Estimated runtime memory margin is {best['margin_gib']} GiB; treat generated commands as investigation aids only.",
    ]


def _next_steps(status: str, best: dict[str, Any], plan) -> list[str]:
    if status == "recommended":
        steps = [
            "Generate the deploy dry-run files and run preflight before launching a real backend.",
            "Run a short benchmark after confirming the local model path and backend binary.",
        ]
        if best["verdict"] == "tight":
            steps.append("Keep other memory-heavy apps closed during first validation because this plan is tight.")
        return steps
    steps = list(plan.downgrade_options)
    steps.append("Re-run recommend with lower quantization, shorter context, or a smaller model.")
    return steps[:6]


def recommend_plans(request: RecommendRequest) -> dict[str, Any]:
    acceptable = _acceptable_verdicts(request.target)
    data = compare_plans(request.compare_request)
    compare = data["compare"]
    rows = compare["rows"]
    matches = [row for row in rows if row["verdict"] in acceptable]
    status = "recommended" if matches else "no-fit"
    best = matches[0] if matches else rows[0]
    plan = _plan_for_row(request, best)
    alternatives = [row for row in rows if row is not best and row["verdict"] in acceptable][:3]
    if not alternatives:
        alternatives = [row for row in rows if row is not best][:3]

    recommendation = {
        "status": status,
        "target": request.target,
        "best": best,
        "alternatives": alternatives,
        "why": _why(status, request.target, best, len(rows), len(matches)),
        "next_steps": _next_steps(status, best, plan),
        "downgrade_options": plan.downgrade_options,
        "warnings": plan.warnings,
        "deploy_command": best["deploy_command"],
        "recommend_command": _recommend_command(request),
    }
    return {"recommendation": recommendation, "compare": compare}


def recommend_markdown(data: dict[str, Any]) -> str:
    rec = data["recommendation"]
    best = rec["best"]
    lines = [
        "# local-llm-lab Recommendation",
        "",
        f"- Status: **{rec['status']}**",
        f"- Target: `{rec['target']}`",
        f"- Backend: `{best['backend']}`",
        f"- Quantization: `{best['quantization']}`",
        f"- Context: `{best['context_tokens']}` tokens",
        f"- Verdict: **{best['verdict']}** risk={best['risk_level']}",
        f"- Runtime required: `{best['runtime_required_gib']} GiB`",
        f"- Memory margin: `{best['margin_gib']} GiB`",
        f"- Estimated decode: `{best['decode_tokens_s_mid']} tok/s`",
        "",
        "## Why",
        "",
    ]
    lines.extend(f"- {item}" for item in rec["why"])
    lines.extend(["", "## Next Steps", ""])
    lines.extend(f"- {item}" for item in rec["next_steps"])
    lines.extend(["", "## Commands", "", "```bash", rec["deploy_command"], "```", ""])
    if rec["alternatives"]:
        lines.extend(
            [
                "## Alternatives",
                "",
                "| Backend | Quant | Context | Verdict | Risk | Margin GiB | Decode tok/s |",
                "| --- | --- | ---: | --- | --- | ---: | ---: |",
            ]
        )
        for row in rec["alternatives"]:
            lines.append(
                "| {backend} | {quantization} | {context_tokens} | {verdict} | {risk_level} | {margin_gib} | {decode_tokens_s_mid} |".format(
                    **row
                )
            )
    lines.append("")
    return "\n".join(lines)


def write_recommend_outputs(data: dict[str, Any], out_dir: str | Path) -> dict[str, Any]:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    json_path = target / "recommend.json"
    json_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    md_path = target / "recommend.md"
    md_path.write_text(recommend_markdown(data), encoding="utf-8")
    return {"out_dir": str(target), "files": [str(path) for path in sorted(target.iterdir()) if path.is_file()]}
