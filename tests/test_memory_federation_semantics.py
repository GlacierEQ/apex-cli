from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core import memory_connect_core as memory


class MemoryFederationSemanticsTests(unittest.TestCase):
    def test_partial_provider_failure_is_degraded_not_blocked(self):
        state = memory.classify_federation_state(
            True,
            {
                "mem0": {"ok": True},
                "supermemory": {"ok": False, "error": "offline"},
                "memory_plugin": {"ok": True},
            },
        )
        self.assertEqual(state, "DEGRADED")

    def test_all_semantic_providers_down_preserves_local_state(self):
        state = memory.classify_federation_state(
            True,
            {
                "mem0": {"ok": False},
                "supermemory": {"ok": False},
                "memory_plugin": {"ok": False},
            },
        )
        self.assertEqual(state, "LOCAL_ONLY")

    def test_canonical_failure_is_the_only_canonical_failure_state(self):
        self.assertEqual(
            memory.classify_federation_state(False, {"mem0": {"ok": True}}),
            "FAILED_CANONICAL",
        )

    def test_canonical_commit_preserves_full_content_and_readback_hash(self):
        content = "x" * (memory.MAX_FACT_LENGTH + 4096)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with (
                patch.object(memory, "CANONICAL_MEMORY_DIR", root / "objects"),
                patch.object(memory, "CANONICAL_MEMORY_LEDGER", root / "ledger.jsonl"),
                patch.object(memory, "PROVIDER_REPAIR_QUEUE", root / "repair.jsonl"),
            ):
                receipt = memory.canonical_commit(content, source_id="test")
                self.assertTrue(receipt["ok"])
                self.assertTrue(receipt["verified_readback"])
                self.assertEqual(receipt["byte_count"], len(content.encode("utf-8")))
                obj = json.loads(Path(receipt["object_path"]).read_text(encoding="utf-8"))
                self.assertEqual(obj["content"], content)
                self.assertEqual(obj["sha256"], receipt["sha256"])

    def test_provider_unanimity_is_not_encoded_as_liveness_requirement(self):
        self.assertNotEqual(
            memory.classify_federation_state(
                True,
                {"memory_plugin": {"ok": False, "error": "offline"}},
            ),
            "FAILED_CANONICAL",
        )


if __name__ == "__main__":
    unittest.main()
