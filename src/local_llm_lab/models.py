from __future__ import annotations

from dataclasses import asdict, dataclass, replace

from .units import parse_params


@dataclass(frozen=True)
class ModelProfile:
    id: str
    family: str
    params_b: float
    layers: int
    heads: int
    kv_heads: int
    head_dim: int
    active_params_b: float | None = None
    architecture: str = "dense"
    default_format: str = "gguf"
    confidence: str = "medium"
    note: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @property
    def speed_params_b(self) -> float:
        return self.active_params_b or self.params_b


PRESETS: dict[str, ModelProfile] = {
    "llama-3.1-8b": ModelProfile("llama-3.1-8b", "Llama", 8.0, 32, 32, 8, 128, confidence="high"),
    "llama-3.3-70b": ModelProfile("llama-3.3-70b", "Llama", 70.0, 80, 64, 8, 128, confidence="high"),
    "llama-3.1-405b": ModelProfile("llama-3.1-405b", "Llama", 405.0, 126, 128, 8, 128, confidence="medium"),
    "qwen2.5-32b": ModelProfile("qwen2.5-32b", "Qwen", 32.5, 64, 40, 8, 128, confidence="medium"),
    "qwen2.5-72b": ModelProfile("qwen2.5-72b", "Qwen", 72.7, 80, 64, 8, 128, confidence="medium"),
    "qwen3-235b-a22b": ModelProfile(
        "qwen3-235b-a22b",
        "Qwen",
        235.0,
        94,
        64,
        4,
        128,
        active_params_b=22.0,
        architecture="moe",
        confidence="low",
        note="MoE speed estimate uses active params; memory estimate stores total params.",
    ),
    "deepseek-v3-671b-a37b": ModelProfile(
        "deepseek-v3-671b-a37b",
        "DeepSeek",
        671.0,
        61,
        128,
        128,
        128,
        active_params_b=37.0,
        architecture="moe",
        confidence="low",
        note="Large MoE preset; metadata is conservative and should be overridden when known.",
    ),
    "mixtral-8x7b": ModelProfile(
        "mixtral-8x7b",
        "Mixtral",
        46.7,
        32,
        32,
        8,
        128,
        active_params_b=12.9,
        architecture="moe",
        confidence="medium",
    ),
    "mixtral-8x22b": ModelProfile(
        "mixtral-8x22b",
        "Mixtral",
        141.0,
        56,
        48,
        8,
        128,
        active_params_b=39.0,
        architecture="moe",
        confidence="medium",
    ),
    "gemma-3-27b": ModelProfile("gemma-3-27b", "Gemma", 27.0, 46, 32, 16, 128, confidence="medium"),
    "phi-4-14b": ModelProfile("phi-4-14b", "Phi", 14.0, 40, 40, 10, 128, confidence="medium"),
    "generic-70b": ModelProfile("generic-70b", "Generic", 70.0, 80, 64, 8, 128, confidence="low"),
    "generic-120b": ModelProfile("generic-120b", "Generic", 120.0, 96, 80, 8, 128, confidence="low"),
    "generic-200b": ModelProfile("generic-200b", "Generic", 200.0, 112, 96, 12, 128, confidence="low"),
    "generic-400b": ModelProfile("generic-400b", "Generic", 400.0, 126, 128, 16, 128, confidence="low"),
    "generic-600b": ModelProfile("generic-600b", "Generic", 600.0, 128, 160, 16, 128, confidence="low"),
}


ALIASES = {
    "llama70b": "llama-3.3-70b",
    "llama-70b": "llama-3.3-70b",
    "llama-3-70b": "llama-3.3-70b",
    "llama-405b": "llama-3.1-405b",
    "qwen-72b": "qwen2.5-72b",
    "qwen72b": "qwen2.5-72b",
    "qwen-235b": "qwen3-235b-a22b",
    "deepseek-v3": "deepseek-v3-671b-a37b",
    "deepseek-r1": "deepseek-v3-671b-a37b",
    "600b": "generic-600b",
}


def list_presets() -> list[ModelProfile]:
    return [PRESETS[key] for key in sorted(PRESETS)]


def get_model(name: str) -> ModelProfile:
    key = name.strip().lower()
    key = ALIASES.get(key, key)
    if key not in PRESETS:
        valid = ", ".join(sorted(PRESETS))
        raise ValueError(f"Unknown model preset {name!r}. Valid presets: {valid}")
    return PRESETS[key]


def generic_model_from_params(value: str | float) -> ModelProfile:
    params_b = parse_params(value)
    if params_b <= 15:
        layers, heads, kv_heads = 40, 32, 8
    elif params_b <= 80:
        layers, heads, kv_heads = 80, 64, 8
    elif params_b <= 160:
        layers, heads, kv_heads = 96, 80, 8
    elif params_b <= 260:
        layers, heads, kv_heads = 112, 96, 12
    elif params_b <= 450:
        layers, heads, kv_heads = 126, 128, 16
    else:
        layers, heads, kv_heads = 128, 160, 16
    return ModelProfile(
        id=f"custom-{params_b:g}b",
        family="Custom",
        params_b=params_b,
        layers=layers,
        heads=heads,
        kv_heads=kv_heads,
        head_dim=128,
        confidence="low",
        note="Generic profile inferred from parameter count; override architecture fields when known.",
    )


def apply_overrides(
    model: ModelProfile,
    *,
    params: str | None = None,
    layers: int | None = None,
    heads: int | None = None,
    kv_heads: int | None = None,
    head_dim: int | None = None,
    model_format: str | None = None,
) -> ModelProfile:
    updates: dict[str, object] = {}
    if params is not None:
        updates["params_b"] = parse_params(params)
        updates["confidence"] = "low"
        updates["note"] = (model.note + " " if model.note else "") + "Parameter count overridden by user."
    if layers is not None:
        updates["layers"] = layers
    if heads is not None:
        updates["heads"] = heads
    if kv_heads is not None:
        updates["kv_heads"] = kv_heads
    if head_dim is not None:
        updates["head_dim"] = head_dim
    if model_format is not None:
        updates["default_format"] = model_format
    return replace(model, **updates)

