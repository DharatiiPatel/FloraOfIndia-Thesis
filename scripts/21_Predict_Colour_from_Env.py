#!/usr/bin/env python3
"""
Prediction task: can flower colour be predicted from environment alone?

The MCMCglmm analysis answers whether colour-environment associations are
statistically detectable. That is a different question from whether the signal
is strong enough to PREDICT colour for an unseen species. This script answers
the second question.

Design notes
------------
Congeneric species share ancestry and occupy similar niches, so a random
train/test split leaks: the model can memorise "genus X is usually white"
from a sibling in the training fold. All headline numbers therefore use
StratifiedGroupKFold grouped by genus, so a genus never spans a split. The
ungrouped split is also reported to quantify how much that leakage inflates
the score.

Two baselines matter:
  * majority class  -- the floor any classifier must beat
  * genus prior     -- predicts a genus's most common training colour, using
                      NO environment at all. Beating this is the real test that
                      environment carries information beyond relatedness.
                      Under grouped CV every test genus is unseen, so this
                      necessarily falls back to the majority class; it is
                      informative under the ungrouped split, where it measures
                      how much of the apparent signal is just phylogeny.

READS : Processed Data/experiments/expansion/step05b_outputs/species_color_environment_final_expanded.csv
WRITES: Processed Data/experiments/prediction_outputs/
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import StratifiedGroupKFold, StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

BASE = Path("/scratch/dp23301/Thesis")
# Primary published analysis set (n=1,438). The earlier clean set under
# step05b_outputs_clean (n=1,174) is historical and no longer used here.
ENV = (BASE / "Processed Data/experiments/expansion/step05b_outputs"
       / "species_color_environment_final_expanded.csv")
OUT = BASE / "Processed Data/experiments/prediction_outputs"

PCS = [f"PC{i}" for i in range(1, 11)]
CLASSES = ["WHITE", "YELLOW", "REDTYPE"]
SEED = 42
N_SPLITS = 5


def load():
    df = pd.read_csv(ENV)
    df["genus"] = df["query_name"].str.split().str[0]
    df = df.dropna(subset=PCS + ["color_group"])
    df = df[df["color_group"].isin(CLASSES)].reset_index(drop=True)
    return df


class GenusPrior:
    """Predict a genus's most common training colour; fall back to majority."""

    def fit(self, genera, y):
        self.majority_ = Counter(y).most_common(1)[0][0]
        table = {}
        for g, label in zip(genera, y):
            table.setdefault(g, Counter())[label] += 1
        self.map_ = {g: c.most_common(1)[0][0] for g, c in table.items()}
        return self

    def predict(self, genera):
        return np.array([self.map_.get(g, self.majority_) for g in genera])


def cv_evaluate(df, grouped: bool):
    """Run cross-validation and return per-model out-of-fold predictions."""
    X = df[PCS].to_numpy()
    y = df["color_group"].to_numpy()
    genera = df["genus"].to_numpy()

    if grouped:
        splitter = StratifiedGroupKFold(
            n_splits=N_SPLITS, shuffle=True, random_state=SEED)
        splits = splitter.split(X, y, groups=genera)
    else:
        splitter = StratifiedKFold(
            n_splits=N_SPLITS, shuffle=True, random_state=SEED)
        splits = splitter.split(X, y)

    models = {
        "majority": lambda: DummyClassifier(strategy="most_frequent"),
        "logreg": lambda: make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=5000, C=1.0, random_state=SEED),
        ),
        "random_forest": lambda: RandomForestClassifier(
            n_estimators=500, min_samples_leaf=3,
            random_state=SEED, n_jobs=-1,
        ),
    }

    oof = {name: np.empty(len(y), dtype=object) for name in models}
    oof["genus_prior"] = np.empty(len(y), dtype=object)

    for train_idx, test_idx in splits:
        for name, factory in models.items():
            clf = factory().fit(X[train_idx], y[train_idx])
            oof[name][test_idx] = clf.predict(X[test_idx])
        gp = GenusPrior().fit(genera[train_idx], y[train_idx])
        oof["genus_prior"][test_idx] = gp.predict(genera[test_idx])

    return y, oof


