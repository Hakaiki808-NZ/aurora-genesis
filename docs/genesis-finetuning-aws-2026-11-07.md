# Genesis AWS Fine-Tuning — 7 November 2026

## Current milestones

1. **Verified CPU weight continuation:** one AWS Lambda asynchronous job trained from the previous Genesis v0 char-MLP checkpoint and saved its updated weights privately in S3. This is a tiny 1,123-parameter proof of the training mechanism, **not** an operational large language model.
2. **GPU QLoRA pipeline staged:** a new real language-model fine-tuning pipeline based on Apache-2.0 Qwen/Qwen2.5-0.5B-Instruct is in GitHub, using 51 original example instruction/response pairs, a fixed random seed, masked prompt labels, held-out validation, LoRA rank 8 and NF4 4-bit quantization.
3. **AWS GPU access requested:** EC2 G-family Spot and On-Demand quotas both requested at 4 vCPUs in Sydney. They are **not yet approved**.
4. **Quota-gated AWS watchdog:** deploy an EventBridge-scheduled Lambda that checks quotas, launches exactly **one** disposable g4dn.xlarge GPU job only after approval, records a conditional S3 launch lock, and terminates the tagged training instance after at most 3 hours. AWS EC2 must still be monitored independently for actual billing.

## CPU continuation verified

- AWS Lambda: `genesis-weights-continuation-dev`
- Runtime: Python 3.12, 256 MB, 90-second maximum per invocation
- Initial held-out loss on new sentences: 2.52513
- Final held-out loss on new sentences: 2.07338
- Original held-out loss: 1.75394 before; 1.76554 after (slight regression)
- Fine-tuned checkpoint: 11,736 bytes, SSE-S3 AES256
- SHA-256: `a951b3570e56def385f730ffe6f38ef761280f914e20cef0bd5a9ef73fc43f58`
- Checkpoint key: `genesis/weights/char-mlp-v0-finetuned/genesis-finetune-a951b3570e56def3.json.gz`
- AWS confirmed the object via S3 HeadObject.

## GPU run details

- Base model: `Qwen/Qwen2.5-0.5B-Instruct` (Apache-2.0); **not our original foundation weights**. Fine-tuning creates a Genesis LoRA adapter.
- Project entrypoint: `genesis/training/finetune_qlora.py`
- Data: `genesis/training/data/genesis_sft_v0.jsonl`
- Dependencies: `genesis/training/requirements_qlora.txt`
- Bootstrap: `tools/aws/run_genesis_qlora.sh`
- Quota watcher: `tools/aws/genesis_gpu_watcher.py`
- Region: `ap-southeast-2`
- AWS DLAMI: GPU PyTorch 2.6 Ubuntu 22.04. Instance: single `g4dn.xlarge` with NVIDIA T4 16 GiB GPU
- Private output prefix: `genesis/finetune/qwen2p5-0p5b-v0/` in the project artifacts S3 bucket
- One run only. LoRA rank 8, up to 80 optimizer steps, default 60 steps. Validation is held out from the small dataset. No claim of broad task transfer, safety or AGI.
- If the account's quota permits, use Spot first with **US$1.00/hour maximum Spot bid**; otherwise on-demand if approved. Current observed on-demand listing was approximately US$0.68/hour in Sydney.
- Software training time limit: 9,000 seconds (2.5 hours).
- Instance shutdown timer: 180 minutes (3 hours), set to **terminate**.
- Separate AWS watchdog: terminates the uniquely tagged instance at 3 hours; checks every 15 minutes.
- EBS: one encrypted 50-GiB gp3 root volume with deletion on termination.
- Network: no inbound security-group rules; HTTPS (443) outbound only; IMDSv2 required.
- Controller/instance IAM roles: narrowly scoped to one training run, role passing, and private S3 artifacts.
- Automatic quota polling expires **2026-11-15 00:00 UTC** if a GPU quota is not approved.

## Spending authorization

Maximum approved extra expenditure: **US$30**. This design deliberately targets a much smaller run (roughly US$1–5 of compute and minor storage/IPv4/log charges under quoted rates), **not** a US$30 open-ended service. AWS Budgets alerts are not a hard spend cap; independent timeout, watchdog and one-run lock are the practical controls. Existing unrelated AWS usage is outside the new training-job estimate and may continue generating charges. Check the actual bill after the run.

## Completion gates

- Confirm CloudFormation stack CREATE_COMPLETE and the EventBridge rule target.
- Confirm quota increase and EC2 instance state before saying GPU training has started.
- Verify adapters and `metrics.json` in S3 after EC2 terminates.
- Independently test the base model and adapter on unseen prompts and regression/safety tasks before exposing through Kyro.
- Keep Aurora operational authorization completely separate from model weights.
