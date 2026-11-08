"""Optional sparse MoE pilot tests; skipped if PyTorch / SafeTensors are absent."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

MISSING = importlib.util.find_spec("torch") is None or importlib.util.find_spec("safetensors") is None


@unittest.skipIf(MISSING, "requires optional research dependencies")
class SparseMoEPilotTests(unittest.TestCase):
    def test_sparse_top_two_routes_and_backward(self):
        import torch
        from genesis.neurol.moe_pilot import make_model

        torch.set_num_threads(2)
        torch.manual_seed(1907)
        model = make_model()
        self.assertEqual(sum(p.numel() for p in model.parameters()), 124_934)
        inputs = torch.tensor([[256,65,66,67],[256,67,66,65]], dtype=torch.long)
        logits, balance, counts = model(inputs)
        self.assertEqual(logits.shape, (2,4,258))
        self.assertEqual(sum(counts), 2*inputs.numel())
        self.assertTrue(all(c >= 0 for c in counts))
        self.assertTrue(torch.isfinite(logits).all())
        self.assertTrue(torch.isfinite(balance))
        (logits.square().mean()+0.01*balance).backward()
        self.assertTrue(any(p.grad is not None for p in model.sparse.router.parameters()))
        self.assertTrue(all(any(p.grad is not None for p in expert.parameters())
                            for expert, count in zip(model.sparse.experts, counts) if count))

    def test_short_training_is_checkpointed_without_deployment(self):
        from genesis.neurol.moe_pilot import train_moe
        from safetensors.torch import load_file
        with tempfile.TemporaryDirectory() as tmp:
            weights = Path(tmp)/"pilot.safetensors"
            report_path = Path(tmp)/"pilot-report.json"
            corpus = Path(__file__).resolve().parents[1]/"examples/neurol/corpus.json"
            report = train_moe(corpus,weights,report_path,steps=2)
            self.assertEqual(report["stage"], "sparse_moe_research_only")
            self.assertEqual(report["parameters"], 124_934)
            self.assertFalse(report["deployed"])
            self.assertFalse(report["training_during_chat"])
            self.assertTrue(report["checkpoint_roundtrip_verified"])
            self.assertEqual(hashlib.sha256(weights.read_bytes()).hexdigest(),report["checkpoint_sha256"])
            self.assertTrue(load_file(str(weights)))
            self.assertEqual(json.loads(report_path.read_text())["checkpoint_sha256"],report["checkpoint_sha256"])


if __name__ == "__main__":
    unittest.main()
