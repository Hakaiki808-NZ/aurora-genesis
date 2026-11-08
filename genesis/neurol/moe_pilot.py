"""Research-only small sparse MoE: real expert dispatch, training and safe checkpoints.

This is an optional Genesis-side proof of concept for the trillion-capacity plan.
It does not grant Aurora permissions, enable Kyro inference, or allocate 1T weights.
Install optional `torch` and `safetensors` separately. No remote data or calls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from .core import encode
from .train import load_dataset, unigram_loss


def _torch_modules():
    try:
        import torch
        from torch import nn
        import torch.nn.functional as F
        from safetensors.torch import save_file, load_file
    except ImportError as exc:
        raise RuntimeError("Optional torch and safetensors are required for MoE research") from exc
    return torch, nn, F, save_file, load_file


def make_model():
    torch, nn, F, _, _ = _torch_modules()

    class SparseExperts(nn.Module):
        def __init__(self, width=64, intermediate=128, experts=4, topk=2):
            super().__init__()
            if type(experts) is not int or type(topk) is not int or not 1 <= topk <= experts <= 16:
                raise ValueError("invalid bounded routing configuration")
            self.experts = nn.ModuleList([
                nn.Sequential(nn.Linear(width, intermediate), nn.SiLU(), nn.Linear(intermediate, width))
                for _ in range(experts)
            ])
            self.router = nn.Linear(width, experts)
            self.topk = topk

        def forward(self, states):
            batch, length, width = states.shape
            flat = states.reshape(-1, width)
            probabilities = F.softmax(self.router(flat), dim=-1)
            _, choice = torch.topk(probabilities, self.topk, dim=-1)
            selected = torch.gather(probabilities, 1, choice)
            selected = selected / selected.sum(-1, keepdim=True)
            output = torch.zeros_like(flat)
            assignments = []
            # Only selected tokens are dispatched into each expert.
            for expert_index, expert in enumerate(self.experts):
                token_index, slot_index = (choice == expert_index).nonzero(as_tuple=True)
                assignments.append(int(token_index.numel()))
                if token_index.numel():
                    values = expert(flat.index_select(0, token_index))
                    output.index_add_(0, token_index, values*selected[token_index, slot_index, None])
            usage = probabilities.mean(0)
            balance = probabilities.shape[1]*((usage-1/probabilities.shape[1])**2).sum()
            return output.reshape(batch,length,width), balance, assignments

    class Pilot(nn.Module):
        def __init__(self):
            super().__init__()
            self.embedding = nn.Embedding(258,64)
            self.sequence = nn.GRU(64,64,batch_first=True)
            self.sparse = SparseExperts(64,128,4,2)
            self.norm = nn.LayerNorm(64)
            self.output = nn.Linear(64,258)

        def forward(self, ids):
            h, _ = self.sequence(self.embedding(ids))
            expert, balance, assignments = self.sparse(h)
            return self.output(self.norm(h+expert)), balance, assignments

    return Pilot()


def train_moe(dataset, output, report, *, steps=300, length=40, batch_size=8,
              rate=0.003, patience=5, seed=1907):
    torch, _, F, save_file, load_file = _torch_modules()
    if (type(steps) is not int or not 1 <= steps <= 2000
            or type(length) is not int or not 2 <= length <= 128
            or type(batch_size) is not int or not 1 <= batch_size <= 32
            or type(patience) is not int or not 1 <= patience <= 20
            or not 0 < rate <= 0.02 or type(seed) is not int or not 0 <= seed < 2**32):
        raise ValueError("invalid training parameters")
    splits, dataset_hash = load_dataset(dataset)
    torch.set_num_threads(2)
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed+1)
    model = make_model()
    parameters = sum(v.numel() for v in model.parameters())

    def eval_split(texts):
        model.eval()
        loss_sum, count = 0., 0
        assignments = np.zeros(4, dtype=np.int64)
        with torch.no_grad():
            for text in texts:
                ids = encode(text)
                x = torch.tensor([ids[:-1]],dtype=torch.long)
                y = torch.tensor(ids[1:],dtype=torch.long)
                logits, _, counts = model(x)
                loss_sum += float(F.cross_entropy(logits.reshape(-1,258),y.reshape(-1),reduction="sum"))
                count += y.numel()
                assignments += np.asarray(counts)
        model.train()
        return loss_sum/count, assignments.tolist()

    train_tokens = np.asarray([t for text in splits["train"] for t in encode(text)], dtype=np.int64)
    if len(train_tokens) <= length: raise ValueError("corpus too small for sequence length")
    first_val, _ = eval_split(splits["validation"])
    best_val, best_step, stalled = first_val, 0, 0
    best = {k: v.detach().clone() for k,v in model.state_dict().items()}
    opt = torch.optim.AdamW(model.parameters(),lr=rate,weight_decay=0.01)
    history = []
    started = time.monotonic()
    for step in range(1, steps+1):
        starts = rng.integers(0,len(train_tokens)-length,size=batch_size)
        seq = train_tokens[starts[:,None]+np.arange(length+1)]
        tokens = torch.tensor(seq,dtype=torch.long)
        logits, balancing, _ = model(tokens[:,:-1])
        loss = F.cross_entropy(logits.reshape(-1,258),tokens[:,1:].reshape(-1))
        opt.zero_grad(set_to_none=True)
        (loss+0.01*balancing).backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(),1.0)
        opt.step()
        if step % 25 == 0 or step == steps:
            val, assignments = eval_split(splits["validation"])
            history.append({"step":step,"train_loss":float(loss.detach()),"validation_loss":val,
                            "expert_assignments":assignments})
            if val < best_val-1e-4:
                best_val, best_step, stalled = val, step, 0
                best = {k:v.detach().clone() for k,v in model.state_dict().items()}
            else:
                stalled += 1
                if stalled >= patience: break
    model.load_state_dict(best)
    test_loss, assignments = eval_split(splits["test"])
    baseline = unigram_loss(splits["train"],splits["test"])
    passed = bool(best_step>0 and best_val < first_val*0.95 and test_loss < baseline
                  and all(x > 0 for x in assignments))
    path = Path(output)
    path.parent.mkdir(parents=True,exist_ok=True)
    save_file({k:v.detach().contiguous().cpu() for k,v in model.state_dict().items()},str(path))
    verified = load_file(str(path))
    if set(verified)!=set(model.state_dict()) or any(not torch.equal(verified[k],v.cpu())
                                                     for k,v in model.state_dict().items()):
        raise RuntimeError("safetensors checkpoint round-trip failed")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    result = {
        "stage": "sparse_moe_research_only", "learning_gate_passed": passed,
        "parameters":parameters,"expert_count":4,"experts_per_token":2,
        "initial_validation_loss":first_val,"best_validation_loss":best_val,
        "test_loss":test_loss,"unigram_test_baseline":baseline,
        "best_step":best_step,"steps_executed":step,"test_expert_assignments":assignments,
        "checkpoint_sha256":digest,"dataset_sha256":dataset_hash,
        "checkpoint_roundtrip_verified":True,"elapsed_seconds":round(time.monotonic()-started,3),
        "deployed":False,"training_during_chat":False,
        "limitations":"Small synthetic corpus; no evidence of fluent conversation or general reasoning.",
        "history":history,
    }
    report_path = Path(report)
    report_path.parent.mkdir(parents=True,exist_ok=True)
    report_path.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset",required=True)
    parser.add_argument("--output",required=True)
    parser.add_argument("--report",required=True)
    parser.add_argument("--steps",type=int,default=300)
    args=parser.parse_args()
    report=train_moe(args.dataset,args.output,args.report,steps=args.steps)
    print(json.dumps({k:v for k,v in report.items() if k != "history"}, indent=2))


if __name__ == "__main__":
    main()
