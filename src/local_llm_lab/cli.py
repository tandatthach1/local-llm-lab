from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from .bench import mock_benchmark, save_bench, tiny_local_benchmark
from .deploy import generate_deploy_files
from .fixtures import list_fixture_names
from .hardware import detect_hardware
from .models import list_presets
from .planner import make_plan
from .render import print_json, print_plan
from .report import generate_report
from .server import serve_directory
from .stress import mock_stress, save_stress


def _add_plan_args(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--model", help="Curated model preset, e.g. llama-3.3-70b")
    group.add_argument("--params", help="Free-form parameter count, e.g. 70B, 120B, 600B")
    parser.add_argument("--quant", default="Q4_K_M", help="Quantization, e.g. Q4_K_M, Q5_K_M, IQ2_XS")
    parser.add_argument("--ctx", type=int, default=8192, help="Context length in tokens")
    parser.add_argument("--concurrency", type=int, default=1, help="Concurrent sequences/requests")
    parser.add_argument("--backend", default="auto", help="auto, llama.cpp, mlx, ollama, vllm")
    parser.add_argument("--format", default=None, help="gguf, mlx, safetensors, hf")
    parser.add_argument("--hardware", default=None, help="Use fixture:name, e.g. fixture:apple-m4-max-128gb")
    parser.add_argument("--layers", type=int, default=None)
    parser.add_argument("--heads", type=int, default=None)
    parser.add_argument("--kv-heads", type=int, default=None)
    parser.add_argument("--head-dim", type=int, default=None)
    parser.add_argument("--kv-dtype-bytes", type=float, default=2.0)


def _plan_from_args(args: argparse.Namespace):
    if not args.model and not args.params:
        raise SystemExit("Either --model or --params is required.")
    hardware_fixture = None
    if args.hardware:
        hardware_fixture = args.hardware.removeprefix("fixture:")
    return make_plan(
        model_name=args.model,
        params=args.params,
        quant_name=args.quant,
        context_tokens=args.ctx,
        concurrency=args.concurrency,
        backend=args.backend,
        model_format=args.format,
        hardware_fixture=hardware_fixture,
        layers=args.layers,
        heads=args.heads,
        kv_heads=args.kv_heads,
        head_dim=args.head_dim,
        kv_dtype_bytes=args.kv_dtype_bytes,
    )


def cmd_detect(args: argparse.Namespace) -> int:
    fixture = args.hardware.removeprefix("fixture:") if args.hardware else None
    profile = detect_hardware(skip_probes=args.skip_probes, fixture=fixture)
    if args.json:
        print_json(profile.to_dict())
    else:
        print(f"Hardware: {profile.name}")
        print(f"CPU: {profile.cpu}")
        print(f"GPU: {profile.gpu}")
        print(f"Memory: {profile.memory_total_gib} GiB total, {profile.memory_available_gib} GiB available")
        print(f"Disk available: {profile.disk_available_gib} GiB")
        print(f"Capabilities: Metal={profile.metal} CUDA={profile.cuda} AVX={profile.avx} NEON={profile.neon}")
        if profile.backends:
            found = {key: value for key, value in profile.backends.items() if value}
            print(f"Backends found: {found if found else 'none'}")
        if profile.probes:
            print(f"Probes: {profile.probes}")
        if profile.note:
            print(f"Note: {profile.note}")
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    plan = _plan_from_args(args)
    if args.output:
        Path(args.output).write_text(json.dumps(plan.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    if args.json:
        print_json(plan.to_dict())
    else:
        print_plan(plan)
    return 0


def cmd_deploy(args: argparse.Namespace) -> int:
    plan = _plan_from_args(args)
    out = args.out or Path(".local-llm-lab") / "deploy" / f"{plan.inputs.model.id}-{plan.inputs.quant.name.lower()}"
    result = generate_deploy_files(plan, out, model_path=args.model_path, dry_run=not args.run)
    if args.json:
        print_json(result.to_dict())
    else:
        print(f"Generated deploy dry-run in {result.out_dir}")
        for item in result.files:
            print(f"- {item}")
        for warning in result.warnings:
            print(f"Warning: {warning}")
    return 0


def cmd_bench(args: argparse.Namespace) -> int:
    plan = None
    if args.model or args.params:
        plan = _plan_from_args(args)
    result = mock_benchmark(plan, seed=args.seed) if args.mock else tiny_local_benchmark()
    if args.output:
        save_bench(result, args.output)
    if args.json:
        print_json(result.to_dict())
    else:
        print(f"Benchmark: {result.kind} backend={result.backend} model={result.model}")
        for row in result.scenarios:
            print(f"- {row['name']}: decode={row['decode_tokens_s']} tok/s p95={row['p95_latency_s']}s")
        for note in result.notes:
            print(f"Note: {note}")
    return 0


def cmd_stress(args: argparse.Namespace) -> int:
    plan = None
    if args.model or args.params:
        plan = _plan_from_args(args)
    result = mock_stress(plan, seed=args.seed)
    if args.output:
        save_stress(result, args.output)
    if args.json:
        print_json(result.to_dict())
    else:
        print(f"Stress: {result.kind}")
        for row in result.scenarios:
            print(
                f"- {row['name']}: drop={row['throughput_drop_pct']}% "
                f"pressure={row['memory_pressure_ratio']} stability={row['stability']}"
            )
        for note in result.notes:
            print(f"Note: {note}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    result = generate_report(args.input, args.out)
    if args.json:
        print_json(result)
    else:
        print(f"Report generated in {result['out_dir']}")
        for item in result["files"]:
            print(f"- {item}")
    if args.serve:
        serve_directory(result["out_dir"], port=args.port)
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    plan = make_plan(
        params="600B",
        quant_name="Q4_K_M",
        context_tokens=32768,
        hardware_fixture="apple-m4-max-128gb",
    )
    bench = mock_benchmark(plan)
    stress = mock_stress(plan, bench)
    data = {"plan": plan.to_dict(), "bench": bench.to_dict(), "stress": stress.to_dict()}
    demo_json = out_dir / "demo-run.json"
    demo_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    report_dir = out_dir / "report"
    generate_report(demo_json, report_dir)
    if args.json:
        print_json({"demo_json": str(demo_json), "report_dir": str(report_dir)})
    else:
        print(f"Demo data: {demo_json}")
        print(f"Demo report: {report_dir / 'index.html'}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    if args.what == "models":
        for model in list_presets():
            print(f"{model.id}\t{model.family}\t{model.params_b}B\t{model.confidence}")
    else:
        for name in list_fixture_names():
            print(name)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="local-llm-lab", description="Honest local LLM planning and benchmarking.")
    sub = parser.add_subparsers(dest="command", required=True)

    detect = sub.add_parser("detect", help="Detect local hardware and backend capabilities.")
    detect.add_argument("--json", action="store_true")
    detect.add_argument("--skip-probes", action="store_true")
    detect.add_argument("--hardware", default=None, help="Use fixture:name instead of local detection.")
    detect.set_defaults(func=cmd_detect)

    plan = sub.add_parser("plan", help="Estimate whether a model can run locally.")
    _add_plan_args(plan)
    plan.add_argument("--json", action="store_true")
    plan.add_argument("--output")
    plan.set_defaults(func=cmd_plan)

    deploy = sub.add_parser("deploy", help="Generate dry-run deployment scripts/configs.")
    _add_plan_args(deploy)
    deploy.add_argument("--out")
    deploy.add_argument("--model-path", default="./model.gguf")
    deploy.add_argument("--run", action="store_true", help="Mark as non-dry-run; still does not download models.")
    deploy.add_argument("--json", action="store_true")
    deploy.set_defaults(func=cmd_deploy)

    bench = sub.add_parser("bench", help="Run mock or tiny local benchmark.")
    _add_plan_args(bench)
    bench.add_argument("--mock", action="store_true", default=False)
    bench.add_argument("--seed", default="local-llm-lab")
    bench.add_argument("--output")
    bench.add_argument("--json", action="store_true")
    bench.set_defaults(func=cmd_bench)

    stress = sub.add_parser("stress", help="Simulate LLM plus GPU/Blender-style resource competition.")
    _add_plan_args(stress)
    stress.add_argument("--mock", action="store_true", default=True)
    stress.add_argument("--seed", default="stress")
    stress.add_argument("--output")
    stress.add_argument("--json", action="store_true")
    stress.set_defaults(func=cmd_stress)

    report = sub.add_parser("report", help="Generate Markdown, JSON, SVG, and HTML report.")
    report.add_argument("--input", required=True)
    report.add_argument("--out", required=True)
    report.add_argument("--json", action="store_true")
    report.add_argument("--serve", action="store_true")
    report.add_argument("--port", type=int, default=8787)
    report.set_defaults(func=cmd_report)

    serve = sub.add_parser("serve", help="Serve a generated report directory on localhost.")
    serve.add_argument("--dir", required=True)
    serve.add_argument("--port", type=int, default=8787)
    serve.set_defaults(func=lambda args: serve_directory(args.dir, port=args.port) or 0)

    demo = sub.add_parser("demo", help="Create reproducible demo data and report.")
    demo.add_argument("--out", default="examples")
    demo.add_argument("--json", action="store_true")
    demo.set_defaults(func=cmd_demo)

    listing = sub.add_parser("list", help="List model presets or hardware fixtures.")
    listing.add_argument("what", choices=["models", "hardware"])
    listing.set_defaults(func=cmd_list)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())

