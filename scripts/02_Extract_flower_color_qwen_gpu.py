import csv
import os
from pathlib import Path

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM 


BASE_DIR = Path("/scratch/dp23301/Thesis")

INPUT_CSV = BASE_DIR / "Processed Data" / "flora_of_india_species_descriptions.csv"
OUTPUT_CSV = BASE_DIR / "Processed Data" / "flora_of_india_flower_color_qwen.csv"

MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"
MAX_NEW_TOKENS = 32

SYSTEM_MESSAGE = (
    "You are an expert botanist. Your ONLY job is to extract the flower colour "
    "from Flora of India species descriptions. "
    "Return a very short phrase like 'flowers white', 'flowers yellow with red centre', "
    "'flowers blue or purple', etc. If flower colour is not mentioned, return exactly "
    "'no flower colour mentioned'. Do NOT add explanations."
)


def load_model_and_tokenizer():
    # HF_TOKEN is optional for Qwen2.5, but we use it if available
    token_kwargs = {} #emooty dic to hold HF token
    hf_token = os.environ.get("HF_TOKEN") 
    if hf_token:
        token_kwargs["token"] = hf_token

    print(f"Loading tokenizer and model: {MODEL_NAME}", flush=True)

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME,
        trust_remote_code=True, 
        **token_kwargs,
    )

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        trust_remote_code=True,
        torch_dtype=torch.float16, #loads model weight in 16floating bit half than normal. computation is faster.
        device_map="auto", #tells pytorch to distribute the model across available hardware.
        **token_kwargs,
    )

    model.eval()
    return tokenizer, model


def infer_flower_color(tokenizer, model, description: str) -> str:
    """Call Qwen2.5 with a chat-style prompt and return its short answer."""
    messages = [
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": f"Species description:\n\n{description}\n\nWhat is the flower colour?"},
    ]

    inputs = tokenizer.apply_chat_template(
        messages,
        return_tensors="pt", #instead of plain string return in tensor. tokenised repr. of entire conversation.
        add_generation_prompt=True, #adds special tokens to the end of the conversation.
    ).to(model.device) #moves the tensor to the appropriate device (GPU or CPU).

    with torch.no_grad(): #disables gradient computation. saves memory and computation.
        outputs = model.generate(
            inputs,
            max_new_tokens=MAX_NEW_TOKENS, 
            do_sample=False, #deterministic generation. no random sampling.
            temperature=0.0, #works with do_sample=False ensures models gives same output for same input every time.
            pad_token_id=tokenizer.eos_token_id,
        )

    generated_ids = outputs[0][inputs.shape[-1]:] #only keeps the models output sliced after the prompt.
    text = tokenizer.decode(generated_ids, skip_special_tokens=True).strip() #converts the token ids back to text. skip_special_tokens=True removes special tokens like <|endoftext|>
    return text


def main():
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input CSV not found: {INPUT_CSV}")

    tokenizer, model = load_model_and_tokenizer()

    print(f"Reading from: {INPUT_CSV}", flush=True)
    print(f"Writing to: {OUTPUT_CSV}", flush=True)

    with open(INPUT_CSV, "r", encoding="utf-8") as f_in, \
         open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f_out:

        reader = csv.DictReader(f_in) #reads input csv where each row is automatically converted into a dict. 
        fieldnames = reader.fieldnames + ["flower_color_free_text"] #adds a new column to the output csv.
        writer = csv.DictWriter(f_out, fieldnames=fieldnames) 
        writer.writeheader() #writes the header row to the output csv.

        count = 0 #counter to track the number of species processed.
        for row in reader:
            description = row.get("raw_text", "")
            try:
                flower_color = infer_flower_color(tokenizer, model, description)
            except Exception as e:
                flower_color = f"ERROR: {e}"

            row["flower_color_free_text"] = flower_color
            writer.writerow(row)

            count += 1
            if count % 20 == 0:
                print(f"Processed {count} species...", flush=True)

    print(f"DONE. Processed {count} species.")
    print(f"Output saved to: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
