from __future__ import annotations

import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from adaptive_slicing import PHASES, make_policy_summary, static_allocation, greedy_allocation

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "adaptive"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    rows = make_policy_summary()
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "policy_summary.csv", index=False)

    summary = df.groupby(["policy"]).agg(
        avg_score=("score", "mean"),
        eMBB_loss=("eMBB_loss_pct", "mean"),
        URLLC_loss=("URLLC_loss_pct", "mean"),
        mMTC_loss=("mMTC_loss_pct", "mean"),
        URLLC_delay=("URLLC_delay_ms", "mean"),
    )
    summary.to_csv(OUT / "overall_summary.csv")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    policies = ["static", "random", "adaptive"]
    scores = [df[df.policy == p].score.mean() for p in policies]
    ax.bar(policies, scores, color=["#3b82f6", "#f59e0b", "#10b981"])
    ax.set_title("Average policy score by policy")
    ax.set_ylabel("Composite score")
    ax.grid(axis="y", alpha=0.15)
    fig.tight_layout()
    fig.savefig(OUT / "policy_score_comparison.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5.5))
    phases = [p["name"] for p in PHASES]
    static_scores = []
    adaptive_scores = []
    from adaptive_slicing import evaluate_allocation

    for phase in PHASES:
        static_eval = evaluate_allocation(phase, static_allocation())
        adaptive_eval = evaluate_allocation(phase, greedy_allocation(phase))
        static_scores.append(static_eval["score"])
        adaptive_scores.append(adaptive_eval["score"])

    x = range(len(phases))
    ax.plot(x, static_scores, marker="o", linewidth=2, label="static")
    ax.plot(x, adaptive_scores, marker="s", linewidth=2, label="adaptive")
    ax.set_xticks(list(x))
    ax.set_xticklabels(phases, rotation=20)
    ax.set_ylabel("Composite score")
    ax.set_title("Phase-wise score comparison")
    ax.legend()
    ax.grid(True, alpha=0.15)
    fig.tight_layout()
    fig.savefig(OUT / "phase_score_comparison.png", dpi=180)
    plt.close(fig)

    print(f"Saved results to {OUT}")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
