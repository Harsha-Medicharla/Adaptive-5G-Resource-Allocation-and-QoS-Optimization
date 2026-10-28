#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from math import sqrt
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results" / "native_policy_compare"


def run_ns3_seed(policy: str, seed: int, ns3_dir: Path, py_exe: str) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    out_prefix = RESULTS / f"{policy}_run{seed}"
    cmd = [
        py_exe,
        str(ns3_dir / "ns3"),
        "run",
        f"slicing-sim --run={seed} --out={out_prefix} --policy={policy}",
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ns3_dir / "contrib" / "ai" / "model" / "gym-interface" / "py")
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=ns3_dir, env=env, check=True)
    return out_prefix.with_name(f"{out_prefix.name}_timeseries.csv")


def run_dqn_seed(seed: int, ns3_dir: Path, py_exe: str) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    out_prefix = RESULTS / f"dqn_run{seed}"
    model_path = RESULTS / f"dqn_model_run{seed}.pt"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ns3_dir / "contrib" / "ai" / "model" / "gym-interface" / "py")
    cmd = [
        py_exe,
        str(ROOT / "code" / "native_dqn.py"),
        "--ns3",
        str(ns3_dir),
        "--run",
        str(seed),
        "--train",
        "--model",
        str(model_path),
        "--out",
        str(out_prefix),
    ]
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)
    return out_prefix.with_name(f"{out_prefix.name}_timeseries.csv")


def summarize_csv(path: Path, policy: str) -> dict:
    df = pd.read_csv(path)
    df["loss_pct"] = ((1.0 - df["delivered_of_tx"] / df["tx_pkts"].clip(lower=1)) * 100.0).clip(lower=0)
    by_slice = df.groupby("slice").agg(
        avg_throughput_mbps=("throughput_mbps", "mean"),
        avg_delay_ms=("delay_mean_ms", "mean"),
        avg_p95_delay_ms=("delay_p95_ms", "mean"),
        avg_loss_pct=("loss_pct", "mean"),
    )
    row = {
        "policy": policy,
        "run": int(df["run"].iloc[0]) if not df.empty else 0,
        "avg_throughput_mbps": float(df["throughput_mbps"].mean()),
        "avg_embb_loss_pct": float(by_slice.loc["eMBB", "avg_loss_pct"]) if "eMBB" in by_slice.index else float("nan"),
        "avg_urllc_loss_pct": float(by_slice.loc["URLLC", "avg_loss_pct"]) if "URLLC" in by_slice.index else float("nan"),
        "avg_mmtc_loss_pct": float(by_slice.loc["mMTC", "avg_loss_pct"]) if "mMTC" in by_slice.index else float("nan"),
        "avg_urllc_delay_ms": float(by_slice.loc["URLLC", "avg_delay_ms"]) if "URLLC" in by_slice.index else float("nan"),
        "avg_urllc_p95_ms": float(by_slice.loc["URLLC", "avg_p95_delay_ms"]) if "URLLC" in by_slice.index else float("nan"),
    }
    return row


def summarize_policy_files() -> pd.DataFrame:
    rows = []
    for csv_path in sorted(RESULTS.glob("*_timeseries.csv")):
        policy = csv_path.name.split("_run")[0]
        if policy.startswith("native_"):
            policy = policy.replace("native_", "")
        rows.append(summarize_csv(csv_path, policy))
    if not rows:
        raise FileNotFoundError(f"No native comparison CSVs found in {RESULTS}")
    return pd.DataFrame(rows)


def aggregate_policy_summary(df: pd.DataFrame) -> pd.DataFrame:
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
            vals = group[metric].dropna().to_numpy(dtype=float)
            if vals.size == 0:
                row[f"{metric}_mean"] = np.nan
                row[f"{metric}_std"] = np.nan
                row[f"{metric}_ci95"] = np.nan
                row[f"{metric}_ci_low"] = np.nan
                row[f"{metric}_ci_high"] = np.nan
                continue
            mean = float(vals.mean())
            std = float(vals.std(ddof=1)) if vals.size > 1 else 0.0
            ci = float(1.96 * std / sqrt(vals.size)) if vals.size > 1 else 0.0
            row[f"{metric}_mean"] = mean
            row[f"{metric}_std"] = std
            row[f"{metric}_ci95"] = ci
            row[f"{metric}_ci_low"] = mean - ci
            row[f"{metric}_ci_high"] = mean + ci
        rows.append(row)
    return pd.DataFrame(rows)


def plot_summary(df: pd.DataFrame, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    grouped = df.groupby("policy", as_index=False).agg(avg_urlc_delay_ms=("avg_urllc_delay_ms", "mean"))
    colors = ["#3b82f6", "#f59e0b", "#10b981", "#ef4444"]
    ax.bar(grouped["policy"], grouped["avg_urlc_delay_ms"], color=colors[: len(grouped)])
    ax.set_title("Average URLLC delay by policy")
    ax.set_ylabel("Delay (ms)")
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a native ns-3 comparison across static, random, adaptive, and DQN policies.")
    parser.add_argument("--ns3", type=str, default=str(Path.home() / "ns3" / "ns-3.45"), help="Path to the ns-3 installation")
    parser.add_argument("--runs", type=int, default=3, help="Number of seeds to run per policy")
    parser.add_argument("--policies", type=str, default="static,random,adaptive,dqn", help="Comma-separated policies to run")
    parser.add_argument("--skip-dqn", action="store_true", help="Skip DQN training for quick comparison")
    args = parser.parse_args()

    ns3_dir = Path(args.ns3).expanduser().resolve()
    py_exe = sys.executable
    if not ns3_dir.exists():
        raise FileNotFoundError(f"ns-3 directory not found: {ns3_dir}")
    if not (ns3_dir / "ns3").exists():
        raise FileNotFoundError(f"ns-3 executable not found in {ns3_dir}")

    policy_list = [p.strip() for p in args.policies.split(",") if p.strip()]
    for policy in policy_list:
        if policy == "dqn" and args.skip_dqn:
            continue
        for seed in range(1, args.runs + 1):
            if policy == "dqn":
                run_dqn_seed(seed, ns3_dir, py_exe)
            else:
                run_ns3_seed(policy, seed, ns3_dir, py_exe)

    overall = summarize_policy_files()
    output_path = RESULTS / "overall_summary.csv"
    overall.to_csv(output_path, index=False)
    aggregate_path = RESULTS / "policy_summary.csv"
    aggregate_policy_summary(overall).to_csv(aggregate_path, index=False)
    plot_summary(overall, RESULTS / "policy_delay_comparison.png")
    print(f"Saved raw benchmark summary to {output_path}")
    print(f"Saved aggregated policy summary to {aggregate_path}")
    print(overall.to_string(index=False))


if __name__ == "__main__":
    main()
