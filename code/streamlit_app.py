from __future__ import annotations

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"

METRICS = {
    "avg_throughput_mbps": {
        "label": "Throughput",
        "unit": "Mbps",
        "goal": "max",
        "description": "Higher is better",
    },
    "avg_embb_loss_pct": {
        "label": "eMBB Packet Loss",
        "unit": "%",
        "goal": "min",
        "description": "Lower is better",
    },
    "avg_urllc_loss_pct": {
        "label": "URLLC Packet Loss",
        "unit": "%",
        "goal": "min",
        "description": "Lower is better",
    },
    "avg_mmtc_loss_pct": {
        "label": "mMTC Packet Loss",
        "unit": "%",
        "goal": "min",
        "description": "Lower is better",
    },
    "avg_urllc_delay_ms": {
        "label": "URLLC Average Delay",
        "unit": "ms",
        "goal": "min",
        "description": "Lower is better",
    },
    "avg_urllc_p95_ms": {
        "label": "URLLC P95 Delay",
        "unit": "ms",
        "goal": "min",
        "description": "Lower is better",
    },
}

POLICY_ORDER = ["dqn", "static", "random"]

POLICY_COLORS = {
    "static": "#64748b",
    "random": "#f59e0b",
    "dqn": "#10b981",
    "dql": "#10b981",
}


# ---------------------------------------------------------
# Page configuration and styling
# ---------------------------------------------------------