def score(y_true, y_pred):
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "balanced_accuracy": balanced_accuracy_score(y_true, y_pred),
        "macro_f1": f1_score(y_true, y_pred, average="macro", zero_division=0),
        **{
            f"f1_{c}": f1_score(y_true, y_pred, labels=[c],
                                average="macro", zero_division=0)
            for c in CLASSES
        },
    }


def bootstrap_ci(y_true, y_pred, n_boot=2000, seed=SEED):
    """Percentile CI for macro-F1, matching the RQ1 figure convention."""
    rng = np.random.default_rng(seed)
    n = len(y_true)
    stats = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        if len(set(y_true[idx])) < 2:
            continue
        stats.append(f1_score(y_true[idx], y_pred[idx],
                              average="macro", zero_division=0))
    return float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    df = load()
    print(f"Species: {len(df)}   genera: {df['genus'].nunique()}")
    print("Class balance:", dict(Counter(df["color_group"])))
    print()

    rows = []
    stored = {}
    for grouped in (True, False):
        label = "genus-grouped" if grouped else "ungrouped (leaky)"
        y, oof = cv_evaluate(df, grouped=grouped)
        stored[grouped] = (y, oof)
        print(f"--- {label} {N_SPLITS}-fold CV ---")
        for name, pred in oof.items():
            s = score(y, pred)
            lo, hi = bootstrap_ci(y, pred)
            s.update(model=name, cv=label, macro_f1_lo=lo, macro_f1_hi=hi)
            rows.append(s)
            print(f"  {name:14s} acc={s['accuracy']:.4f}  "
                  f"balacc={s['balanced_accuracy']:.4f}  "
                  f"macroF1={s['macro_f1']:.4f} [{lo:.3f}, {hi:.3f}]")
        print()

    summary = pd.DataFrame(rows)[
        ["cv", "model", "accuracy", "balanced_accuracy", "macro_f1",
         "macro_f1_lo", "macro_f1_hi"] + [f"f1_{c}" for c in CLASSES]
    ].round(4)
    summary.to_csv(OUT / "prediction_cv_summary.csv", index=False)

    # Detailed report + confusion for the headline configuration
    y, oof = stored[True]
    best = max(("logreg", "random_forest"),
               key=lambda m: f1_score(y, oof[m], average="macro",
                                      zero_division=0))
    print(f"Best environment model under grouped CV: {best}\n")
    print(classification_report(y, oof[best], zero_division=0))

    cm = confusion_matrix(y, oof[best], labels=CLASSES)
    pd.DataFrame(cm, index=CLASSES, columns=CLASSES).to_csv(
        OUT / "prediction_confusion_grouped.csv")

    pd.DataFrame({
        "query_name": df["query_name"],
        "genus": df["genus"],
        "true": y,
        **{f"pred_{m}": oof[m] for m in oof},
    }).to_csv(OUT / "prediction_oof_predictions.csv", index=False)

    # Which environmental axes carry the signal?
    X = df[PCS].to_numpy()
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=5000, random_state=SEED),
    ).fit(X, df["color_group"])
    imp = permutation_importance(
        model, X, df["color_group"], n_repeats=50,
        random_state=SEED, scoring="f1_macro", n_jobs=-1)
    pi = (pd.DataFrame({
        "variable": PCS,
        "importance_mean": imp.importances_mean,
        "importance_std": imp.importances_std,
    }).sort_values("importance_mean", ascending=False).round(5))
    pi.to_csv(OUT / "prediction_permutation_importance.csv", index=False)
    print("\nPermutation importance (macro-F1 drop, full-data fit):")
    print(pi.to_string(index=False))

    meta = {
        "n_species": int(len(df)),
        "n_genera": int(df["genus"].nunique()),
        "class_balance": {k: int(v) for k, v in Counter(df["color_group"]).items()},
        "n_splits": N_SPLITS,
        "seed": SEED,
        "features": PCS,
        "best_env_model_grouped": best,
    }
    (OUT / "prediction_run_metadata.json").write_text(json.dumps(meta, indent=2))
    print(f"\nSaved to {OUT}")


if __name__ == "__main__":
    main()
