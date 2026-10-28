"""Descriptive statistics, hypothesis tests and logistic regression.
Usage:  python -m src.analysis
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, norm

from src.clean import clean
from src.load_data import load_raw

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_PATH = ROOT / "data" / "processed" / "cleaned_encounters.csv"
TABLE_DIR = ROOT / "reports" / "tables"
FIG_DIR = ROOT / "reports" / "figures"

GROUP_COLUMNS = ["age_group", "a1c_status", "admission_type", "diag_group",
                 "race", "gender", "change"]

# Categorical predictors and their reference (baseline) level
MODEL_CATEGORICALS = {
    "age_group": "40-59", "gender": "Female", "race": "Caucasian",
    "a1c_status": "Not tested", "admission_type": "Emergency",
    "diag_group": "Circulatory", "change": "No",
}
MODEL_NUMERIC = ["time_in_hospital", "num_medications", "num_lab_procedures",
                 "number_diagnoses", "number_inpatient", "number_emergency",
                 "number_outpatient"]
Z95 = norm.ppf(0.975)


def wilson_ci(successes, n, z: float = Z95):
    """Wilson score interval for a proportion."""
    k, n = np.asarray(successes, float), np.asarray(n, float)
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return centre - half, centre + half


def rate_table(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """30-day readmission rate with 95% CI for each level of `col`."""
    g = (df.groupby(col)["readmitted_30d"]
         .agg(encounters="size", readmitted="sum").reset_index())
    g["rate_pct"] = 100 * g["readmitted"] / g["encounters"]
    low, high = wilson_ci(g["readmitted"], g["encounters"])
    g["ci_low_pct"], g["ci_high_pct"] = 100 * low, 100 * high
    return g.sort_values("rate_pct", ascending=False).reset_index(drop=True)


def chi_square_p(df: pd.DataFrame, col: str) -> float:
    table = pd.crosstab(df[col], df["readmitted_30d"])
    return float(chi2_contingency(table)[1])


def plot_rates(tbl: pd.DataFrame, col: str, overall: float, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    err = [tbl["rate_pct"] - tbl["ci_low_pct"], tbl["ci_high_pct"] - tbl["rate_pct"]]
    ax.bar(tbl[col].astype(str), tbl["rate_pct"], yerr=err, capsize=3, color="#3b7ea1")
    ax.axhline(overall, color="red", linestyle="--", linewidth=1, label=f"Overall {overall:.1f}%")
    ax.set_ylabel("30-day readmission rate (%)")
    ax.set_title(f"Readmission rate by {col} (95% CI)")
    ax.legend()
    plt.xticks(rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def design_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Intercept + numeric columns + dummy-coded categoricals (reference dropped)."""
    parts = [df[MODEL_NUMERIC].astype(float)]
    for col, ref in MODEL_CATEGORICALS.items():
        dummies = pd.get_dummies(df[col], prefix=col, prefix_sep=": ").astype(float)
        parts.append(dummies.drop(columns=f"{col}: {ref}", errors="ignore"))
    X = pd.concat(parts, axis=1)
    X.insert(0, "Intercept", 1.0)
    return X


def logit_irls(X: np.ndarray, y: np.ndarray, max_iter: int = 100, tol: float = 1e-8):
    """Logistic regression by Newton-Raphson. Returns (coefficients, std errors)."""
    beta = np.zeros(X.shape[1])
    for _ in range(max_iter):
        p = 1 / (1 + np.exp(-np.clip(X @ beta, -30, 30)))
        w = np.clip(p * (1 - p), 1e-10, None)
        hessian = X.T @ (X * w[:, None])
        step = np.linalg.solve(hessian, X.T @ (y - p))
        beta = beta + step
        if np.max(np.abs(step)) < tol:
            break
    p = 1 / (1 + np.exp(-np.clip(X @ beta, -30, 30)))
    w = np.clip(p * (1 - p), 1e-10, None)
    cov = np.linalg.inv(X.T @ (X * w[:, None]))
    return beta, np.sqrt(np.diag(cov))


def fit_logistic(df: pd.DataFrame) -> pd.DataFrame:
    """Odds ratios with 95% CI for predictors of 30-day readmission."""
    X = design_matrix(df)
    beta, se = logit_irls(X.to_numpy(float), df["readmitted_30d"].to_numpy(float))
    out = pd.DataFrame({
        "term": X.columns,
        "odds_ratio": np.exp(beta),
        "ci_low": np.exp(beta - Z95 * se),
        "ci_high": np.exp(beta + Z95 * se),
        "p_value": 2 * norm.sf(np.abs(beta / se)),
    })
    return out[out["term"] != "Intercept"].sort_values("odds_ratio", ascending=False)


def plot_forest(odds: pd.DataFrame, path: Path) -> None:
    sig = odds[odds["p_value"] < 0.05].copy()
    order = sig["odds_ratio"].apply(lambda x: abs(np.log(x))).sort_values(ascending=False).index
    sig = sig.loc[order].head(15).iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 6))
    y = np.arange(len(sig))
    ax.errorbar(sig["odds_ratio"], y,
                xerr=[sig["odds_ratio"] - sig["ci_low"], sig["ci_high"] - sig["odds_ratio"]],
                fmt="o", color="#1f4e79", capsize=3)
    ax.axvline(1, color="red", linestyle="--", linewidth=1)
    ax.set_yticks(y)
    ax.set_yticklabels(sig["term"])
    ax.set_xlabel("Odds ratio (95% CI)")
    ax.set_title("Significant predictors of 30-day readmission (p < 0.05)")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def run(df: pd.DataFrame, table_dir: Path = TABLE_DIR, fig_dir: Path = FIG_DIR,
        summary_path: Path = ROOT / "reports" / "summary.json") -> dict:
    table_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)
    overall = 100 * df["readmitted_30d"].mean()

    summary = {
        "patients_analysed": int(len(df)),
        "readmission_rate_pct": round(overall, 2),
        "mean_length_of_stay_days": round(df["time_in_hospital"].mean(), 2),
        "chi_square_p_values": {},
    }
    for col in GROUP_COLUMNS:
        tbl = rate_table(df, col)
        tbl.round(2).to_csv(table_dir / f"readmission_by_{col}.csv", index=False)
        summary["chi_square_p_values"][col] = chi_square_p(df, col)
        if col in ("age_group", "a1c_status", "admission_type", "diag_group"):
            plot_rates(tbl, col, overall, fig_dir / f"rate_by_{col}.png")

    prior = df.assign(prior_inpatient=np.where(df["number_inpatient"] >= 3, "3+",
                                               df["number_inpatient"].astype(str)))
    tbl = rate_table(prior, "prior_inpatient").sort_values("prior_inpatient")
    tbl.round(2).to_csv(table_dir / "readmission_by_prior_inpatient.csv", index=False)
    plot_rates(tbl, "prior_inpatient", overall, fig_dir / "rate_by_prior_inpatient.png")

    odds = fit_logistic(df)
    odds.round(4).to_csv(table_dir / "logistic_odds_ratios.csv", index=False)
    plot_forest(odds, fig_dir / "odds_ratio_forest.png")

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    df = clean(load_raw())
    PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED_PATH, index=False)
    summary = run(df)
    print(json.dumps(summary, indent=2))
    print(f"Tables -> {TABLE_DIR}\nFigures -> {FIG_DIR}")


if __name__ == "__main__":
    main()