from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from local_llm_lab.cli import main
from local_llm_lab.hardware import HardwareProfile, detect_hardware
from local_llm_lab.profiles import list_profiles, load_profile, save_profile


class ProfileTest(unittest.TestCase):
    def test_save_load_and_list_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"LOCAL_LLM_LAB_HOME": tmp}):
                profile = detect_hardware(skip_probes=True, fixture="apple-m4-max-128gb")
                path = save_profile("demo", profile, source="fixture:apple-m4-max-128gb")
                self.assertTrue(path.exists())

                loaded = load_profile("demo")
                self.assertEqual(loaded.name, profile.name)
                self.assertEqual(loaded.memory_total_gib, 128.0)

                profiles = list_profiles()
                self.assertEqual([item["name"] for item in profiles], ["demo"])
                self.assertEqual(profiles[0]["hardware_name"], profile.name)

    def test_profile_sanitizes_backend_paths_and_probe_errors(self) -> None:
        hardware = HardwareProfile(
            name="Private machine",
            os="macOS",
            arch="arm64",
            cpu="Apple Silicon",
            gpu="Apple GPU",
            unified_memory=True,
            memory_total_gib=128.0,
            memory_available_gib=100.0,
            disk_available_gib=900.0,
            metal=True,
            neon=True,
            backends={"ollama": "/Users/alice/bin/ollama", "vllm": None},
            probes={"disk_probe_error": "/Users/alice/tmp token=abc123"},
            note="local test",
        )
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"LOCAL_LLM_LAB_HOME": tmp}):
                path = save_profile("private", hardware, source="/Users/alice/project")
                serialized = path.read_text(encoding="utf-8")
                self.assertNotIn("/Users/alice", serialized)
                self.assertNotIn("abc123", serialized)
                data = json.loads(serialized)
                self.assertEqual(data["hardware"]["backends"]["ollama"], "found")
                self.assertEqual(data["hardware"]["probes"]["disk_probe_error"], "error redacted")

    def test_cli_profile_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"LOCAL_LLM_LAB_HOME": tmp}):
                out = io.StringIO()
                with redirect_stdout(out):
                    code = main(
                        [
                            "detect",
                            "--hardware",
                            "fixture:apple-m4-max-128gb",
                            "--skip-probes",
                            "--save-profile",
                            "demo",
                        ]
                    )
                self.assertEqual(code, 0)
                self.assertTrue((Path(tmp) / "profiles" / "demo.json").exists())

                out = io.StringIO()
                with redirect_stdout(out):
                    code = main(["list", "profiles"])
                self.assertEqual(code, 0)
                self.assertIn("demo", out.getvalue())

                out = io.StringIO()
                with redirect_stdout(out):
                    code = main(["profile", "show", "demo", "--json"])
                self.assertEqual(code, 0)
                shown = json.loads(out.getvalue())
                self.assertEqual(shown["profile_name"], "demo")

                out = io.StringIO()
                with redirect_stdout(out):
                    code = main(
                        [
                            "plan",
                            "--params",
                            "600B",
                            "--quant",
                            "Q4_K_M",
                            "--ctx",
                            "32768",
                            "--hardware",
                            "profile:demo",
                            "--json",
                        ]
                    )
                self.assertEqual(code, 0)
                planned = json.loads(out.getvalue())
                self.assertEqual(planned["inputs"]["hardware"]["name"], "Mock Apple Silicon Max-class 128GB")
                self.assertEqual(planned["verdict"], "does-not-fit")


if __name__ == "__main__":
    unittest.main()