st.set_page_config(
    page_title="5G Network Slicing Analytics",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.6rem;
            padding-bottom: 2.5rem;
            max-width: 1550px;
        }

        div[data-testid="stMetric"] {
            background: rgba(128, 128, 128, 0.08);
            border: 1px solid rgba(128, 128, 128, 0.18);
            padding: 16px;
            border-radius: 12px;
        }

        div[data-testid="stMetricLabel"] {
            font-size: 14px;
        }

        h1, h2, h3 {
            letter-spacing: -0.02em;
        }

        .demo-banner {
            padding: 12px 16px;
            border-radius: 10px;
            border: 1px solid rgba(16, 185, 129, 0.45);
            background: rgba(16, 185, 129, 0.09);
            margin: 12px 0 18px 0;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("5G Network Slicing Analytics")
st.caption(
    "Native ns-3 benchmark dashboard | Static vs Random vs DQN"
)


# ---------------------------------------------------------
# Temporary demo dataset
#
# Edit or remove this block when you are ready to display
# actual benchmark data. No CSV is read or changed in demo mode.
# ---------------------------------------------------------

DEMO_VALUES = pd.DataFrame(
    [
        {
            "policy": "dqn",
            "avg_throughput_mbps": 4.65,
            "avg_embb_loss_pct": 8.50,
            "avg_urllc_loss_pct": 3.50,
            "avg_mmtc_loss_pct": 1.50,
            "avg_urllc_delay_ms": 6.80,
            "avg_urllc_p95_ms": 7.50,
        },
        {
            "policy": "random",
            "avg_throughput_mbps": 3.38,
            "avg_embb_loss_pct": 36.24,
            "avg_urllc_loss_pct": 14.39,
            "avg_mmtc_loss_pct": 5.90,
            "avg_urllc_delay_ms": 27.37,
            "avg_urllc_p95_ms": 29.90,
        },
        {
            "policy": "static",
            "avg_throughput_mbps": 4.33,
            "avg_embb_loss_pct": 11.99,
            "avg_urllc_loss_pct": 8.33,
            "avg_mmtc_loss_pct": 2.17,
            "avg_urllc_delay_ms": 8.31,
            "avg_urllc_p95_ms": 9.11,
        },
    ]
)

raw_summary = DEMO_VALUES.copy()

summary = DEMO_VALUES.rename(
    columns={metric: f"{metric}_mean" for metric in METRICS}
).copy()


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def metric_columns(summary_df: pd.DataFrame) -> list[str]:
    """Return metrics available in the summary dataframe."""
    return [
        metric
        for metric in METRICS
        if f"{metric}_mean" in summary_df.columns
    ]


def best_policy(
    summary_df: pd.DataFrame,
    metric: str,
) -> tuple[str, float] | None:
    """Return the best policy and its value for a metric."""
    mean_column = f"{metric}_mean"

    if mean_column not in summary_df.columns:
        return None

    valid = summary_df[["policy", mean_column]].dropna()
    if valid.empty:
        return None

    if METRICS[metric]["goal"] == "max":
        index = valid[mean_column].idxmax()
    else:
        index = valid[mean_column].idxmin()

    row = valid.loc[index]
    return str(row["policy"]), float(row[mean_column])


def format_value(value: float, unit: str) -> str:
    if unit == "%":
        return f"{value:.2f}%"
    return f"{value:.2f} {unit}"


def ordered_policies(values: list[str]) -> list[str]:
    """Keep a stable visual order across all charts."""
    values = [str(value).lower() for value in values]
    ordered = [p for p in POLICY_ORDER if p in values]
    ordered.extend(p for p in values if p not in ordered)
    return ordered


def policy_color() -> alt.Color:
    return alt.Color(
        "policy:N",
        scale=alt.Scale(
            domain=["static", "random", "dqn", "dql"],
            range=["#64748b", "#f59e0b", "#10b981", "#10b981"],
        ),
        legend=None,
    )


# ---------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------

with st.sidebar:
    st.header("Dashboard Controls")

    available_policies = ordered_policies(
        summary["policy"].astype(str).unique().tolist()
    )

    selected_policies = st.multiselect(
        "Policies to compare",
        options=available_policies,
        default=available_policies,
        format_func=lambda policy: policy.upper(),
    )

    st.divider()

    available_metrics = metric_columns(summary)

    selected_metric = st.selectbox(
        "Primary metric",
        options=available_metrics,
        format_func=lambda key: (
            f"{METRICS[key]['label']} ({METRICS[key]['unit']})"
        ),
    )


if not selected_policies:
    st.warning("Select at least one policy to display.")
    st.stop()

filtered = summary[
    summary["policy"].astype(str).isin(selected_policies)
].copy()

# Use a stable policy order for all charts and tables.
filtered["policy"] = pd.Categorical(
    filtered["policy"],
    categories=ordered_policies(selected_policies),
    ordered=True,
)
filtered = filtered.sort_values("policy")


# ---------------------------------------------------------
# Executive KPI cards
# ---------------------------------------------------------

st.subheader("Executive Overview")

priority_metrics = [
    "avg_throughput_mbps",
    "avg_urllc_delay_ms",
    "avg_urllc_loss_pct",
    "avg_urllc_p95_ms",
]
priority_metrics = [
    metric
    for metric in priority_metrics
    if f"{metric}_mean" in filtered.columns
]

if priority_metrics:
    cols = st.columns(len(priority_metrics))

    for col, metric in zip(cols, priority_metrics):
        result = best_policy(filtered, metric)

        with col:
            st.markdown(f"**{METRICS[metric]['label']}**")

            if result is None:
                st.metric("Best value", "N/A")
                continue

            policy, value = result
            st.metric(
                label=f"Best: {policy.upper()}",
                value=format_value(value, METRICS[metric]["unit"]),
            )
            st.caption(METRICS[metric]["description"])

st.divider()


# ---------------------------------------------------------
# Main policy comparison chart
# ---------------------------------------------------------

st.subheader("Policy Performance Comparison")

metric = selected_metric
mean_column = f"{metric}_mean"

plot_df = (
    filtered[["policy", mean_column]]
    .dropna()
    .rename(columns={mean_column: "value"})
)
plot_df["policy"] = plot_df["policy"].astype(str)

sort_order = (
    plot_df.sort_values(
        "value",
        ascending=(METRICS[metric]["goal"] == "min"),
    )["policy"]
    .tolist()
)

base = alt.Chart(plot_df).encode(
    y=alt.Y(
        "policy:N",
        title="Allocation Policy",
        sort=sort_order,
        axis=alt.Axis(
            labelFontSize=13,
            labelLimit=120,
            labelPadding=10,
            ticks=False,
            domain=False,
        ),
    ),
    x=alt.X(
        "value:Q",
        title=f"{METRICS[metric]['label']} ({METRICS[metric]['unit']})",
        axis=alt.Axis(
            grid=True,
            labelFontSize=12,
            titleFontSize=13,
            tickCount=8,
        ),
    ),
    color=policy_color(),
    tooltip=[
        alt.Tooltip("policy:N", title="Policy"),
        alt.Tooltip(
            "value:Q",
            title=METRICS[metric]["label"],
            format=".2f",
        ),
    ],
)

bars = base.mark_bar(
    cornerRadiusEnd=6,
    size=38,
)

labels = base.mark_text(
    align="left",
    baseline="middle",
    dx=8,
    fontSize=13,
    fontWeight="bold",
    color="#f8fafc",
    clip=False,
).encode(
    text=alt.Text("value:Q", format=".2f"),
)

main_chart = (
    alt.layer(bars, labels)
    .properties(
        height=max(240, 85 * len(plot_df)),
        padding={"left": 8, "right": 45, "top": 10, "bottom": 8},
        title=alt.TitleParams(
            text=f"{METRICS[metric]['label']} by Allocation Policy",
            anchor="start",
            fontSize=17,
            offset=16,
        ),
    )
    .configure_view(strokeOpacity=0)
    .configure_axis(
        labelFontSize=12,
        titleFontSize=13,
    )
)

st.altair_chart(main_chart, width="stretch")

result = best_policy(filtered, metric)
if result:
    policy, value = result
    st.caption(
        f"Best displayed policy for this metric: **{policy.upper()}** "
        f"({format_value(value, METRICS[metric]['unit'])}). "
        f"{METRICS[metric]['description']}."
    )

st.divider()


# ---------------------------------------------------------
# All-metric comparison charts
# ---------------------------------------------------------

st.subheader("All Metrics at a Glance")
st.caption(
    "Higher throughput is better. Lower packet loss and latency are better. "
    "Each chart uses the same policy colors and a dedicated row per policy."
)

all_metrics = metric_columns(filtered)

for start in range(0, len(all_metrics), 2):
    metric_pair = all_metrics[start : start + 2]
    columns = st.columns(2)

    for col, metric in zip(columns, metric_pair):
        with col:
            mean_column = f"{metric}_mean"

            chart_df = (
                filtered[["policy", mean_column]]
                .dropna()
                .rename(columns={mean_column: "value"})
            )
            chart_df["policy"] = chart_df["policy"].astype(str)

            chart_order = ordered_policies(
                chart_df["policy"].tolist()
            )

            chart_df["value_label"] = chart_df["value"].map(
                lambda value: f"{value:.2f}"
            )

            mini_base = alt.Chart(chart_df).encode(
                y=alt.Y(
                    "policy:N",
                    title=None,
                    sort=chart_order,
                    axis=alt.Axis(
                        labelFontSize=12,
                        labelLimit=100,
                        labelPadding=8,
                        ticks=False,
                        domain=False,
                    ),
                ),
                x=alt.X(
                    "value:Q",
                    title=METRICS[metric]["unit"],
                    axis=alt.Axis(
                        labelFontSize=10,
                        titleFontSize=11,
                        grid=True,
                        tickCount=5,
                    ),
                ),
                color=policy_color(),
                tooltip=[
                    alt.Tooltip("policy:N", title="Policy"),
                    alt.Tooltip(
                        "value:Q",
                        title=METRICS[metric]["label"],
                        format=".2f",
                    ),
                ],
            )

            mini_bars = mini_base.mark_bar(
                cornerRadiusEnd=4,
                size=23,
            )

            mini_labels = mini_base.mark_text(
                align="left",
                baseline="middle",
                dx=5,
                fontSize=11,
                color="#f8fafc",
                clip=False,
            ).encode(
                text=alt.Text("value:Q", format=".2f")
            )

            mini_chart = (
                alt.layer(mini_bars, mini_labels)
                .properties(
                    title=alt.TitleParams(
                        text=METRICS[metric]["label"],
                        anchor="start",
                        fontSize=15,
                        offset=10,
                    ),
                    height=max(150, 58 * len(chart_df)),
                    padding={"left": 4, "right": 30, "top": 5, "bottom": 5},
                )
                .configure_view(strokeOpacity=0)
            )

            st.altair_chart(mini_chart, width="stretch")

st.divider()


# ---------------------------------------------------------
# Numerical comparison table — no ± values
# ---------------------------------------------------------

st.subheader("Numerical Comparison")

display_rows = []

for _, row in filtered.iterrows():
    record = {"Policy": str(row["policy"]).upper()}

    for metric in all_metrics:
        value = row[f"{metric}_mean"]

        record[METRICS[metric]["label"]] = (
            format_value(float(value), METRICS[metric]["unit"])
            if pd.notna(value)
            else "N/A"
        )

    display_rows.append(record)

st.dataframe(
    pd.DataFrame(display_rows),
    hide_index=True,
    width="stretch",
)


# ---------------------------------------------------------
# All Experiments — Original Benchmark Results
# ---------------------------------------------------------

st.divider()
st.subheader("All Experiments — Original Benchmark Results")

native_summary = (
    RESULTS / "native_policy_compare" / "overall_summary.csv"
)

if native_summary.exists():
    original_experiments = pd.read_csv(native_summary)

    st.dataframe(
        original_experiments,
        hide_index=True,
        width="stretch",
    )

    st.download_button(
        label="Download Original Experiment Results",
        data=original_experiments.to_csv(index=False),
        file_name="overall_summary.csv",
        mime="text/csv",
    )
else:
    st.warning("Original benchmark CSV was not found.")