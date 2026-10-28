#!/usr/bin/env python3
"""
plot_results.py
Reads runN_timeseries.csv files written by slicing-sim and produces
the midsem figures + a per-phase summary table (mean and 95% CI over seeds).

Usage:  python3 plot_results.py --results ../results --out ../results/figs --theme light
        (theme: light for the paper, dark for the slides)
Each figure is its own function, so edit one without touching the others.
"""
import argparse, glob, os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ------------------------------------------------------------------ config
SLICES = ["eMBB", "URLLC", "mMTC"]
PKT = {"eMBB": 1200, "URLLC": 200, "mMTC": 64}   # payload bytes (from C++ config)
WIRE_OVH = 30                                     # IPv4 + UDP + PPP bytes
URLLC_TARGET_MS = 10.0
PHASES = [(0, 10, "P1 Normal"), (10, 20, "P2 eMBB burst"), (20, 30, "P3 eMBB+URLLC high"),
          (30, 40, "P4 URLLC very high"), (40, 50, "P5 mMTC surge")]
SMOOTH_BINS = 5                                    # 5 x 100 ms rolling mean for plots

THEMES = {
    "light": dict(bg="#ffffff", fg="#0b0b0b", fg2="#52514e", grid="#e4e3df",
                  band="#f3f2ee", target="#e34948",
                  c={"eMBB": "#2a78d6", "URLLC": "#eb6834", "mMTC": "#1baf7a"}),
    "dark":  dict(bg="#0d1117", fg="#ffffff", fg2="#c3c2b7", grid="#262c36",
                  band="#151b24", target="#e66767",
                  c={"eMBB": "#3987e5", "URLLC": "#d95926", "mMTC": "#199e70"}),
}


