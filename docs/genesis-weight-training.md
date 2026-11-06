# Genesis model-weights programme — initial AWS CPU baseline

## Status
Phase 0: experimental weights training and checkpointing. This is a small neural-network demonstration, **not** a trained general-purpose language model or evidence of AGI.

## Architecture
The Genesis cognitive model owns semantic processing; Aurora owns execution control. The first experiment is deliberately isolated from Aurora's protected runtime. Kyro will not serve these toy weights to end users.

## AWS job
- Region: `ap-southeast-2`
- Service: AWS Lambda (Python 3.12, short CPU-only on-demand job)
- Source: `genesis/training/aws_lambda_baseline.py`
- Checkpoint: `s3://<project-artifact-bucket>/genesis/weights/char-mlp-v0/*.json.gz`
- Security: dedicated execution role, only CloudWatch log write and S3 PutObject under checkpoint prefix
- Bounds: 4 epochs, 3,500 training characters maximum, no internet downloads, no GPUs, one short invocation
- Training data: original synthetic project-specific sentences; no private user data

The character-level neural network predicts the next character from the previous two, using an 8-dimensional embedding, 20-unit tanh hidden layer and softmax. Training uses stochastic gradient descent and evaluates cross-entropy on distinct validation sentences. It has about 1,123 learnable parameters.

## Validate the run
Check Lambda invocation response for `trained=true`, `checkpoint_saved=true`, parameter count and decreasing validation loss. Independently inspect S3 with `HeadObject` and confirm the checkpoint SHA-256. A falling training/validation loss here proves the code can update parameters on this miniature dataset only. It does not establish useful language ability.

## Next steps / milestones
1. Define licensed, documented, deduplicated datasets and held-out evaluations.
2. Select an open-weight pretrained model with a compatible license rather than pretraining a competitive LLM from scratch.
3. Obtain and verify an AWS cost allowance, approved GPU training quota and least-privilege SageMaker role.
4. Add parameter-efficient fine-tuning (LoRA/QLoRA), proper tokenizer and ML checkpoint formats.
5. Gate promotion on safety, regression, generalization, memory and tool-use evaluations.
6. Keep Aurora/Genesis security boundaries independent of model-generated instructions.

**Cost:** AWS Budgets alerts do not cap spend. Do not launch GPU training until an explicit maximum cost and stop mechanism are configured.
