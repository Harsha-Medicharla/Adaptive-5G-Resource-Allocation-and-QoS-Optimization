#!/usr/bin/env python3
"""
draw_diagrams.py  -  architecture figures for the paper (light) and slides (dark).
Usage: python3 draw_diagrams.py --out ../results/figs_light --theme light
"""
import argparse, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

THEMES = {
    "light": dict(bg="#ffffff", fg="#0b0b0b", fg2="#52514e", box="#f6f5f1", edge="#8a8984",
                  accent="#0b7fa8", warn="#c98500",
                  c={"eMBB": "#2a78d6", "URLLC": "#eb6834", "mMTC": "#1baf7a"}),
    "dark": dict(bg="#0d1117", fg="#ffffff", fg2="#c3c2b7", box="#161d27", edge="#3b4554",
                 accent="#22d3ee", warn="#f5a524",
                 c={"eMBB": "#3987e5", "URLLC": "#d95926", "mMTC": "#199e70"}),
}


def box(ax, x, y, w, h, text, t, edge=None, fill=None, fs=8.5, bold=False, color=None, dashed=False):
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.01,rounding_size=0.12",
                       fc=fill or t["box"], ec=edge or t["edge"], lw=1.4,
                       ls="--" if dashed else "-")
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            color=color or t["fg"], fontweight="bold" if bold else "normal", linespacing=1.3)


def arrow(ax, a, b, t, color=None, lw=1.4, ls="-", text=None, rad=0.0, fs=7.5, toff=(0, 0.12)):
    ar = FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=10, lw=lw,
                         color=color or t["fg2"], ls=ls, connectionstyle=f"arc3,rad={rad}")
    ax.add_patch(ar)
    if text:
        ax.text((a[0] + b[0]) / 2 + toff[0], (a[1] + b[1]) / 2 + toff[1], text, ha="center",
                va="bottom", fontsize=fs, color=t["fg2"])


def topology(t, out):
    fig, ax = plt.subplots(figsize=(7.2, 3.3))
    ax.set_xlim(0, 12); ax.set_ylim(0.3, 6.05); ax.axis("off")
    rows = [("eMBB", "3 UEs\nCBR, 1200 B", 4.6, "50 u = 10 Mbps"),
            ("URLLC", "3 UEs\nPoisson, 200 B", 2.7, "30 u = 6 Mbps"),
            ("mMTC", "15-60 devices\nPoisson, 64 B", 0.8, "20 u = 4 Mbps")]
    for sl, desc, y, cap in rows:
        c = t["c"][sl]
        box(ax, 0.1, y, 2.3, 1.0, f"{sl}\n{desc}", t, edge=c, fs=7.8)
        arrow(ax, (2.45, y + 0.5), (3.55, y + 0.5), t, color=c, text="100 Mbps", fs=6.5)
        box(ax, 3.6, y + 0.1, 1.6, 0.8, f"GW {sl}", t, edge=c, fs=8)
        # slice pipe with queue
        ax.add_patch(FancyBboxPatch((5.5, y + 0.3), 0.9, 0.4, boxstyle="square,pad=0", fc=t["bg"], ec=c, lw=1.2))
        for k in range(6):
            ax.add_patch(plt.Rectangle((5.55 + k * 0.14, y + 0.34), 0.1, 0.32, fc=c, ec="none", alpha=0.5 + 0.08 * k))
        ax.text(5.95, y + 0.78, "FIFO 100 p", ha="center", fontsize=6.5, color=t["fg2"])
        arrow(ax, (5.25, y + 0.5), (5.5, y + 0.5), t, color=c)
        arrow(ax, (6.45, y + 0.5), (8.65, 3.2 + (y - 2.7) * 0.25), t, color=c, lw=1.4 + 0.5 * (sl == "eMBB"))
        ax.text(7.45 + (0.9 if sl == "eMBB" else 0), y + (0.3 if sl == "eMBB" else (0.62 if sl == "URLLC" else -0.15)), f"slice pipe\n{cap}", ha="center", fontsize=6.8, color=c)
    box(ax, 8.7, 2.3, 1.9, 1.8, "Base station\n(gNB + sink)\n\nper-packet\ndelay, loss", t, edge=t["accent"], fs=8)
    box(ax, 10.75, 2.3, 1.2, 1.8, "Resource\npool\n100 units\n= 20 Mbps", t, edge=t["warn"], fs=7.3, dashed=True)
    ax.text(6.0, 5.85, "ApplyAllocation(units)  sets slice pipe rates  (static now, DQN after midsem)",
            ha="center", fontsize=7.5, color=t["warn"])
    fig.tight_layout(pad=0.2)
    fig.savefig(os.path.join(out, "arch_topology.png"), dpi=230)
    plt.close(fig)


