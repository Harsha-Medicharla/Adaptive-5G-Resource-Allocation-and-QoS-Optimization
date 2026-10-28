from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"


def summarize_policy_runs(df: pd.DataFrame) -> pd.DataFrame:
    if "policy" not in df.columns:
        return df

    metrics = [
        "avg_throughput_mbps",
        "avg_embb_loss_pct",
        "avg_urllc_loss_pct",
        "avg_mmtc_loss_pct",
        "avg_urllc_delay_ms",
        "avg_urllc_p95_ms",
    ]
    rows = []
    for policy, group in df.groupby("policy", sort=True):
        row = {"policy": policy}
        for metric in metrics:
            if metric not in group.columns:
                continue
            vals = group[metric].dropna().astype(float)
            if vals.empty:
                continue
            mean = float(vals.mean())
            std = float(vals.std(ddof=1)) if len(vals) > 1 else 0.0
            ci95 = float(1.96 * std / np.sqrt(len(vals))) if len(vals) > 1 else 0.0
            row[f"{metric}_mean"] = mean
            row[f"{metric}_std"] = std
            row[f"{metric}_ci95"] = ci95
            row[f"{metric}_low"] = mean - ci95
            row[f"{metric}_high"] = mean + ci95
        rows.append(row)
    return pd.DataFrame(rows)


st.set_page_config(page_title="5G Slicing Dashboard", layout="wide")
st.title("5G Slicing Comparison Dashboard")

native_summary = RESULTS / "native_policy_compare" / "overall_summary.csv"
prototype_summary = RESULTS / "adaptive" / "policy_summary.csv"

available = {
    "native": pd.read_csv(native_summary) if native_summary.exists() else None,
    "prototype": pd.read_csv(prototype_summary) if prototype_summary.exists() else None,
}

if not any(available.values()):
    st.warning("No summary CSV found. Run the native comparison or the adaptive prototype first.")
    st.stop()

selected_key = st.radio("Choose dataset", [k for k, v in available.items() if v is not None], horizontal=True)
raw_summary = available[selected_key]
summary = summarize_policy_runs(raw_summary)

st.subheader(f"{selected_key.title()} policy summary (mean ± 95% CI)")
if summary.empty:
    st.info("No comparable metrics available for this dataset.")
else:
    score_cols = [c for c in summary.columns if c.endswith("_mean") or c.endswith("_ci95")]
    display = summary[["policy"] + [c for c in summary.columns if c.startswith("avg_urllc_delay_ms") or c.startswith("avg_urllc_p95_ms") or c.startswith("avg_throughput_mbps") or c.startswith("avg_urllc_loss_pct")]].copy()
    st.dataframe(display.round(3), use_container_width=True)

    delay = summary[["policy", "avg_urllc_delay_ms_mean"]].rename(columns={"avg_urllc_delay_ms_mean": "avg_urllc_delay_ms"})
    st.bar_chart(delay.set_index("policy"))

st.subheader("Raw per-run comparison")
policies = sorted(raw_summary["policy"].unique())
selected = st.multiselect("Policies", policies, default=policies)
filtered = raw_summary[raw_summary["policy"].isin(selected)]
st.dataframe(filtered.round(3), use_container_width=True)

st.subheader("CSV file browser")
for path in sorted(RESULTS.rglob("*.csv")):
    if "native_policy_compare" in str(path) or "adaptive" in str(path):
        st.caption(str(path.relative_to(ROOT)))

st.subheader("Images")
img_files = sorted(RESULTS.rglob("*.png"))
if img_files:
    for p in img_files[:10]:
        st.image(str(p), caption=str(p.relative_to(ROOT)))
else:
    st.write("No PNG plots available yet.")
