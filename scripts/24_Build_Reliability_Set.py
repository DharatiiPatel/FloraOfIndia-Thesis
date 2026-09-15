#!/usr/bin/env python3
"""Build the reliability analysis table from existing extractor outputs.

No GPU. Recategorises stored free-text with categoriser v2.

Primary ecology labels on a species are Qwen-7B (predeclared). 72B and Llama
are used only for coverage, agreement, and confidence. The keyword baseline is
stored as a benchmark and is not part of consensus.

Species among the n=1,438 ecology set that lack 72B/Llama predictions (fascicle/
recovery increment) are kept in the table with three_llm_coverage=False.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from lib.source_validator import colour_classes_in_phrase, validate_prediction  # noqa: E402

EXP = ROOT / "Processed Data" / "experiments"
OUT = EXP / "reliability"
RES_TABLES = ROOT / "Results" / "tables" / "reliability"

KNOWN = {"WHITE", "YELLOW", "REDTYPE"}


def _load_c2():
    spec = importlib.util.spec_from_file_location(
        "c2", ROOT / "scripts" / "14_Categorize_v2.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _read(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _write(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _norm_bin(s: str) -> str:
    return " ".join((s or "").strip().lower().split())


def _sid_maps(treatments: list[dict]):
    sid_to_bin = {}
    bin_to_sid = {}
    bin_to_text = {}
    for r in treatments:
        sid = r["species_id"]
        b = _norm_bin(r.get("binomial") or f"{r.get('genus', '')} {r.get('epithet', '')}")
        sid_to_bin[sid] = b
        if b and b not in bin_to_sid:
            bin_to_sid[b] = sid
        text = r.get("raw_text") or ""
        if b and text and b not in bin_to_text:
            bin_to_text[b] = text
    return sid_to_bin, bin_to_sid, bin_to_text


def _pred_by_binomial(rows: list[dict], sid_to_bin: dict, text_key="flower_color_free_text"):
    out = {}
    for r in rows:
        sid = r.get("species_id", "")
        b = sid_to_bin.get(sid) or _norm_bin(
            r.get("binomial") or f"{r.get('genus', '')} {r.get('epithet', '')}"
        )
        if not b:
            continue
        out[b] = r.get(text_key) or ""
    return out


def _coarse(c2, free_text: str) -> str:
    return c2.to_class(c2.categorize_v2(free_text or ""))


def _ecology_row(env: dict, color_group: str) -> dict:
    """Binary colour columns only for known classes. UNKNOWN is never 0/1."""
    if color_group not in KNOWN:
        raise ValueError("refuse to code UNKNOWN/OTHER as not-white/yellow/redtype")
    out = {
        "query_name": env["query_name"],
        "color_group": color_group,
        "n_records": env.get("n_records", ""),
    }
    for i in range(1, 11):
        out[f"PC{i}"] = env[f"PC{i}"]
    out["is_white"] = 1 if color_group == "WHITE" else 0
    out["is_yellow"] = 1 if color_group == "YELLOW" else 0
    out["is_redtype"] = 1 if color_group == "REDTYPE" else 0
    return out


def main() -> None:
    c2 = _load_c2()
    eco = _read(
        EXP / "expansion" / "step05b_outputs" / "species_color_environment_final_expanded.csv"
    )
    env_trim = {
        _norm_bin(r["query_name"]): r
        for r in _read(
            EXP / "expansion" / "step05b_outputs" / "species_environment_trimmed.csv"
        )
    }
    treatments = _read(EXP / "species_descriptions_treatments.csv")
    sid_to_bin, bin_to_sid, bin_to_text = _sid_maps(treatments)

    qwen7 = _pred_by_binomial(_read(EXP / "flower_color_qwen_clean.csv"), sid_to_bin)
    # Expansion (recovered/fascicle) 7B extracts fill ONLY species that have no
    # treatment-based extract in flower_color_qwen_clean.csv. Never overwrite an
    # existing original 7B label: its free text must stay aligned with the 72B/
    # Llama treatment extracts (same source text) for a fair three-model
    # comparison. Overwriting made 12 species use a different re-OCR'd text.
    for r in _read(EXP / "expansion" / "flower_color_new.csv"):
        b = _norm_bin(r.get("binomial") or f"{r.get('genus', '')} {r.get('epithet', '')}")
        if b and r.get("flower_color_free_text") and not qwen7.get(b):
            qwen7[b] = r["flower_color_free_text"]
            if r.get("raw_text"):
                bin_to_text[b] = r["raw_text"]

    qwen72 = _pred_by_binomial(
        _read(EXP / "benchmark" / "treatments_pred_qwen72b.csv"), sid_to_bin
    )
    llama = _pred_by_binomial(
        _read(EXP / "benchmark" / "treatments_pred_llama70b.csv"), sid_to_bin
    )
    baseline = _pred_by_binomial(
        _read(EXP / "benchmark" / "treatments_pred_baseline.csv"), sid_to_bin
    )

    rows = []
    for env in eco:
        name = env["query_name"]
        b = _norm_bin(name)
        ft7 = qwen7.get(b, "")
        ft72 = qwen72.get(b, "")
        ftL = llama.get(b, "")
        ftB = baseline.get(b, "")
        c7 = _coarse(c2, ft7) if ft7 else "MISSING"
        c72 = _coarse(c2, ft72) if ft72 else "MISSING"
        cL = _coarse(c2, ftL) if ftL else "MISSING"
        cB = _coarse(c2, ftB) if ftB else "MISSING"

        coverage = c7 not in ("MISSING",) and c72 not in ("MISSING",) and cL not in (
            "MISSING",
        )
        known7 = c7 in KNOWN
        known_all = coverage and c7 in KNOWN and c72 in KNOWN and cL in KNOWN
        agree = known_all and c7 == c72 == cL
        disagree = known_all and not agree

        source = bin_to_text.get(b, "")
        val = validate_prediction(source, c7 if known7 else "UNKNOWN", ft7)

        alt = env_trim.get(b, {}).get("alt", "")
        rec = {
            "query_name": name,
            "binomial_key": b,
            "species_id": bin_to_sid.get(b, ""),
            "genus": name.split()[0] if name.split() else "",
            "published_color_group": env["color_group"],
            "n_records": env.get("n_records", ""),
            "alt": alt,
            "qwen7b_free_text": ft7,
            "qwen72b_free_text": ft72,
            "llama70b_free_text": ftL,
            "baseline_free_text": ftB,
            "qwen7b_v2": c7,
            "qwen72b_v2": c72,
            "llama70b_v2": cL,
            "baseline_v2": cB,
            "three_llm_coverage": str(coverage).upper(),
            "common_known_support": str(known_all).upper(),
            "high_confidence": str(agree).upper(),
            "low_confidence_disagree": str(disagree).upper(),
            "primary_label": c7 if known7 else "",
        }
        for i in range(1, 11):
            rec[f"PC{i}"] = env[f"PC{i}"]
        rec.update(val)
        rec["source_text_available"] = str(bool(source)).upper()
        rec["n_colour_classes_in_7b"] = len(colour_classes_in_phrase(ft7))
        rows.append(rec)

    fields = list(rows[0].keys())
    OUT.mkdir(parents=True, exist_ok=True)
    _write(OUT / "species_reliability.csv", rows, fields)

    def subset(pred):
        keep = [r for r in rows if pred(r)]
        eco_rows = []
        for r in keep:
            env = {
                "query_name": r["query_name"],
                "n_records": r["n_records"],
                **{f"PC{i}": r[f"PC{i}"] for i in range(1, 11)},
            }
            eco_rows.append(_ecology_row(env, r["primary_label"]))
            eco_rows[-1]["genus"] = r["genus"]
            eco_rows[-1]["alt"] = r["alt"]
        return keep, eco_rows

    common, common_eco = subset(lambda r: r["common_known_support"] == "TRUE")
    high, high_eco = subset(lambda r: r["high_confidence"] == "TRUE")
    disagree = [r for r in rows if r["low_confidence_disagree"] == "TRUE"]

    eco_fields = [
        "query_name", "genus", "color_group", "n_records", "alt",
        *[f"PC{i}" for i in range(1, 11)],
        "is_white", "is_yellow", "is_redtype",
    ]
    _write(OUT / "ecology_common_known.csv", common_eco, eco_fields)
    _write(OUT / "ecology_high_confidence.csv", high_eco, eco_fields)
    _write(OUT / "disagreement_descriptive.csv", disagree, fields)

    n = len(rows)
    n_cov = sum(r["three_llm_coverage"] == "TRUE" for r in rows)
    n_common = len(common)
    n_high = len(high)
    n_dis = len(disagree)
    n_unsup = sum(r["unsupported_known_colour"] == True or r["unsupported_known_colour"] == "True"
                  for r in rows if r["qwen7b_v2"] in KNOWN)
    # boolean from validate_prediction
    n_unsup = sum(1 for r in rows if r.get("unsupported_known_colour") in (True, "True", "TRUE"))
    n_wrong = sum(1 for r in rows if r.get("wrong_context_evidence") in (True, "True", "TRUE"))

    agree_on_cov = sum(
        1 for r in rows
        if r["three_llm_coverage"] == "TRUE"
        and r["qwen7b_v2"] in KNOWN
        and r["qwen7b_v2"] == r["qwen72b_v2"] == r["llama70b_v2"]
    )

    summary = {
        "primary_ecology_n": n,
        "three_llm_coverage_n": n_cov,
        "missing_72b_or_llama_n": n - n_cov,
        "note_missing": (
            "Fascicle/recovery species have Qwen-7B only. Three-LLM reliability "
            "is defined on the coverage subset, not the full n=1438."
        ),
        "common_known_support_n": n_common,
        "high_confidence_n": n_high,
        "disagreement_n": n_dis,
        "primary_label": "Qwen-7B categoriser v2",
        "consensus_models": ["qwen7b", "qwen72b", "llama70b"],
        "baseline_not_in_consensus": True,
        "unknown_never_coded_as_negative": True,
        "common_known_colour_counts": dict(Counter(r["primary_label"] for r in common)),
        "high_confidence_colour_counts": dict(Counter(r["primary_label"] for r in high)),
        "agreement_rate_on_coverage_known": None,
        "unsupported_known_colour_n": n_unsup,
        "wrong_context_n": n_wrong,
        "high_confidence_and_supported_n": sum(
            1 for r in high if r.get("supported_floral_evidence") in (True, "True", "TRUE")
        ),
        "agreement_rate_on_common_known": round(n_high / n_common, 4) if n_common else None,
    }
    cov_known = [
        r for r in rows
        if r["three_llm_coverage"] == "TRUE" and r["qwen7b_v2"] in KNOWN
    ]
    if cov_known:
        summary["agreement_rate_on_coverage_known"] = round(
            agree_on_cov / len(cov_known), 4
        )

    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    RES_TABLES.mkdir(parents=True, exist_ok=True)
    (RES_TABLES / "reliability_summary.json").write_text(json.dumps(summary, indent=2))

    print(json.dumps(summary, indent=2))
    print(f"wrote {OUT / 'species_reliability.csv'} ({n} rows)")


if __name__ == "__main__":
    main()
