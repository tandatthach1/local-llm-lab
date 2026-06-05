from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Quantization:
    name: str
    bits: float
    bytes_per_param: float
    quality_note: str


QUANTIZATIONS: dict[str, Quantization] = {
    "F16": Quantization("F16", 16, 2.00, "Highest memory use; good quality baseline."),
    "BF16": Quantization("BF16", 16, 2.00, "Highest memory use; common for training/native checkpoints."),
    "Q8_0": Quantization("Q8_0", 8, 1.05, "Large but usually close to full precision for inference."),
    "Q6_K": Quantization("Q6_K", 6, 0.80, "Good quality, still expensive for very large models."),
    "Q5_K_M": Quantization("Q5_K_M", 5, 0.68, "Often a strong quality/memory compromise."),
    "Q4_K_M": Quantization("Q4_K_M", 4, 0.56, "Common default for local GGUF deployments."),
    "Q4_0": Quantization("Q4_0", 4, 0.53, "Smaller legacy 4-bit option; quality can vary."),
    "Q3_K_M": Quantization("Q3_K_M", 3, 0.44, "Aggressive compression; expect quality loss."),
    "IQ3_XS": Quantization("IQ3_XS", 3, 0.40, "Aggressive imatrix-style quantization; model dependent."),
    "IQ2_XS": Quantization("IQ2_XS", 2, 0.31, "Last-resort tiny quantization; quality risk is high."),
}


ALIASES = {
    "fp16": "F16",
    "float16": "F16",
    "bf16": "BF16",
    "q8": "Q8_0",
    "q8_0": "Q8_0",
    "q6": "Q6_K",
    "q6_k": "Q6_K",
    "q5": "Q5_K_M",
    "q5_k_m": "Q5_K_M",
    "q4": "Q4_K_M",
    "q4_k_m": "Q4_K_M",
    "q4_0": "Q4_0",
    "q3": "Q3_K_M",
    "q3_k_m": "Q3_K_M",
    "iq3": "IQ3_XS",
    "iq3_xs": "IQ3_XS",
    "iq2": "IQ2_XS",
    "iq2_xs": "IQ2_XS",
}


def get_quantization(name: str) -> Quantization:
    key = ALIASES.get(name.strip().lower(), name.strip().upper())
    if key not in QUANTIZATIONS:
        valid = ", ".join(QUANTIZATIONS)
        raise ValueError(f"Unknown quantization {name!r}. Valid values: {valid}")
    return QUANTIZATIONS[key]


def lower_memory_quants(starting_from: str) -> list[Quantization]:
    current = get_quantization(starting_from)
    ordered = sorted(QUANTIZATIONS.values(), key=lambda q: q.bytes_per_param, reverse=True)
    return [q for q in ordered if q.bytes_per_param < current.bytes_per_param]

