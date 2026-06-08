from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from local_llm_lab.compare import CompareRequest
from local_llm_lab.hardware import detect_hardware
from local_llm_lab.profiles import save_profile
from local_llm_lab.recommend import RecommendRequest, recommend_plans, write_recommend_outputs


class RecommendTest(unittest.TestCase):
    def test_recommend_70b_on_128gb_returns_runnable_candidate(self) -> None:
        result = recommend_plans(
            RecommendRequest(
                CompareRequest(
                    model_name="llama-3.3-70b",
                    params=None,
                    quantizations=["Q6_K", "Q4_K_M"],
                    contexts=[4096, 8192],
                    backends=["auto"],
                    concurrency=1,
                    model_format=None,
                    hardware_fixture="apple-m4-max-128gb",
                )
            )
        )
        rec = result["recommendation"]
        self.assertEqual(rec["status"], "recommended")
        self.assertIn(rec["best"]["verdict"], {"smooth", "tight"})
        self.assertIn("python3 -m local_llm_lab deploy", rec["deploy_command"])
        self.assertGreater(len(rec["why"]), 0)

    def test_recommend_600b_on_128gb_returns_no_fit(self) -> None:
        result = recommend_plans(
            RecommendRequest(
                CompareRequest(
                    model_name=None,
                    params="600B",
                    quantizations=["Q4_K_M", "IQ2_XS"],
                    contexts=[8192, 32768],
                    backends=["auto"],
                    concurrency=1,
                    model_format=None,
                    hardware_fixture="apple-m4-max-128gb",
                )
            )
        )
        rec = result["recommendation"]
        self.assertEqual(rec["status"], "no-fit")
        self.assertIn(rec["best"]["verdict"], {"not-recommended", "does-not-fit"})
        self.assertTrue(rec["downgrade_options"])

    def test_recommend_supports_saved_profile_and_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"LOCAL_LLM_LAB_HOME": tmp}):
                profile = detect_hardware(skip_probes=True, fixture="apple-m4-max-128gb")
                save_profile("demo", profile, source="fixture:apple-m4-max-128gb")
                result = recommend_plans(
                    RecommendRequest(
                        CompareRequest(
                            model_name="llama-3.3-70b",
                            params=None,
                            quantizations=["Q4_K_M"],
                            contexts=[8192],
                            backends=["auto"],
                            concurrency=1,
                            model_format=None,
                            hardware_fixture=None,
                            hardware_profile=profile,
                            hardware_label="profile:demo",
                        )
                    )
                )
                self.assertIn("--hardware profile:demo", result["recommendation"]["recommend_command"])
                out = Path(tmp) / "recommend"
                written = write_recommend_outputs(result, out)
                self.assertTrue((out / "recommend.json").exists())
                self.assertTrue((out / "recommend.md").exists())
                loaded = json.loads((out / "recommend.json").read_text(encoding="utf-8"))
                self.assertEqual(loaded["recommendation"]["status"], "recommended")
                self.assertIn(str(out / "recommend.md"), written["files"])


if __name__ == "__main__":
    unittest.main()