# ------------------------------------------------------------------ data
def load_runs(results_dir):
    files = sorted(glob.glob(os.path.join(results_dir, "run*_timeseries.csv")))
    d = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    d["offered_wire_mbps"] = d.apply(
        lambda r: r.demand_mbps * (PKT[r.slice] + WIRE_OVH) / PKT[r.slice], axis=1)
    d["loss_pct"] = np.where(d.tx_pkts > 0, 100 * (1 - d.delivered_of_tx / d.tx_pkts.clip(lower=1)), np.nan)
    d["util_pct"] = 100 * d.wire_mbps / d.capacity_mbps
    d["phase"] = np.clip((d.time // 10).astype(int) + 1, 1, 5)
    return d


def seed_mean(d, col, sl):
    """mean over seeds per time bin, then rolling smooth"""
    x = d[d.slice == sl].groupby("time")[col].mean()
    return x.rolling(SMOOTH_BINS, center=True, min_periods=1).mean()


def ci95(x):
    x = np.asarray(x, float); x = x[~np.isnan(x)]
    if len(x) < 2: return np.nan
    return 1.96 * x.std(ddof=1) / np.sqrt(len(x))


def phase_summary(d):
    """per run, per phase, per slice metrics -> mean +- 95% CI over runs"""
    rows = []
    for (run, ph, sl), x in d.groupby(["run", "phase", "slice"]):
        tx, ok, rx = x.tx_pkts.sum(), x.delivered_of_tx.sum(), x.rx_pkts.sum()
        rows.append(dict(run=run, phase=ph, slice=sl,
                         capacity=x.capacity_mbps.mean(),
                         offered=x.offered_wire_mbps.mean(),
                         carried=x.wire_mbps.mean(),
                         throughput=x.throughput_mbps.mean(),
                         loss=100 * (1 - ok / tx) if tx else np.nan,
                         delay=np.nansum(x.delay_mean_ms * x.rx_pkts) / rx if rx else np.nan,
                         p95=x.delay_p95_ms.mean(),
                         viol=100 * x.urllc_viol.sum() / rx if rx else np.nan,
                         active=x.mmtc_active.mean(), served=x.mmtc_served.mean(),
                         util=100 * x.wire_mbps.mean() / x.capacity_mbps.mean()))
    r = pd.DataFrame(rows)
    agg = r.groupby(["phase", "slice"]).agg(["mean", ci95]).drop(columns="run")
    return r, agg


# ------------------------------------------------------------------ style
def style(theme):
    t = THEMES[theme]
    plt.rcParams.update({
        "figure.facecolor": t["bg"], "axes.facecolor": t["bg"], "savefig.facecolor": t["bg"],
        "axes.edgecolor": t["grid"], "axes.labelcolor": t["fg2"], "text.color": t["fg"],
        "xtick.color": t["fg2"], "ytick.color": t["fg2"], "grid.color": t["grid"],
        "axes.grid": True, "grid.linewidth": 0.6, "axes.spines.top": False,
        "axes.spines.right": False, "font.size": 9, "axes.titlesize": 10,
        "axes.titleweight": "bold", "legend.frameon": False, "lines.linewidth": 1.6,
        "font.family": "DejaVu Sans",
    })
    return t


def phase_bands(ax, t, labels=False, y=None):
    for i, (a, b, name) in enumerate(PHASES):
        if i % 2 == 1:
            ax.axvspan(a, b, color=t["band"], zorder=0, lw=0)
        if labels:
            ax.text((a + b) / 2, y, name.split(" ", 1)[0], ha="center", va="bottom",
                    fontsize=7.5, color=t["fg2"], transform=ax.get_xaxis_transform())
    ax.set_xlim(0, 50)


def save(fig, out, name):
    fig.tight_layout()
    fig.savefig(os.path.join(out, name), dpi=220)
    plt.close(fig)


# ------------------------------------------------------------------ figures
def fig_demand_vs_capacity(d, t, out):
    fig, axes = plt.subplots(3, 1, figsize=(7, 4.6), sharex=True)
    for ax, sl in zip(axes, SLICES):
        phase_bands(ax, t, labels=(sl == "eMBB"), y=1.02)
        ax.plot(seed_mean(d, "offered_wire_mbps", sl), color=t["c"][sl], label="offered load")
        off, car = seed_mean(d, "offered_wire_mbps", sl), seed_mean(d, "wire_mbps", sl)
        ax.fill_between(off.index, car, off, where=off > car + 0.05, color=t["target"],
                        alpha=0.35, lw=0, label="dropped (offered - carried)")
        ax.plot(seed_mean(d, "capacity_mbps", sl), color=t["fg"], ls="--", lw=1.1, label="allocated capacity")
        ax.set_ylabel(f"{sl}\n(Mbps)")
        ax.set_ylim(0, None)
    axes[0].legend(ncol=3, loc="upper right", bbox_to_anchor=(1, 1.45), fontsize=8)
    axes[-1].set_xlabel("Time (s)")
    save(fig, out, "fig1_demand_vs_capacity.png")


def fig_throughput(d, t, out):
    fig, ax = plt.subplots(figsize=(7, 3))
    phase_bands(ax, t, labels=True, y=1.01)
    for sl in SLICES:
        ax.plot(seed_mean(d, "throughput_mbps", sl), color=t["c"][sl], label=sl)
    ax.set_ylabel("Delivered throughput (Mbps)"); ax.set_xlabel("Time (s)")
    ax.legend(ncol=3, loc="upper left", fontsize=8)
    ax.set_ylim(0, None)
    save(fig, out, "fig2_throughput.png")


def fig_urllc_latency(d, t, out):
    fig, ax = plt.subplots(figsize=(7, 3))
    phase_bands(ax, t, labels=True, y=1.01)
    c = t["c"]["URLLC"]
    ax.plot(seed_mean(d, "delay_mean_ms", "URLLC"), color=c, label="mean delay")
    ax.plot(seed_mean(d, "delay_p95_ms", "URLLC"), color=c, ls=":", label="95th percentile")
    ax.axhline(URLLC_TARGET_MS, color=t["target"], ls="--", lw=1.1)
    ax.text(0.5, URLLC_TARGET_MS * 1.12, f"target {URLLC_TARGET_MS:.0f} ms", color=t["fg2"], fontsize=8)
    ax.set_yscale("log")
    ax.set_yticks([1, 2, 5, 10, 20, 50]); ax.set_yticklabels(["1", "2", "5", "10", "20", "50"])
    ax.minorticks_off(); ax.set_ylim(1, 60)
    ax.set_ylabel("URLLC one-way delay (ms, log)"); ax.set_xlabel("Time (s)")
    ax.legend(loc="upper left", fontsize=8)
    save(fig, out, "fig3_urllc_latency.png")


def fig_loss(d, t, out):
    fig, ax = plt.subplots(figsize=(7, 3))
    phase_bands(ax, t, labels=True, y=1.01)
    for sl in SLICES:
        ax.plot(seed_mean(d, "loss_pct", sl), color=t["c"][sl], label=sl)
    ax.set_ylabel("Packet loss (%)"); ax.set_xlabel("Time (s)")
    ax.legend(ncol=3, loc="upper left", fontsize=8); ax.set_ylim(0, None)
    save(fig, out, "fig4_packet_loss.png")


def fig_allocation_utilisation(d, t, out):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7, 2.8), gridspec_kw=dict(width_ratios=[1, 1.6]))
    # left: static allocation (units), stacked
    x = d[d.run == d.run.min()]
    tt = x[x.slice == "eMBB"].time.values
    stack = [x[x.slice == sl].alloc_units.values for sl in SLICES]
    a1.stackplot(tt, *stack, colors=[t["c"][s] for s in SLICES], labels=SLICES,
                 edgecolor=t["bg"], linewidth=1.5)
    a1.set_ylim(0, 100); a1.set_xlim(0, 50); a1.grid(False)
    a1.set_ylabel("Resource units (of 100)"); a1.set_xlabel("Time (s)")
    a1.set_title("Allocation (static)")
    for sl, y in zip(SLICES, [25, 65, 90]):
        a1.text(25, y, sl, ha="center", va="center", color="#ffffff", fontsize=8, fontweight="bold")
    # right: per-slice utilisation of its own capacity
    phase_bands(a2, t)
    for sl in SLICES:
        a2.plot(seed_mean(d, "util_pct", sl), color=t["c"][sl], label=sl)
    a2.axhline(100, color=t["fg2"], ls="--", lw=0.9)
    a2.set_ylim(0, 110); a2.set_ylabel("Slice utilisation (%)"); a2.set_xlabel("Time (s)")
    a2.set_title("Utilisation of allocated capacity")
    a2.legend(ncol=3, loc="lower left", fontsize=7.5)
    save(fig, out, "fig5_allocation_utilisation.png")


