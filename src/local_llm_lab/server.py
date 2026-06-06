from __future__ import annotations

import functools
import html
import http.server
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


def _load_json(path: Path) -> dict[str, object] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _fmt(value: object, fallback: str = "unknown") -> str:
    if value is None or value == "":
        return fallback
    return str(value)


def _report_card(root: Path, directory: Path) -> dict[str, object] | None:
    index = directory / "index.html"
    compare_json = directory / "compare.json"
    report_json = directory / "report.json"
    if compare_json.exists():
        data = _load_json(compare_json)
        compare = data.get("compare", {}) if data else {}
        request = compare.get("request", {}) if isinstance(compare, dict) else {}
        summary = compare.get("summary", {}) if isinstance(compare, dict) else {}
        best = summary.get("best", {}) if isinstance(summary, dict) else {}
        return {
            "kind": "compare",
            "title": _fmt(request.get("model") or request.get("params"), directory.name) if isinstance(request, dict) else directory.name,
            "subtitle": _fmt(request.get("hardware") if isinstance(request, dict) else None),
            "verdict": _fmt(best.get("verdict") if isinstance(best, dict) else None),
            "risk": _fmt(best.get("risk_level") if isinstance(best, dict) else None),
            "metric": f"{_fmt(best.get('quantization') if isinstance(best, dict) else None)} / {_fmt(best.get('context_tokens') if isinstance(best, dict) else None)} ctx",
            "detail": f"{_fmt(best.get('backend') if isinstance(best, dict) else None)} · {_fmt(best.get('decode_tokens_s_mid') if isinstance(best, dict) else None)} tok/s",
            "href": index.relative_to(root).as_posix() if index.exists() else compare_json.relative_to(root).as_posix(),
            "json": compare_json.relative_to(root).as_posix(),
            "mtime": directory.stat().st_mtime,
        }
    if report_json.exists():
        data = _load_json(report_json)
        plan = data.get("plan", {}) if data else {}
        inputs = plan.get("inputs", {}) if isinstance(plan, dict) else {}
        model = inputs.get("model", {}) if isinstance(inputs, dict) else {}
        hardware = inputs.get("hardware", {}) if isinstance(inputs, dict) else {}
        memory = plan.get("memory", {}) if isinstance(plan, dict) else {}
        bench = data.get("bench", {}) if data else {}
        scenarios = bench.get("scenarios", []) if isinstance(bench, dict) else []
        decode = None
        if isinstance(scenarios, list) and scenarios:
            first = scenarios[0]
            if isinstance(first, dict):
                decode = first.get("decode_tokens_s")
        return {
            "kind": "report",
            "title": _fmt(model.get("id") if isinstance(model, dict) else None, directory.name),
            "subtitle": _fmt(hardware.get("name") if isinstance(hardware, dict) else None),
            "verdict": _fmt(plan.get("verdict") if isinstance(plan, dict) else None),
            "risk": _fmt(plan.get("risk_level") if isinstance(plan, dict) else None),
            "metric": f"{_fmt(memory.get('margin_gib') if isinstance(memory, dict) else None)} GiB margin",
            "detail": f"{_fmt(decode)} tok/s short prompt",
            "href": index.relative_to(root).as_posix() if index.exists() else report_json.relative_to(root).as_posix(),
            "json": report_json.relative_to(root).as_posix(),
            "mtime": directory.stat().st_mtime,
        }
    return None


