from __future__ import annotations

import hashlib
import json
import random
import time
from dataclasses import dataclass
from pathlib import Path

from .planner import PlanResult


@dataclass
class BenchResult:
    kind: str
    backend: str
    model: str
    scenarios: list[dict[str, object]]
    notes: list[str]

    def to_dict(self) -> dict[str, object]:
        return {"kind": self.kind, "backend": self.backend, "model": self.model, "scenarios": self.scenarios, "notes": self.notes}


def mock_benchmark(plan: PlanResult | None = None, *, seed: str = "local-llm-lab") -> BenchResult:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    rng = random.Random(int(digest[:12], 16))
    backend = plan.recommended_backend if plan else "mock"
    model = plan.inputs.model.id if plan else "mock-70b"
    mid = plan.expected_decode_tokens_s["mid"] if plan else 12.0
    margin = plan.memory.margin_gib if plan else 24.0
    pressure = 1.0 if margin > 20 else 0.78 if margin > 8 else 0.48
    scenarios = []
    for name, prompt_tokens, output_tokens, concurrency, factor in [
        ("short_prompt", 256, 128, 1, 1.08),
        ("long_context", 8192, 256, 1, 0.72),
        ("prefill_heavy", 32768, 128, 1, 0.42),
        ("concurrent_4", 2048, 128, 4, 0.58),
    ]:
        decode = max(mid * factor * pressure * rng.uniform(0.88, 1.12), 0.05)
        prefill = max(decode * rng.uniform(7.5, 15.0), 0.5)
        latency = prompt_tokens / prefill + output_tokens / decode
        scenarios.append(
            {
                "name": name,
                "prompt_tokens": prompt_tokens,
                "output_tokens": output_tokens,
                "concurrency": concurrency,
                "prefill_tokens_s": round(prefill, 2),
                "decode_tokens_s": round(decode, 2),
                "p50_latency_s": round(latency, 2),
                "p95_latency_s": round(latency * rng.uniform(1.25, 1.8), 2),
                "peak_memory_gib": round((plan.memory.runtime_required_gib if plan else 42.0) * rng.uniform(0.96, 1.04), 2),
                "estimated_power_w": round((60 if backend in {"mlx", "llama.cpp"} else 180) * rng.uniform(0.8, 1.25), 1),
                "temperature_c": round(58 + rng.random() * 18, 1),
            }
        )
    return BenchResult(
        kind="mock",
        backend=backend,
        model=model,
        scenarios=scenarios,
        notes=["Mock benchmark: deterministic demo data, not measured backend performance."],
    )


def save_bench(result: BenchResult, output: str | Path) -> None:
    Path(output).write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True), encoding="utf-8")


def tiny_local_benchmark() -> BenchResult:
    start = time.perf_counter()
    text = "local-llm-lab " * 100_000
    tokens = len(text.split())
    elapsed = max(time.perf_counter() - start, 1e-9)
    return BenchResult(
        kind="local-cpu-smoke",
        backend="python",
        model="none",
        scenarios=[
            {
                "name": "tokenization_smoke",
                "prompt_tokens": tokens,
                "output_tokens": 0,
                "concurrency": 1,
                "prefill_tokens_s": round(tokens / elapsed, 2),
                "decode_tokens_s": 0,
                "p50_latency_s": round(elapsed, 4),
                "p95_latency_s": round(elapsed, 4),
                "peak_memory_gib": 0,
                "estimated_power_w": 0,
                "temperature_c": 0,
            }
        ],
        notes=["CPU smoke benchmark only; use --mock or a backend-specific run for LLM-shaped data."],
    )