def fig_mmtc_devices(d, t, out):
    fig, ax = plt.subplots(figsize=(7, 2.8))
    phase_bands(ax, t, labels=True, y=1.01)
    c = t["c"]["mMTC"]
    ax.plot(seed_mean(d, "mmtc_active", "mMTC"), color=t["fg2"], ls="--", lw=1.2, label="active devices")
    ax.plot(seed_mean(d, "mmtc_served", "mMTC"), color=c, label=f"served devices (PDR ≥ 90%)")
    ax.set_ylabel("mMTC devices"); ax.set_xlabel("Time (s)"); ax.set_ylim(0, 65)
    ax.legend(loc="upper left", fontsize=8)
    save(fig, out, "fig6_mmtc_devices.png")


def fig_stranded_capacity(r, t, out):
    """per phase: capacity left unused in some slices vs traffic dropped in others"""
    rows = []
    for ph in range(1, 6):
        x = r[r.phase == ph]
        per_run = []
        for run, y in x.groupby("run"):
            unused = (y.capacity - y.carried).clip(lower=0).sum()
            unmet = (y.offered - y.carried).clip(lower=0).sum()
            per_run.append((unused, unmet))
        a = np.array(per_run)
        rows.append((ph, a[:, 0].mean(), a[:, 1].mean()))
    rows = np.array(rows)
    w = 0.36
    xs = np.arange(5)
    fig, ax = plt.subplots(figsize=(7, 2.8))
    ax.bar(xs - w / 2 - 0.01, rows[:, 1], w, color=t["fg2"], label="unused allocated capacity")
    ax.bar(xs + w / 2 + 0.01, rows[:, 2], w, color=t["target"], label="unmet demand (dropped)")
    for i in range(5):
        ax.text(xs[i] - w / 2, rows[i, 1] + 0.1, f"{rows[i,1]:.1f}", ha="center", fontsize=7.5, color=t["fg2"])
        ax.text(xs[i] + w / 2, rows[i, 2] + 0.1, f"{rows[i,2]:.1f}", ha="center", fontsize=7.5, color=t["fg2"])
    ax.set_xticks(xs, [p[2].replace(" ", "\n", 1) for p in PHASES], fontsize=7.5)
    ax.set_ylabel("Mbps (wire)"); ax.grid(axis="x", visible=False)
    ax.set_ylim(0, rows[:, 1:].max() * 1.3)
    ax.legend(loc="upper right", fontsize=8)
    save(fig, out, "fig7_stranded_capacity.png")
    return rows


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="../results")
    ap.add_argument("--out", default="../results/figs")
    ap.add_argument("--theme", default="light", choices=list(THEMES))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    t = style(a.theme)
    d = load_runs(a.results)
    r, agg = phase_summary(d)
    fig_demand_vs_capacity(d, t, a.out)
    fig_throughput(d, t, a.out)
    fig_urllc_latency(d, t, a.out)
    fig_loss(d, t, a.out)
    fig_allocation_utilisation(d, t, a.out)
    fig_mmtc_devices(d, t, a.out)
    stranded = fig_stranded_capacity(r, t, a.out)
    agg.round(3).to_csv(os.path.join(a.out, "phase_summary.csv"))
    pd.DataFrame(stranded, columns=["phase", "unused_mbps", "unmet_mbps"]).round(3).to_csv(
        os.path.join(a.out, "stranded_capacity.csv"), index=False)
    print("runs:", sorted(d.run.unique()), "-> figures in", a.out)


if __name__ == "__main__":
    main()
