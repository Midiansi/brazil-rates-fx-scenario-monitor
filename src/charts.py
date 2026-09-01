from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


COLORS = ["#0B6E4F", "#137CBD", "#E07A1F", "#6F4E9C", "#A23B3B", "#65737E"]


def _style(fig: go.Figure, *, y_title: str) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        margin=dict(l=20, r=20, t=60, b=20),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        yaxis_title=y_title,
        xaxis_title="Date",
    )
    return fig


def focus_expectations_chart(frame: pd.DataFrame, indicator: str) -> go.Figure:
    fig = go.Figure()
    clean = frame.dropna(subset=["Date", "Reference year", "Median"]).sort_values("Date")
    for index, (year, group) in enumerate(clean.groupby("Reference year", sort=True)):
        fig.add_trace(
            go.Scatter(
                x=group["Date"],
                y=group["Median"],
                mode="lines",
                name=str(int(year)),
                line=dict(width=2, color=COLORS[index % len(COLORS)]),
                hovertemplate=(
                    "%{x|%d %b %Y}<br>%{y:.4f}% p.a.<extra></extra>"
                    if indicator == "Selic"
                    else "%{x|%d %b %Y}<br>%{y:.4f}%<extra></extra>"
                ),
            )
        )
    fig.update_layout(title=f"Evolution of annual {indicator} median expectations")
    y_title = "Median expectation (% p.a.)" if indicator == "Selic" else "Median annual inflation (%)"
    return _style(fig, y_title=y_title)


def ptax_chart(frame: pd.DataFrame) -> go.Figure:
    clean = frame.dropna(subset=["Date", "Midpoint"]).sort_values("Date")
    if not clean.empty:
        clean = clean.loc[clean["Date"] >= clean["Date"].max() - pd.DateOffset(months=3)]
    fig = go.Figure(
        go.Scatter(
            x=clean["Date"],
            y=clean["Midpoint"],
            mode="lines",
            name="PTAX midpoint",
            line=dict(width=2.5, color="#137CBD"),
            hovertemplate="%{x|%d %b %Y}<br>R$ %{y:.5f} per USD<extra></extra>",
        )
    )
    fig.update_layout(title="USD/BRL PTAX midpoint — latest three months")
    return _style(fig, y_title="BRL per USD")


def policy_diff_chart(frame: pd.DataFrame) -> go.Figure:
    clean = frame.dropna(subset=["Date", "Policy differential"]).sort_values("Date")
    fig = go.Figure(
        go.Scatter(
            x=clean["Date"],
            y=clean["Policy differential"],
            mode="lines",
            name="Selic target − Fed midpoint",
            line=dict(width=2.5, color="#0B6E4F"),
            hovertemplate="%{x|%d %b %Y}<br>%{y:.2f} pp<extra></extra>",
        )
    )
    fig.add_hline(y=0, line_width=1, line_dash="dot", line_color="#65737E")
    fig.update_layout(title="Brazil–US policy-rate differential")
    return _style(fig, y_title="Percentage points")
