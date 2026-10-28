"""Cleaning and feature engineering for readmission analysis."""
import pandas as pd

# Discharge codes for death or hospice (these patients cannot be readmitted)
EXCLUDE_DISCHARGE = [11, 13, 14, 19, 20, 21]

ADMISSION_TYPE = {
    1: "Emergency", 2: "Urgent", 3: "Elective", 4: "Newborn",
    5: "Not available", 6: "Not available", 7: "Trauma center", 8: "Not available",
}

AGE_MAP = {
    "[0-10)": "<40", "[10-20)": "<40", "[20-30)": "<40", "[30-40)": "<40",
    "[40-50)": "40-59", "[50-60)": "40-59",
    "[60-70)": "60-79", "[70-80)": "60-79",
    "[80-90)": "80+", "[90-100)": "80+",
}

A1C_MAP = {"Norm": "Normal", ">7": "High (>7)", ">8": "High (>8)"}


def icd9_group(code) -> str:
    """Map a primary ICD-9 diagnosis code to a broad clinical group."""
    if pd.isna(code):
        return "Unknown"
    text = str(code)
    if text[0] in "EV":
        return "Other"
    try:
        base = int(float(text))
    except ValueError:
        return "Other"
    if base == 250:
        return "Diabetes"
    if 390 <= base <= 459 or base == 785:
        return "Circulatory"
    if 460 <= base <= 519 or base == 786:
        return "Respiratory"
    if 520 <= base <= 579 or base == 787:
        return "Digestive"
    if 580 <= base <= 629 or base == 788:
        return "Genitourinary"
    if 710 <= base <= 739:
        return "Musculoskeletal"
    if 800 <= base <= 999:
        return "Injury"
    if 140 <= base <= 239:
        return "Neoplasms"
    return "Other"


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Return an analysis-ready table: one row per patient (first encounter)."""
    df = df.copy()
    df = df[~df["discharge_disposition_id"].isin(EXCLUDE_DISCHARGE)]
    df = df[df["gender"].isin(["Male", "Female"])]
    df = df.sort_values("encounter_id").drop_duplicates("patient_nbr", keep="first")

    df["readmitted_30d"] = (df["readmitted"] == "<30").astype(int)
    df["age_group"] = df["age"].map(AGE_MAP)
    df["admission_type"] = df["admission_type_id"].map(ADMISSION_TYPE).fillna("Not available")
    df["discharged_home"] = (df["discharge_disposition_id"] == 1).astype(int)
    df["diag_group"] = df["diag_1"].map(icd9_group)
    df["a1c_status"] = df["A1Cresult"].map(A1C_MAP).fillna("Not tested")

    for col in ("race", "medical_specialty", "payer_code"):
        df[col] = df[col].fillna("Unknown")

    df = df.drop(columns=["weight"], errors="ignore")  # almost entirely missing
    return df.reset_index(drop=True)