"""Clean PTB-XL metadata and (optionally) export the matching ECG signals.

Usage:
    python clean_dataset.py                      # metadata + labels only
    python clean_dataset.py --signals            # also save X.npy aligned with metadata
    python clean_dataset.py --min-likelihood 50  # ignore low-confidence SCP statements

Outputs (in --out-dir, default data/processed/):
    metadata.pkl  cleaned metadata (pickle keeps dtypes, categories and list columns)
    labels.csv    multi-label 0/1 targets (NORM, MI, STTC, CD, HYP), indexed by ecg_id
    X.npy         signals, rows in the same order as metadata.pkl (only with --signals)

"""

import argparse
import ast
import os

import numpy as np
import pandas as pd

from ekg.config import load_config, setup, to_absolute_path

QUALITY_COLS = [
    "baseline_drift",
    "static_noise",
    "burst_noise",
    "electrodes_problems",
    "extra_beats",
    "pacemaker",
]
ID_COLS = ["patient_id", "nurse", "site", "validated_by", "device"]

# plausibility limits for adults (children are left untouched)
ADULT_AGE = 18
HEIGHT_RANGE = (120, 230)  # cm
WEIGHT_RANGE = (30, 250)  # kg
BMI_RANGE = (12, 70)


def load_metadata(path):
    Y = pd.read_csv(os.path.join(path, "ptbxl_database.csv"), index_col="ecg_id")
    Y["scp_codes"] = Y["scp_codes"].apply(ast.literal_eval)

    agg_df = pd.read_csv(os.path.join(path, "scp_statements.csv"), index_col=0)
    agg_df = agg_df[agg_df.diagnostic == 1]
    return Y, agg_df


def aggregate_diagnostic(scp_codes, agg_df, min_likelihood=0):
    """Map SCP codes to sorted, de-duplicated diagnostic superclasses."""
    return sorted(
        {
            agg_df.loc[code].diagnostic_class
            for code, likelihood in scp_codes.items()
            if code in agg_df.index and likelihood >= min_likelihood
        }
    )


def clean_metadata(Y, agg_df, min_likelihood=0):
    Y = Y.copy()
    n_start = len(Y)

    # labels
    Y["diagnostic_superclass"] = Y["scp_codes"].apply(
        aggregate_diagnostic, agg_df=agg_df, min_likelihood=min_likelihood
    )

    # age: 300 = anonymised ">89"
    Y["age_over_89"] = Y["age"] == 300
    Y.loc[Y["age_over_89"], "age"] = 90

    # implausible adult height/weight -> NaN
    adult = Y["age"] >= ADULT_AGE
    bad_h = adult & Y["height"].notna() & ~Y["height"].between(*HEIGHT_RANGE)
    bad_w = adult & Y["weight"].notna() & ~Y["weight"].between(*WEIGHT_RANGE)
    Y.loc[bad_h, "height"] = np.nan
    Y.loc[bad_w, "weight"] = np.nan

    # combos that pass individually but are impossible together
    bmi = Y["weight"] / (Y["height"] / 100) ** 2
    bad_bmi = bmi.notna() & ~bmi.between(*BMI_RANGE)
    Y.loc[bad_bmi, ["height", "weight"]] = np.nan

    # signal-quality columns: NaN means "no problem noted"
    for col in QUALITY_COLS:
        Y[f"has_{col}"] = Y[col].notna()

    # unify missing markers / types
    Y["infarction_stadium1"] = Y["infarction_stadium1"].replace("unknown", np.nan)
    Y["heart_axis"] = Y["heart_axis"].fillna("unknown")
    Y["recording_date"] = pd.to_datetime(Y["recording_date"])

    # IDs are categories, not numbers
    for col in ID_COLS:
        Y[col] = Y[col].astype("category")

    # drop records without a diagnostic label
    no_label = Y["diagnostic_superclass"].str.len() == 0
    Y = Y[~no_label]

    print(f"records:            {n_start} -> {len(Y)}")
    print(f"  no label dropped: {no_label.sum()}")
    print(f'  age 300 -> 90:    {Y["age_over_89"].sum()}')
    print(f"  bad height:       {bad_h.sum()}")
    print(f"  bad weight:       {bad_w.sum()}")
    print(f"  bad BMI combo:    {bad_bmi.sum()}")
    return Y


def make_labels(Y):
    """Multi-label 0/1 matrix, one column per superclass."""
    return (
        pd.get_dummies(Y["diagnostic_superclass"].explode())
        .groupby(level=0)
        .max()
        .astype(int)
        .reindex(Y.index, fill_value=0)
    )


def load_signals(Y, sampling_rate, path):
    import wfdb

    files = Y.filename_lr if sampling_rate == 100 else Y.filename_hr
    return np.array([wfdb.rdsamp(os.path.join(path, f))[0] for f in files])


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--config", default="config.yml")
    parser.add_argument("--out-dir")
    parser.add_argument(
        "--min-likelihood",
        type=float,
        default=0,
        help="ignore SCP statements below this likelihood (0-100)",
    )
    parser.add_argument(
        "--signals", action="store_true", help="also load and save the ECG signals as X.npy"
    )
    args = parser.parse_args()

    setup()

    cfg = load_config(args.config)
    path = cfg["paths"]["raw_data"]
    sampling_rate = cfg["data"]["sampling_rate"]

    Y, agg_df = load_metadata(path)
    Y = clean_metadata(Y, agg_df, args.min_likelihood)
    labels = make_labels(Y)

    out_dir = to_absolute_path(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)
    Y.to_pickle(os.path.join(out_dir, "metadata.pkl"))
    labels.to_csv(os.path.join(out_dir, "labels.csv"))
    print("\nlabel counts:")
    print(labels.sum().to_string())

    if args.signals:
        print(f"\nloading {len(Y)} signals at {sampling_rate} Hz ...")
        X = load_signals(Y, sampling_rate, path)
        np.save(os.path.join(out_dir, "X.npy"), X)
        print(f"X shape: {X.shape}")

    print(f"\nsaved to {out_dir}/")


if __name__ == "__main__":
    main()
