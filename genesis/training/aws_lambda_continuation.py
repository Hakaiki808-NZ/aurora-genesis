# Concatenate after aws_lambda_baseline.py when packaging this Lambda.
# A separate bounded continuation run loads the previous AWS checkpoint,
# updates the learned parameters and writes a new checkpoint.
PREVIOUS_CHECKPOINT = (
    "genesis/weights/char-mlp-v0/"
    "genesis-char-mlp-v0-a92999b01204795c.json.gz"
)
EXPECTED_BASE_SHA256 = (
    "a92999b01204795c47dc64b5eec9ed21c65b5e8910d073db71ce64a843bd89d0"
)
CONTINUATION_LINES = [
    "evidence should change a belief when verified facts are different.",
    "do not claim a deployment succeeded without confirmation.",
    "a model output is not an engine permission.",
    "uncertainty is important when information is missing.",
    "observations and predictions should be clearly separated.",
    "genesis can learn from mistakes without changing engine authority.",
    "review new evidence and update an interpretation carefully.",
    "training loss alone does not prove general reasoning ability.",
]
CONTINUATION_VALIDATION = [
    "genesis checks information before drawing conclusions.",
    "uncertain observations should not be reported as proven facts.",
]


def continuation_run(event):
    import boto3
    bucket = os.environ["GENESIS_WEIGHTS_BUCKET"]
    client = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "ap-southeast-2"))
    res = client.get_object(Bucket=bucket, Key=PREVIOUS_CHECKPOINT)
    compressed = res["Body"].read()
    if hashlib.sha256(compressed).hexdigest() != EXPECTED_BASE_SHA256:
        raise ValueError("Source model checksum mismatch")
    previous = json.loads(gzip.decompress(compressed).decode("utf-8"))
    weights = previous["weights"]
    vocab = previous["vocabulary"]
    if previous["architecture"]["parameter_count"] != 1123:
        raise ValueError("Unexpected base model architecture")
    stoi = {char: i for i, char in enumerate(vocab)}
    allowed = set(stoi)

    def normalize(raw):
        return "".join(c if c in allowed else " " for c in raw.lower())

    train_text = normalize("\n".join(CONTINUATION_LINES)) * 2
    validation_text = normalize("\n".join(CONTINUATION_VALIDATION))
    base_validation = normalize("\n".join(VALIDATION_LINES))
    ids = [stoi[c] for c in train_text]
    initial_task_loss = loss_on_text(weights, validation_text, stoi)
    initial_old_loss = loss_on_text(weights, base_validation, stoi)
    losses = []
    for epoch in range(2):
        train_loss = 0.0
        for pos in range(2, len(ids)):
            train_loss += training_step(
                weights, ids[pos - 2], ids[pos - 1], ids[pos], 0.015
            )
        losses.append({
            "epoch": epoch + 1,
            "train_loss": round(train_loss / max(1, len(ids) - 2), 5),
            "heldout_loss": round(loss_on_text(weights, validation_text, stoi), 5),
        })
    final_old_loss = loss_on_text(weights, base_validation, stoi)
    continuation = {
        "format": "genesis-char-mlp-v0-finetuned",
        "kind": "small_neural_continuation_proof",
        "base_checkpoint_sha256": EXPECTED_BASE_SHA256,
        "architecture": previous["architecture"],
        "vocabulary": vocab,
        "weights": weights,
        "training": {
            "epochs": 2,
            "learning_rate": 0.015,
            "source": "original-synthetic-genesis-continuation-text",
            "new_heldout_loss_before": round(initial_task_loss, 5),
            "new_heldout_loss_after": losses[-1]["heldout_loss"],
            "old_heldout_loss_before": round(initial_old_loss, 5),
            "old_heldout_loss_after": round(final_old_loss, 5),
            "history": losses,
        },
        "limitations": (
            "Tiny neural character model. This does not demonstrate useful "
            "instruction-following or general model competence."
        ),
    }
    raw = json.dumps(continuation, separators=(",", ":")).encode("utf-8")
    zipped = gzip.compress(raw, compresslevel=6, mtime=0)
    digest = hashlib.sha256(zipped).hexdigest()
    key = f"genesis/weights/char-mlp-v0-finetuned/genesis-finetune-{digest[:16]}.json.gz"
    save = event.get("save", True)
    if save:
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=zipped,
            ContentType="application/json",
            ContentEncoding="gzip",
            ServerSideEncryption="AES256",
            Metadata={"sha256": digest, "base-sha256": EXPECTED_BASE_SHA256},
        )
    return {
        "ok": True,
        "finetuned": True,
        "checkpoint_saved": save,
        "checkpoint_key": key if save else None,
        "checkpoint_sha256": digest,
        "checkpoint_bytes": len(zipped),
        "initial_task_validation_loss": round(initial_task_loss, 5),
        "final_task_validation_loss": losses[-1]["heldout_loss"],
        "old_validation_loss_before": round(initial_old_loss, 5),
        "old_validation_loss_after": round(final_old_loss, 5),
        "epochs": 2,
    }


def lambda_handler(event, context):
    event = event or {}
    if event.get("action") != "fine_tune":
        return {"ok": False, "error": "Only fine_tune action supported"}
    return continuation_run(event)
