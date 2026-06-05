from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path

from .bench import BenchResult, mock_benchmark
from .planner import PlanResult


@dataclass
class StressResult:
    kind: str
    scenarios: list[dict[str, object]]
    notes: list[str]

    def to_dict(self) -> dict[str, object]:
        return {"kind": self.kind, "scenarios": self.scenarios, "notes": self.notes}


def mock_stress(plan: PlanResult | None = None, bench: BenchResult | None = None, *, seed: str = "stress") -> StressResult:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    rng = random.Random(int(digest[:12], 16))
    base = bench or mock_benchmark(plan)
    baseline = max(float(base.scenarios[0]["decode_tokens_s"]), 0.05)
    memory = plan.memory.runtime_required_gib if plan else 42.0
    available = plan.memory.available_runtime_gib if plan else 96.0
    pressure_ratio = min(memory / max(available, 1.0), 1.8)
    scenarios = []
    for name, gpu_load, extra_memory, factor in [
        ("llm_only", 0.0, 0.0, 1.0),
        ("llm_plus_viewport_render", 0.35, 4.0, 0.82),
        ("llm_plus_blender_preview", 0.65, 10.0, 0.62),
        ("llm_plus_gpu_pressure", 0.85, 18.0, 0.44),
    ]:
        memory_pressure = min((memory + extra_memory) / max(available, 1.0), 2.0)
        stability = "ok"
        if memory_pressure > 1.1:
            stability = "unstable"
        elif memory_pressure > 0.92:
            stability = "watch"
        decode = baseline * factor * max(0.22, 1.0 - gpu_load * 0.35) * rng.uniform(0.92, 1.08)
        scenarios.append(
            {
                "name": name,
                "simulated_gpu_load": gpu_load,
                "extra_memory_gib": extra_memory,
                "memory_pressure_ratio": round(memory_pressure, 2),
                "decode_tokens_s": round(max(decode, 0.03), 2),
                "throughput_drop_pct": round(max(0, 100 * (1 - decode / baseline)), 1),
                "p95_latency_multiplier": round(1 + (baseline / max(decode, 0.03) - 1) * 0.8 + pressure_ratio * 0.2, 2),
                "stability": stability,
            }
        )
    return StressResult(
        kind="mock",
        scenarios=scenarios,
        notes=["Stress data is a reproducible simulation. Real Blender/GPU stress is opt-in for future versions."],
    )


def save_stress(result: StressResult, output: str | Path) -> None:
    Path(output).write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

