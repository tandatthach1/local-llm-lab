from __future__ import annotations

from copy import deepcopy


BUILTIN_FIXTURES: dict[str, dict[str, object]] = {
    "apple-m4-max-64gb": {
        "name": "Mock Apple Silicon Max-class 64GB",
        "os": "macOS",
        "arch": "arm64",
        "cpu": "Apple Silicon Max-class",
        "gpu": "Integrated Apple GPU",
        "unified_memory": True,
        "memory_total_gib": 64.0,
        "memory_available_gib": 51.0,
        "disk_available_gib": 900.0,
        "memory_bandwidth_gbps": 410.0,
        "metal": True,
        "cuda": False,
        "avx": False,
        "neon": True,
        "note": "Illustrative fixture for demos; not a measured machine.",
    },
    "apple-m4-max-128gb": {
        "name": "Mock Apple Silicon Max-class 128GB",
        "os": "macOS",
        "arch": "arm64",
        "cpu": "Apple Silicon Max-class",
        "gpu": "Integrated Apple GPU",
        "unified_memory": True,
        "memory_total_gib": 128.0,
        "memory_available_gib": 110.0,
        "disk_available_gib": 1800.0,
        "memory_bandwidth_gbps": 546.0,
        "metal": True,
        "cuda": False,
        "avx": False,
        "neon": True,
        "note": "Illustrative fixture for demos; not a measured machine.",
    },
    "apple-m3-ultra-192gb": {
        "name": "Mock Apple Silicon Ultra-class 192GB",
        "os": "macOS",
        "arch": "arm64",
        "cpu": "Apple Silicon Ultra-class",
        "gpu": "Integrated Apple GPU",
        "unified_memory": True,
        "memory_total_gib": 192.0,
        "memory_available_gib": 166.0,
        "disk_available_gib": 2500.0,
        "memory_bandwidth_gbps": 800.0,
        "metal": True,
        "cuda": False,
        "avx": False,
        "neon": True,
        "note": "Illustrative fixture for demos; not a measured machine.",
    },
    "apple-m4-ultra-256gb": {
        "name": "Mock Apple Silicon Ultra-class 256GB",
        "os": "macOS",
        "arch": "arm64",
        "cpu": "Apple Silicon Ultra-class",
        "gpu": "Integrated Apple GPU",
        "unified_memory": True,
        "memory_total_gib": 256.0,
        "memory_available_gib": 224.0,
        "disk_available_gib": 3600.0,
        "memory_bandwidth_gbps": 900.0,
        "metal": True,
        "cuda": False,
        "avx": False,
        "neon": True,
        "note": "Illustrative fixture for demos; not a measured machine.",
    },
    "linux-rtx-4090-24gb": {
        "name": "Mock Linux + RTX 4090 24GB",
        "os": "Linux",
        "arch": "x86_64",
        "cpu": "High-end desktop x86_64",
        "gpu": "NVIDIA RTX 4090",
        "unified_memory": False,
        "memory_total_gib": 128.0,
        "memory_available_gib": 100.0,
        "vram_total_gib": 24.0,
        "disk_available_gib": 1800.0,
        "memory_bandwidth_gbps": 1000.0,
        "metal": False,
        "cuda": True,
        "avx": True,
        "neon": False,
        "note": "Illustrative future-path fixture; not a measured machine.",
    },
    "linux-dual-h100-160gb": {
        "name": "Mock Linux + dual H100 160GB VRAM",
        "os": "Linux",
        "arch": "x86_64",
        "cpu": "Server x86_64",
        "gpu": "2x NVIDIA H100 80GB",
        "unified_memory": False,
        "memory_total_gib": 512.0,
        "memory_available_gib": 440.0,
        "vram_total_gib": 160.0,
        "disk_available_gib": 8000.0,
        "memory_bandwidth_gbps": 3200.0,
        "metal": False,
        "cuda": True,
        "avx": True,
        "neon": False,
        "note": "Illustrative future-path fixture; not a measured machine.",
    },
}


def list_fixture_names() -> list[str]:
    return sorted(BUILTIN_FIXTURES)


def get_fixture(name: str) -> dict[str, object]:
    key = name.removeprefix("fixture:").strip().lower()
    if key not in BUILTIN_FIXTURES:
        valid = ", ".join(list_fixture_names())
        raise ValueError(f"Unknown hardware fixture {name!r}. Valid fixtures: {valid}")
    return deepcopy(BUILTIN_FIXTURES[key])

