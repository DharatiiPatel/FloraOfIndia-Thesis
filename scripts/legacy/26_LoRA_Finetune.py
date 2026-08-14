#!/usr/bin/env python3
"""
Supervised adaptation - STEP 3: LoRA fine-tuning of Qwen2.5-7B on the gold set.

What this does differently from every earlier method
----------------------------------------------------
Zero-shot and RAG are *prompted*: the 98 human labels never change a single
model weight. This script actually learns from them. The base model is frozen
and small low-rank adapter matrices are trained on the attention projections,
so only ~0.1-0.5% of parameters are updated. With 71 training rows per fold
that constraint is the point: a full fine-tune would memorise the set instantly.

Protocol (read from finetune/protocol.json, never re-derived here)
------------------------------------------------------------------
For each of the 5 folds: train adapters on that fold's 71-72 training rows,
then generate predictions for the ~18 held-out rows. Concatenating the five
held-out sets gives one out-of-fold prediction for each of the 89 genuine rows,
scored on exactly the rows 25_Lock_Baselines.py locked. Every fold starts from
a fresh copy of the base model, so no information crosses folds.

Loss is masked to the assistant response only - the model is never trained to
reproduce the species description, just to emit the colour phrase given it.

The 9 malformed rows are never trained on. Each fold's model does predict them,
tagged with its fold, so the abstention analysis can use them without any fold
having seen them.

  READS  : Processed Data/experiments/finetune/protocol.json
                                              train_fold{k}.jsonl
                                              eval_fold{k}.jsonl
                                              eval_junk.jsonl
  WRITES : Processed Data/experiments/finetune/
             adapters/fold{k}/            trained LoRA adapter weights
             lora_predictions.csv         out-of-fold predictions (the 89)
             lora_predictions_junk.csv    junk-row predictions, per fold
             lora_train_log.json          per-epoch loss, config, timings

Usage
-----
  # sanity-check one fold and print sample generations before burning GPU time
  python 26_LoRA_Finetune.py --pilot

  # full 5-fold run
  python 26_LoRA_Finetune.py --folds all --epochs 3

  # resume (folds already finished are skipped)
  python 26_LoRA_Finetune.py --folds all
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import time
from pathlib import Path

BASE = Path("/scratch/dp23301/Thesis")
EXP = BASE / "Processed Data" / "experiments"
FT = EXP / "finetune"
ADAPTERS = FT / "adapters"

DEFAULT_MODEL = "Qwen/Qwen2.5-7B-Instruct"
# Matches the generation settings of the zero-shot and RAG extractors so the
# comparison isn't confounded by decoding differences.
MAX_NEW_TOKENS = 32


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def resolve_model_path(model_id: str) -> str:
    """Map a hub repo id to its local snapshot directory when one is cached.

    transformers 4.57 calls model_info() during tokenizer load unless the path
    it is given is local, which fails outright on these nodes (proxy returns
    403, and HF_HUB_OFFLINE turns that into a hard error). Handing it the
    snapshot directory skips that lookup entirely.
    """
    if Path(model_id).is_dir():
        return model_id

    hf_home = os.environ.get("HF_HOME", str(Path.home() / ".cache" / "huggingface"))
    repo_dir = Path(hf_home) / "hub" / f"models--{model_id.replace('/', '--')}"
    snapshots = repo_dir / "snapshots"
    if snapshots.is_dir():
        candidates = [d for d in snapshots.iterdir() if d.is_dir()]
        # A snapshot is only usable if the weight index and tokenizer are there.
        for d in sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True):
            if (d / "config.json").exists() and (d / "tokenizer_config.json").exists():
                print(f"Using cached snapshot: {d}")
                return str(d)

    print(f"No local snapshot for {model_id}; falling back to hub id "
          f"(requires network access)")
    return model_id


def build_example(tokenizer, record: dict, max_len: int):
    """Tokenise one record, masking loss over the prompt.

    The prompt and the answer are tokenised separately rather than trying to
    locate the assistant span inside a rendered template - templates change
    between model families and silent misalignment here would train the model
    on the wrong tokens.
    """
    msgs = record["messages"]
    system, user, assistant = msgs[0], msgs[1], msgs[2]

    prompt_ids = tokenizer.apply_chat_template(
        [system, user], add_generation_prompt=True, tokenize=True,
    )
    answer_ids = tokenizer(
        assistant["content"], add_special_tokens=False,
    )["input_ids"]
    eos = tokenizer.eos_token_id
    if eos is not None:
        answer_ids = answer_ids + [eos]

    input_ids = prompt_ids + answer_ids
    labels = [-100] * len(prompt_ids) + answer_ids

    # Truncate from the LEFT of the prompt so the answer is never cut off.
    if len(input_ids) > max_len:
        overflow = len(input_ids) - max_len
        input_ids = input_ids[overflow:]
        labels = labels[overflow:]

    return {"input_ids": input_ids, "labels": labels}


def generate(model, tokenizer, record: dict, device) -> str:
    import torch

    msgs = record["messages"]
    inputs = tokenizer.apply_chat_template(
        [msgs[0], msgs[1]], add_generation_prompt=True, return_tensors="pt",
    ).to(device)
    with torch.no_grad():
        out = model.generate(
            inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    gen = out[0][inputs.shape[-1]:]
    return tokenizer.decode(gen, skip_special_tokens=True).strip()


def train_one_fold(fold: int, args, log: dict):
    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import (AutoModelForCausalLM, AutoTokenizer,
                              get_linear_schedule_with_warmup)

    torch.manual_seed(args.seed)
    random.seed(args.seed)

    train_recs = load_jsonl(FT / f"train_fold{fold}.jsonl")
    eval_recs = load_jsonl(FT / f"eval_fold{fold}.jsonl")
    junk_recs = load_jsonl(FT / "eval_junk.jsonl")
    print(f"\n{'=' * 70}\nFOLD {fold}: train={len(train_recs)} eval={len(eval_recs)}"
          f" junk={len(junk_recs)}\n{'=' * 70}", flush=True)

    token_kwargs = {}
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token and Path.home().joinpath(".hf_token").exists():
        hf_token = Path.home().joinpath(".hf_token").read_text().strip()
    if hf_token:
        token_kwargs["token"] = hf_token

    model_path = resolve_model_path(args.model)
    tokenizer = AutoTokenizer.from_pretrained(
        model_path, trust_remote_code=True, **token_kwargs)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        **token_kwargs,
    )

    lora_cfg = LoraConfig(
        r=args.rank,
        lora_alpha=args.alpha,
        lora_dropout=args.dropout,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    )
    model = get_peft_model(model, lora_cfg)
    model.print_trainable_parameters()

    if args.grad_checkpointing:
        model.enable_input_require_grads()
        model.gradient_checkpointing_enable()

    device = next(model.parameters()).device
    examples = [build_example(tokenizer, r, args.max_len) for r in train_recs]
    lens = [len(e["input_ids"]) for e in examples]
    print(f"token lengths: min={min(lens)} median={sorted(lens)[len(lens) // 2]} "
          f"max={max(lens)}", flush=True)

    trainable = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(trainable, lr=args.lr, weight_decay=0.0)

    steps_per_epoch = max(1, len(examples) // args.grad_accum)
    total_steps = steps_per_epoch * args.epochs
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=max(1, int(0.03 * total_steps)),
        num_training_steps=total_steps,
    )

    model.train()
    fold_log = {"fold": fold, "epochs": [], "n_train": len(examples)}
    t0 = time.time()

    for epoch in range(args.epochs):
        order = list(range(len(examples)))
        random.Random(args.seed + epoch).shuffle(order)
        running, n_tok, optimizer_steps = 0.0, 0, 0
        optimizer.zero_grad(set_to_none=True)

        for i, idx in enumerate(order, 1):
            ex = examples[idx]
            input_ids = torch.tensor([ex["input_ids"]], device=device)
            labels = torch.tensor([ex["labels"]], device=device)
            out = model(input_ids=input_ids, labels=labels)
            (out.loss / args.grad_accum).backward()
            running += out.loss.item()
            n_tok += 1

            if i % args.grad_accum == 0 or i == len(order):
                torch.nn.utils.clip_grad_norm_(trainable, 1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)
                optimizer_steps += 1

        mean_loss = running / max(1, n_tok)
        fold_log["epochs"].append({"epoch": epoch, "mean_loss": round(mean_loss, 4),
                                   "optimizer_steps": optimizer_steps})
        print(f"  epoch {epoch}: mean_loss={mean_loss:.4f} "
              f"steps={optimizer_steps}", flush=True)

    fold_log["train_seconds"] = round(time.time() - t0, 1)

    out_dir = ADAPTERS / f"fold{fold}"
    out_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out_dir)
    print(f"  adapter saved -> {out_dir}", flush=True)

    model.eval()
    if args.grad_checkpointing:
        model.gradient_checkpointing_disable()

    print(f"  generating {len(eval_recs)} held-out predictions...", flush=True)
    preds = []
    for r in eval_recs:
        preds.append({
            "species_id": r["species_id"],
            "flower_color_free_text": generate(model, tokenizer, r, device),
            "fold": fold,
            "gold_free_text": r["gold_free_text"],
            "gold_category": r["gold_category"],
        })

    print(f"  generating {len(junk_recs)} junk-row predictions...", flush=True)
    junk_preds = []
    for r in junk_recs:
        junk_preds.append({
            "species_id": r["species_id"],
            "flower_color_free_text": generate(model, tokenizer, r, device),
            "fold": fold,
            "gold_free_text": r["gold_free_text"],
            "gold_category": r["gold_category"],
        })

    if args.pilot:
        print("\n  --- sample generations (pilot) ---")
        for p in preds[:8]:
            mark = "ok " if p["flower_color_free_text"].strip().lower() == \
                p["gold_free_text"].strip().lower() else "  "
            print(f"  {mark} pred={p['flower_color_free_text'][:45]!r:50s} "
                  f"gold={p['gold_free_text'][:40]!r}")

    log.setdefault("folds", []).append(fold_log)
    del model
    torch.cuda.empty_cache()
    return preds, junk_preds


def append_csv(path: Path, rows: list[dict], fieldnames: list[str]):
    exists = path.exists()
    with path.open("a" if exists else "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            w.writeheader()
        w.writerows(rows)


def done_folds(path: Path) -> set[int]:
    if not path.exists():
        return set()
    with path.open(encoding="utf-8") as f:
        return {int(r["fold"]) for r in csv.DictReader(f)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--folds", default="all",
                    help="'all' or comma-separated fold ids, e.g. 0,1")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=32)
    ap.add_argument("--dropout", type=float, default=0.05)
    ap.add_argument("--grad-accum", type=int, default=8)
    ap.add_argument("--max-len", type=int, default=1536)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--grad-checkpointing", default=True,
                    action=argparse.BooleanOptionalAction,
                    help="trades compute for memory; --no-grad-checkpointing to disable")
    ap.add_argument("--pilot", action="store_true",
                    help="train fold 0 only and print sample generations")
    args = ap.parse_args()

    protocol = json.loads((FT / "protocol.json").read_text(encoding="utf-8"))
    n_folds = protocol["n_folds"]

    if args.pilot:
        folds = [0]
    elif args.folds == "all":
        folds = list(range(n_folds))
    else:
        folds = [int(x) for x in args.folds.split(",")]

    pred_path = FT / ("lora_predictions_pilot.csv" if args.pilot
                      else "lora_predictions.csv")
    junk_path = FT / ("lora_predictions_junk_pilot.csv" if args.pilot
                      else "lora_predictions_junk.csv")

    already = done_folds(pred_path)
    todo = [k for k in folds if k not in already]
    if already:
        print(f"Already complete: folds {sorted(already)} - skipping")
    if not todo:
        print("Nothing to do.")
        return

    print(f"Model   : {args.model}")
    print(f"Folds   : {todo}")
    print(f"LoRA    : r={args.rank} alpha={args.alpha} dropout={args.dropout}")
    print(f"Train   : epochs={args.epochs} lr={args.lr} grad_accum={args.grad_accum}")
    print(f"Eval set: {protocol['n_genuine_eval']} genuine rows "
          f"(+{protocol['n_junk_heldout']} junk held out)")

    log = {"config": vars(args), "model": args.model}
    fields = ["species_id", "flower_color_free_text", "fold",
              "gold_free_text", "gold_category"]

    for k in todo:
        preds, junk_preds = train_one_fold(k, args, log)
        append_csv(pred_path, preds, fields)
        append_csv(junk_path, junk_preds, fields)
        print(f"  fold {k} predictions appended -> {pred_path.name}", flush=True)

    log_path = FT / ("lora_train_log_pilot.json" if args.pilot
                     else "lora_train_log.json")
    prev = json.loads(log_path.read_text()) if log_path.exists() else {}
    if "folds" in prev:
        log["folds"] = prev["folds"] + log.get("folds", [])
    log_path.write_text(json.dumps(log, indent=2), encoding="utf-8")

    print(f"\nDONE. predictions -> {pred_path}")
    print(f"      train log   -> {log_path}")
    if not args.pilot:
        n = len(done_folds(pred_path))
        print(f"      folds complete: {n}/{n_folds}")
        if n == n_folds:
            print("      -> ready to score with 27_Score_Adaptation.py")


if __name__ == "__main__":
    main()