def render_report_hub(root: Path) -> str | None:
    cards = []
    for child in sorted(root.iterdir()) if root.exists() else []:
        if child.is_dir():
            card = _report_card(root, child)
            if card:
                cards.append(card)
    if not cards:
        return None
    cards.sort(key=lambda item: float(item["mtime"]), reverse=True)
    body = "\n".join(_render_card(card) for card in cards)
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>local-llm-lab Report Hub</title>
  <style>
    :root {{ color: #111827; background: #f5f6f8; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    body {{ margin: 0; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 32px 20px 56px; }}
    h1 {{ margin: 0; font-size: 36px; letter-spacing: 0; }}
    .subtle {{ color: #5f6876; margin: 8px 0 24px; }}
    .top {{ display: flex; justify-content: space-between; gap: 16px; align-items: end; flex-wrap: wrap; }}
    .pill {{ display: inline-flex; align-items: center; border: 1px solid #d4dae6; background: #fff; border-radius: 999px; padding: 7px 12px; color: #374151; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }}
    article {{ background: #fff; border: 1px solid #d8dee9; border-radius: 8px; padding: 16px; }}
    article:hover {{ border-color: #9aa6b8; }}
    h2 {{ margin: 8px 0 6px; font-size: 20px; letter-spacing: 0; }}
    a {{ color: inherit; text-decoration: none; }}
    .meta {{ color: #667085; font-size: 13px; margin: 0 0 14px; }}
    .row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 12px 0; }}
    .metric {{ border: 1px solid #edf0f5; border-radius: 8px; padding: 9px; background: #fafbfc; }}
    .label {{ color: #6b7280; font-size: 11px; text-transform: uppercase; }}
    strong {{ display: block; margin-top: 4px; overflow-wrap: anywhere; }}
    .badge {{ display: inline-block; border-radius: 999px; padding: 4px 9px; font-size: 12px; font-weight: 700; }}
    .smooth, .low {{ color: #065f46; background: #d1fae5; }}
    .tight, .medium {{ color: #92400e; background: #fef3c7; }}
    .not-recommended, .high {{ color: #991b1b; background: #fee2e2; }}
    .does-not-fit, .extreme {{ color: #7f1d1d; background: #fecaca; }}
    .links {{ display: flex; gap: 10px; margin-top: 14px; }}
    .links a {{ border: 1px solid #cfd6e3; border-radius: 6px; padding: 7px 10px; background: #fff; color: #1f2937; }}
  </style>
</head>
<body>
<main>
  <div class="top">
    <div>
      <h1>local-llm-lab Report Hub</h1>
      <p class="subtle">Local-only index for generated planning, benchmark, stress, and compare reports.</p>
    </div>
    <span class="pill">{len(cards)} reports · generated {html.escape(generated)}</span>
  </div>
  <section class="grid">{body}</section>
</main>
</body>
</html>
"""


def _render_card(card: dict[str, object]) -> str:
    kind = html.escape(str(card["kind"]))
    title = html.escape(str(card["title"]))
    subtitle = html.escape(str(card["subtitle"]))
    verdict = html.escape(str(card["verdict"]))
    risk = html.escape(str(card["risk"]))
    metric = html.escape(str(card["metric"]))
    detail = html.escape(str(card["detail"]))
    href = html.escape(str(card["href"]), quote=True)
    json_href = html.escape(str(card["json"]), quote=True)
    return f"""
    <article>
      <span class="pill">{kind}</span>
      <a href="{href}"><h2>{title}</h2></a>
      <p class="meta">{subtitle}</p>
      <div class="row">
        <div class="metric"><span class="label">Verdict</span><strong><span class="badge {verdict}">{verdict}</span></strong></div>
        <div class="metric"><span class="label">Risk</span><strong><span class="badge {risk}">{risk}</span></strong></div>
        <div class="metric"><span class="label">Best setting</span><strong>{metric}</strong></div>
        <div class="metric"><span class="label">Performance</span><strong>{detail}</strong></div>
      </div>
      <div class="links"><a href="{href}">Open report</a><a href="{json_href}">JSON</a></div>
    </article>
    """


class ReportHubHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args: object, directory: str, hub_html: str | None, **kwargs: object) -> None:
        self._hub_html = hub_html
        super().__init__(*args, directory=directory, **kwargs)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if self._hub_html and path in {"/", "/index.html"}:
            payload = self._hub_html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        super().do_GET()


def serve_directory(directory: str | Path, *, host: str = "127.0.0.1", port: int = 8787) -> None:
    root = Path(directory).resolve()
    hub_html = None if (root / "index.html").exists() else render_report_hub(root)
    handler = functools.partial(ReportHubHandler, directory=str(root), hub_html=hub_html)
    with http.server.ThreadingHTTPServer((host, port), handler) as httpd:
        print(f"Serving {root} at http://{host}:{port}/")
        httpd.serve_forever()