def system(t, out):
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    ax.set_xlim(0, 12); ax.set_ylim(0, 6.6); ax.axis("off")
    # ns-3 side
    ax.add_patch(FancyBboxPatch((0.15, 0.2), 5.6, 6.1, boxstyle="round,pad=0,rounding_size=0.2",
                                fc="none", ec=t["accent"], lw=1.3, ls="--"))
    ax.text(0.35, 6.0, "ns-3 (C++)  network simulation", fontsize=8.5, color=t["accent"], fontweight="bold")
    box(ax, 0.5, 4.5, 2.4, 1.0, "Traffic generator\n5-phase scenario", t, fs=7.8)
    box(ax, 3.1, 4.5, 2.4, 1.0, "Slice pipes + FIFO\n(eMBB / URLLC / mMTC)", t, fs=7.8)
    box(ax, 0.5, 2.6, 2.4, 1.2, "Measurement\n100 ms bins: thr, delay,\np95, loss, served devs", t, fs=7.3)
    box(ax, 3.1, 2.6, 2.4, 1.2, "ApplyAllocation()\nsets pipe rates\n(units x 0.2 Mbps)", t, edge=t["warn"], fs=7.5)
    box(ax, 0.5, 0.6, 5.0, 1.2, "Env step (post-midsem, 1 s decision interval)\nrun interval  ->  build state  ->  wait for action", t, fs=7.5, dashed=True)
    arrow(ax, (2.9, 5.0), (3.1, 5.0), t)
    arrow(ax, (4.3, 4.5), (1.7, 3.8), t, rad=0.0)
    arrow(ax, (1.7, 2.6), (1.7, 1.8), t)
    arrow(ax, (4.3, 1.8), (4.3, 2.6), t, color=t["warn"])
    # bridge
    box(ax, 6.05, 2.4, 1.5, 1.8, "ns3-ai\nshared\nmemory\n(state, action,\nreward)", t, edge=t["accent"], fs=7.2, dashed=True)
    arrow(ax, (5.5, 1.3), (6.3, 2.4), t, color=t["accent"], text="state", fs=7, toff=(0.35, -0.25))
    arrow(ax, (6.8, 2.4), (5.6, 1.0), t, color=t["warn"], text="", rad=0.25)
    # python side
    ax.add_patch(FancyBboxPatch((7.85, 0.2), 4.0, 6.1, boxstyle="round,pad=0,rounding_size=0.2",
                                fc="none", ec=t["warn"], lw=1.3, ls="--"))
    ax.text(8.05, 6.0, "Python (post-midsem)", fontsize=8.5, color=t["warn"], fontweight="bold")
    box(ax, 8.2, 4.4, 3.3, 1.2, "DQN agent (PyTorch)\nMLP 64-64, replay buffer,\ntarget net, e-greedy", t, edge=t["warn"], fs=7.3, dashed=True)
    box(ax, 8.2, 2.6, 3.3, 1.2, "Reward\n+thr, -delay viol, -loss,\n+mMTC served, +util, +fairness", t, fs=7.2, dashed=True)
    box(ax, 8.2, 0.6, 3.3, 1.3, "Baselines + Dashboard\nStatic | Random | DQN\nStreamlit (reads logs)", t, fs=7.3, dashed=True)
    arrow(ax, (7.55, 3.6), (8.2, 4.9), t, color=t["accent"])
    arrow(ax, (8.2, 5.1), (7.55, 4.0), t, color=t["warn"], text="action", fs=7, toff=(-0.05, 0.6), rad=0.2)
    arrow(ax, (9.85, 3.8), (9.85, 4.4), t)
    ax.text(6.8, 0.35, "solid = built for midsem\ndashed = post-midsem", fontsize=6.6, color=t["fg2"], ha="center", va="center")
    fig.tight_layout(pad=0.2)
    fig.savefig(os.path.join(out, "arch_system.png"), dpi=230)
    plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="../results/figs_light")
    ap.add_argument("--theme", default="light", choices=list(THEMES))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    t = THEMES[a.theme]
    plt.rcParams.update({"figure.facecolor": t["bg"], "savefig.facecolor": t["bg"], "font.family": "DejaVu Sans"})
    topology(t, a.out)
    system(t, a.out)
    print("diagrams ->", a.out)
