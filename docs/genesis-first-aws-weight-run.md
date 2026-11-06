# Genesis first AWS weight-training checkpoint

**Date:** 2026-11-07 NZDT  
**Status:** First AWS training proof completed successfully  
**Environment:** AWS Sydney (`ap-southeast-2`), experimental development

## Verified result

- Trainer: `genesis/training/aws_lambda_baseline.py`
- Lambda function: `genesis-weights-pretrain-dev`
- Provisioning stack: `genesis-weights-baseline-dev` (`CREATE_COMPLETE`)
- Compute: Python 3.12 on AWS Lambda, 256 MB, 60-second timeout, on-demand, no trigger
- Model: 2-character-context neural language model (embedding + tanh hidden layer + softmax)
- Trainable weights: **1,123**
- Vocabulary size: 27 characters
- Training epochs: 4
- Validation cross-entropy: **3.29558 → 1.73859**
- Checkpoint length (S3 HeadObject): **11,642 bytes**
- Artifact key: `genesis/weights/char-mlp-v0/genesis-char-mlp-v0-a92999b01204795c.json.gz`
- Artifact SHA-256 reported and stored in S3 metadata: `a92999b01204795c47dc64b5eec9ed21c65b5e8910d073db71ce64a843bd89d0`
- S3 server-side encryption: AES256
- CloudWatch log retention: 7 days

### Per-epoch validation loss

| Epoch | Loss |
|---|---:|
| Before training | 3.29558 |
| 1 | 2.67123 |
| 2 | 2.23086 |
| 3 | 1.92665 |
| 4 | 1.73859 |

## Interpretation

This confirms a bounded AWS training job updated the parameters of a tiny neural model and saved a private checkpoint in S3. It **does not** show transferable language understanding, general reasoning, AGI, or production model quality. The source corpus is small and synthetic. Further training must be evaluated against genuinely held-out, broad, licensed datasets.

## Next gate

Do not start GPU-based fine-tuning until an explicit cost allowance, permissions and quota exist. The AWS account currently has a US$1 budget alert; an alert is **not** a spending limit. Select an appropriately licensed pretrained base model, set up a reproducible LoRA/QLoRA training pipeline and safety evaluation, and maintain Aurora/Genesis trust boundaries.
