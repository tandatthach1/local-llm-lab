from __future__ import annotations

import json
from typing import Any

from .optional import optional_import
from .planner import PlanResult
from .units import format_gib, format_params


def print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def _rich_console():
    rich = optional_import("rich.console")
    return rich.Console() if rich else None


def print_plan(plan: PlanResult) -> None:
    console = _rich_console()
    model = plan.inputs.model
    hw = plan.inputs.hardware
    mem = plan.memory
    if console:
        table_mod = optional_import("rich.table")
        panel_mod = optional_import("rich.panel")
        if table_mod and panel_mod:
            verdict_color = {
                "smooth": "green",
                "tight": "yellow",
                "not-recommended": "red",
                "does-not-fit": "bold red",
            }.get(plan.verdict, "white")
            console.print(panel_mod.Panel.fit(f"[{verdict_color}]VERDICT: {plan.verdict.upper()}[/]", title="local-llm-lab"))
            table = table_mod.Table(show_header=True, header_style="bold")
            table.add_column("Metric")
            table.add_column("Value")
            table.add_row("Model", f"{model.id} ({format_params(model.params_b)})")
            table.add_row("Hardware", hw.name)
            table.add_row("Quantization", plan.inputs.quant.name)
            table.add_row("Backend", plan.recommended_backend)
            table.add_row("Weights", format_gib(mem.weights_gib))
            table.add_row("KV cache", format_gib(mem.kv_cache_gib))
            table.add_row("Runtime required", format_gib(mem.runtime_required_gib))
            table.add_row("Available runtime memory", format_gib(mem.available_runtime_gib))
            table.add_row("Margin", format_gib(mem.margin_gib))
            table.add_row("Estimated decode", f"{plan.expected_decode_tokens_s['low']}-{plan.expected_decode_tokens_s['high']} tok/s")
            table.add_row("Risk", plan.risk_level)
            table.add_row("Confidence", plan.confidence)
            console.print(table)
            if plan.downgrade_options:
                console.print("[bold]Downgrade options[/]")
                for option in plan.downgrade_options:
                    console.print(f"- {option}")
            if plan.warnings:
                console.print("[bold]Warnings[/]")
                for warning in plan.warnings:
                    console.print(f"- {warning}")
            return

    print(f"VERDICT: {plan.verdict.upper()}  risk={plan.risk_level}  confidence={plan.confidence}")
    print(f"Model: {model.id} ({format_params(model.params_b)}, {model.architecture})")
    print(f"Hardware: {hw.name} | memory={format_gib(hw.memory_total_gib)} | available={format_gib(hw.memory_available_gib)}")
    print(f"Backend: {plan.recommended_backend} | Quantization: {plan.inputs.quant.name}")
    print(f"Weights: {format_gib(mem.weights_gib)}")
    print(f"KV cache: {format_gib(mem.kv_cache_gib)}")
    print(f"Runtime required: {format_gib(mem.runtime_required_gib)}")
    print(f"Available runtime memory: {format_gib(mem.available_runtime_gib)}")
    print(f"Margin: {format_gib(mem.margin_gib)}")
    print(
        "Estimated decode: "
        f"{plan.expected_decode_tokens_s['low']}-{plan.expected_decode_tokens_s['high']} tokens/s"
    )
    if plan.recommended_quantization != plan.inputs.quant.name:
        print(f"Recommended quantization: {plan.recommended_quantization}")
    if plan.downgrade_options:
        print("Downgrade options:")
        for option in plan.downgrade_options:
            print(f"  - {option}")
    if plan.warnings:
        print("Warnings:")
        for warning in plan.warnings:
            print(f"  - {warning}")

