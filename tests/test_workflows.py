from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from local_llm_lab.bench import mock_benchmark
from local_llm_lab.deploy import generate_deploy_files
from local_llm_lab.hardware import detect_hardware
from local_llm_lab.planner import make_plan
from local_llm_lab.report import generate_report
from local_llm_lab.stress import mock_stress


class WorkflowTest(unittest.TestCase):
    def test_deploy_generates_expected_files(self) -> None:
        plan = make_plan(
            model_name="llama-3.3-70b",
            quant_name="Q4_K_M",
            context_tokens=8192,
            hardware_fixture="apple-m4-max-128gb",
        )
        with tempfile.TemporaryDirectory() as tmp:
            result = generate_deploy_files(plan, tmp)
            names = {Path(item).name for item in result.files}
            self.assertIn("run-llama-cpp.sh", names)
            self.assertIn("run-mlx.sh", names)
            self.assertIn("Modelfile", names)
            self.assertIn("run-ollama.sh", names)
            self.assertTrue(result.dry_run)

    def test_report_generation(self) -> None:
        plan = make_plan(
            params="600B",
            quant_name="Q4_K_M",
            context_tokens=32768,
            hardware_fixture="apple-m4-max-128gb",
        )
        bench = mock_benchmark(plan)
        stress = mock_stress(plan, bench)
        data = {"plan": plan.to_dict(), "bench": bench.to_dict(), "stress": stress.to_dict()}
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "demo.json"
            out = Path(tmp) / "report"
            source.write_text(json.dumps(data), encoding="utf-8")
            result = generate_report(source, out)
            self.assertTrue((out / "report.md").exists())
            self.assertTrue((out / "report.json").exists())
            self.assertTrue((out / "index.html").exists())
            self.assertTrue((out / "decode_tokens.svg").exists())
            self.assertIn(str(out / "index.html"), result["files"])

    def test_fixture_detection_has_no_sensitive_identifiers(self) -> None:
        profile = detect_hardware(skip_probes=True, fixture="apple-m4-max-128gb").to_dict()
        serialized = json.dumps(profile).lower()
        self.assertNotIn("serial", serialized)
        self.assertNotIn("uuid", serialized)
        self.assertNotIn("password", serialized)
        self.assertNotIn("token", serialized)


if __name__ == "__main__":
    unittest.main()

