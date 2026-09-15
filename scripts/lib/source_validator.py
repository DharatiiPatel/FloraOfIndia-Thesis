"""Lexical source-text checks for flower-colour predictions.

Flags only: a miss does not prove the extractor is wrong, and a hit does not
prove it is right. Windowing can miss a colour named far from 'flower'.
"""

from __future__ import annotations

import re

FLORAL = re.compile(
    r"\b(flowers?|floral|corolla|petals?|tepals?|perianth|"
    r"inflorescence|florets?|anthers?|stamens?|sepals?|calyx)\b",
    re.I,
)
WRONG_CONTEXT = re.compile(
    r"\b(fruits?|berr(?:y|ies)|drupes?|arils?|leaves|leaf|foliage|"
    r"bark|seeds?|indument|tomentose|pubescent|hairy|hirsute|"
    r"villous|sericeous|woolly)\b",
    re.I,
)
KEY_STUB = re.compile(
    r"\b(carpels?\s+\d|key to |flowers yellow, in panicles|perennial herbs;)\b",
    re.I,
)

# Coarse class -> colour tokens expected in Flora prose
CLASS_PATTERNS = {
    "WHITE": re.compile(r"\b(whitish|white|cream(?:y)?)\b", re.I),
    "YELLOW": re.compile(r"\b(yellowish|yellow|golden|orange)\b", re.I),
    "REDTYPE": re.compile(
        r"\b(pinkish|pink|scarlet|crimson|reddish|\bred\b|"
        r"purplish|purple|violet|bluish|\bblue\b)\b",
        re.I,
    ),
}

MULTI_HINT = re.compile(
    r"\b( or | to |tinged|variable|sometimes|rarely|and )\b", re.I
)

WINDOW = 140


def _windows_around(text: str, span: tuple[int, int]) -> str:
    a, b = span
    return text[max(0, a - WINDOW) : min(len(text), b + WINDOW)]


def colour_classes_in_phrase(phrase: str) -> list[str]:
    """All coarse classes mentioned in extractor free text (not first-only)."""
    found = []
    for cls, pat in CLASS_PATTERNS.items():
        if pat.search(phrase or ""):
            found.append(cls)
    return found


def validate_prediction(source: str, predicted_class: str, free_text: str) -> dict:
    source = source or ""
    free_text = free_text or ""
    pred = (predicted_class or "UNKNOWN").upper()
    classes_in_pred = colour_classes_in_phrase(free_text)
    multi = len(classes_in_pred) > 1 or bool(MULTI_HINT.search(free_text))

    floral_in_source = bool(FLORAL.search(source))
    malformed = (not source.strip()) or len(source) < 80 or bool(KEY_STUB.search(source))

    supported = False
    wrong_context = False
    colour_in_source = False

    if pred in CLASS_PATTERNS:
        pat = CLASS_PATTERNS[pred]
        for m in pat.finditer(source):
            colour_in_source = True
            chunk = _windows_around(source, m.span())
            has_floral = bool(FLORAL.search(chunk))
            has_wrong = bool(WRONG_CONTEXT.search(chunk))
            if has_floral:
                supported = True
            if has_wrong and not has_floral:
                wrong_context = True
        # If the colour word is absent from the treatment, the quote is unsupported.
        if pred in ("WHITE", "YELLOW", "REDTYPE") and not colour_in_source:
            supported = False

    if pred in ("UNKNOWN", "OTHER"):
        # Abstention: 'supported' means the treatment also lacks a floral colour.
        supported = not any(p.search(source) for p in CLASS_PATTERNS.values()) or (
            not floral_in_source
        )

    return {
        "floral_term_in_source": floral_in_source,
        "predicted_colour_in_source": colour_in_source,
        "supported_floral_evidence": supported,
        "wrong_context_evidence": wrong_context and not supported,
        "multi_colour_phrase": multi,
        "classes_in_prediction": "|".join(classes_in_pred),
        "malformed_or_key_stub": malformed,
        "unsupported_known_colour": pred in ("WHITE", "YELLOW", "REDTYPE")
        and not supported,
    }
