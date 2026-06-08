# local-llm-lab Recommendation

- Status: **recommended**
- Target: `tight`
- Backend: `llama.cpp`
- Quantization: `Q8_0`
- Context: `8192` tokens
- Verdict: **smooth** risk=low
- Runtime required: `78.93 GiB`
- Memory margin: `31.07 GiB`
- Estimated decode: `5.1 tok/s`

## Why

- Meets the requested target (tight) within the scanned quantization/context/backend matrix.
- Selected from 24 acceptable candidates out of 24 total plans.
- Estimated runtime memory margin is 31.07 GiB with 5.1 tok/s mid decode.

## Next Steps

- Generate the deploy dry-run files and run preflight before launching a real backend.
- Run a short benchmark after confirming the local model path and backend binary.

## Commands

```bash
python3 -m local_llm_lab deploy --model llama-3.3-70b --quant Q8_0 --ctx 8192 --backend llama.cpp --hardware fixture:apple-m4-max-128gb --out .local-llm-lab/deploy/llama-3.3-70b-q8_0-8192
```

## Alternatives

| Backend | Quant | Context | Verdict | Risk | Margin GiB | Decode tok/s |
| --- | --- | ---: | --- | --- | ---: | ---: |
| llama.cpp | Q8_0 | 4096 | smooth | low | 32.32 | 5.1 |
| llama.cpp | Q6_K | 32768 | smooth | low | 39.81 | 6.7 |
| llama.cpp | Q6_K | 16384 | smooth | low | 45.71 | 6.7 |
