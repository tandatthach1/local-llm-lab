# local-llm-lab

**Can my 128GB Mac run this 600B model?**

local-llm-lab gives you the uncomfortable answer before you waste a weekend downloading weights.

```bash
python3 -m local_llm_lab plan \
  --params 600B \
  --quant Q4_K_M \
  --ctx 32768 \
  --hardware fixture:apple-m4-max-128gb
```

```text
VERDICT: DOES-NOT-FIT  risk=extreme  confidence=demo
Model: custom-600b (600B, dense)
Hardware: Mock Apple Silicon Max-class 128GB | memory=128 GiB | available=110 GiB
Backend: llama.cpp | Quantization: Q4_K_M
Weights: 325 GiB
KV cache: 32.0 GiB
Runtime required: 377 GiB
Available runtime memory: 110 GiB
Margin: -267 GiB
Estimated decode: 0.18-0.38 tokens/s
Recommended quantization: no-safe-local-quant
Downgrade options:
  - No supported quantization fits safely at this context on this hardware.
  - Consider remote inference, hybrid/offloaded inference, or a smaller distilled model.
  - For 600B+ models, avoid local-only deployment unless you have measured headroom.
```

It is a lightweight CLI for local LLM planning, dry-run deployment, benchmarking, stress simulation, and report generation. It is built for developers with 64GB, 128GB, 192GB, and 256GB unified-memory machines, especially Apple Silicon Max/Ultra users, with Linux + NVIDIA support as a future expansion path.

## What it does

- Detect local hardware: OS, CPU/GPU, unified memory/VRAM, disk, Metal/CUDA/AVX/NEON, backend binaries.
- Plan whether a model fits: weights, KV cache, overhead, OS reserve, margin, verdict, risk, backend, quantization.
- Deploy without downloading huge models: generate llama.cpp, MLX, and Ollama dry-run scripts/configs.
- Benchmark with deterministic mock data or tiny local smoke checks.
- Stress-test resource contention with reproducible LLM + Blender/GPU-style simulations.
- Report in Markdown, JSON, SVG charts, and static HTML.
- Serve reports locally with a localhost-only Web viewer.

## Install

Run from source without installing:

```bash
git clone https://github.com/duongngocbinh56599-ui/local-llm-lab.git
cd local-llm-lab
python3 -m local_llm_lab --help
```

Install editable:

```bash
python3 -m pip install -e .
local-llm-lab --help
```

Optional enhancements:

```bash
python3 -m pip install -e ".[ui]"      # Rich terminal tables
python3 -m pip install -e ".[detect]"  # psutil-assisted telemetry
python3 -m pip install -e ".[charts]"  # matplotlib chart exports
python3 -m pip install -e ".[all]"
```

The core CLI has no required third-party dependencies.

## Quick demo

Create demo data and a local HTML report:

```bash
python3 -m local_llm_lab demo --out examples
python3 -m local_llm_lab serve --dir examples/report --port 8787
```

Then open `http://127.0.0.1:8787/`.

## Commands

### detect

```bash
python3 -m local_llm_lab detect
python3 -m local_llm_lab detect --json --skip-probes
python3 -m local_llm_lab detect --hardware fixture:apple-m4-ultra-256gb
```

Hardware detection redacts sensitive identifiers. It does not write serial numbers, hardware UUIDs, account names, tokens, or credentials.

### plan

Use `--model` for curated presets:

```bash
python3 -m local_llm_lab plan --model llama-3.3-70b --quant Q4_K_M --ctx 8192
```

Use `--params` for unknown, private, future, or hypothetical models:

```bash
python3 -m local_llm_lab plan --params 120B --quant Q5_K_M --ctx 16384
python3 -m local_llm_lab plan --params 600B --quant Q4_K_M --ctx 32768 --hardware fixture:apple-m4-max-128gb
```

Override architecture details when you know them:

```bash
python3 -m local_llm_lab plan \
  --params 200B \
  --layers 112 \
  --heads 96 \
  --kv-heads 12 \
  --head-dim 128 \
  --quant Q4_K_M \
  --ctx 16384
```

### deploy

```bash
python3 -m local_llm_lab deploy \
  --model llama-3.3-70b \
  --quant Q4_K_M \
  --ctx 8192 \
  --out .local-llm-lab/deploy/llama70b
```

This writes:

- `local-llm-lab-plan.json`
- `run-llama-cpp.sh`
- `run-mlx.sh`
- `Modelfile`
- `run-ollama.sh`

It does not download model weights.

### bench

```bash
python3 -m local_llm_lab bench --mock --model llama-3.3-70b --quant Q4_K_M --ctx 8192
python3 -m local_llm_lab bench --mock --output examples/bench.json
```

Mock mode is deterministic demo data. Real backend benchmark support will expand in v0.2.

### stress

```bash
python3 -m local_llm_lab stress --model llama-3.3-70b --quant Q4_K_M --ctx 8192
```

v0.1 simulates LLM inference competing with viewport rendering, Blender preview, and generic GPU pressure. It is safe by default and does not launch heavy GPU workloads.

### report

```bash
python3 -m local_llm_lab report --input examples/demo-run.json --out sample_reports/demo
python3 -m local_llm_lab serve --dir sample_reports/demo --port 8787
```

Reports include Markdown, JSON, static HTML, and SVG charts. If `matplotlib` is installed, PNG charts are added.

## Model presets

Curated v0.1 presets include:

- Llama: `llama-3.1-8b`, `llama-3.3-70b`, `llama-3.1-405b`
- Qwen: `qwen2.5-32b`, `qwen2.5-72b`, `qwen3-235b-a22b`
- DeepSeek: `deepseek-v3-671b-a37b`
- Mixtral: `mixtral-8x7b`, `mixtral-8x22b`
- Gemma: `gemma-3-27b`
- Phi: `phi-4-14b`
- Generic planning profiles: `generic-70b`, `generic-120b`, `generic-200b`, `generic-400b`, `generic-600b`

List them:

```bash
python3 -m local_llm_lab list models
```

## Hardware fixtures

Fixtures are illustrative demo profiles, not measured machines:

```bash
python3 -m local_llm_lab list hardware
```

They let anyone reproduce 64GB/128GB/192GB/256GB unified-memory reports without owning those machines.

## Estimation model

local-llm-lab uses explicit, inspectable formulas:

```text
weights = params * quant_effective_bytes_per_param * format_overhead
kv_cache = ctx * concurrency * layers * kv_heads * head_dim * 2(K,V) * kv_dtype_bytes
runtime_required = weights + kv_cache + activation + backend_overhead
total_required = runtime_required + os_reserve
```

These are estimates. Backend kernels, model architecture, tokenizer behavior, prompt shape, thermal state, and memory pressure can move real results. The CLI labels low-confidence inputs and recommends validation benchmarks.

## Roadmap

v0.1:

- Honest planning for `--model` and `--params`
- Dry-run deploy generation for llama.cpp, MLX, Ollama
- Mock bench/stress data
- Markdown/JSON/SVG/HTML reports
- Local report server

v0.2:

- Real backend adapters for llama.cpp, Ollama, MLX
- Better Linux + NVIDIA detection through `nvidia-smi`
- Backend-specific context/batch/offload planning
- Community benchmark fixture submissions
- Optional Web panel controls

## License

MIT
