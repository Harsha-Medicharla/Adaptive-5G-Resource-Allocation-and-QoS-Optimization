from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "results" / "adaptive" / "policy_summary.csv"

st.set_page_config(page_title="Adaptive 5G Slicing Dashboard", layout="wide")
st.title("Adaptive 5G Slicing Dashboard")

if not CSV_PATH.exists():
    st.error(f"No results found at {CSV_PATH}. Run `python3 code/run_adaptive_experiments.py` first.")
    st.stop()

summary = pd.read_csv(CSV_PATH)
policies = sorted(summary["policy"].unique())
selected = st.multiselect("Policies", policies, default=policies)
filtered = summary[summary["policy"].isin(selected)]

st.subheader("Per-phase comparison")
st.dataframe(filtered, use_container_width=True)

st.subheader("Policy-level average metrics")
metric_cols = [
    "eMBB_loss_pct",
    "URLLC_loss_pct",
    "mMTC_loss_pct",
    "eMBB_delay_ms",
    "URLLC_delay_ms",
    "mMTC_delay_ms",
    "score",
]
by_policy = filtered.groupby("policy")[metric_cols].mean().round(3)
st.dataframe(by_policy, use_container_width=True)

st.subheader("Allocation view")
alloc_df = filtered[["policy", "phase", "alloc"]].copy()
alloc_df["alloc"] = alloc_df["alloc"].astype(str)
st.dataframe(alloc_df, use_container_width=True)
