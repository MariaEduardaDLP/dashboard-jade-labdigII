"""Gráficos com cores consistentes e rótulos em português."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from jade.catalog import MESSAGES, URGENCIES, URGENCY_COLORS


def _style(figure: go.Figure, height: int = 370) -> go.Figure:
    figure.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=20, b=8),
        font=dict(family="sans-serif", color="#102846", size=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend_title_text="",
    )
    figure.update_xaxes(showgrid=False, automargin=True)
    figure.update_yaxes(gridcolor="#E6E6DF", zeroline=False, automargin=True)
    return figure


def hourly_chart(counts: pd.DataFrame) -> go.Figure:
    figure = px.line(
        counts, x="hour", y="count", color="message",
        color_discrete_map={message.label: message.color for message in MESSAGES},
        labels={"hour": "Horário do dia", "count": "Solicitações", "message": "Mensagem"},
    )
    figure.update_traces(
        line_width=2.5,
        hovertemplate="%{x:02d}h · %{y} solicitações<extra>%{fullData.name}</extra>",
    )
    figure.update_layout(legend=dict(orientation="h", y=-0.25, x=0), hovermode="x unified")
    figure.update_xaxes(tickvals=list(range(0, 24, 3)), ticktext=[f"{hour:02d}h" for hour in range(0, 24, 3)])
    figure.update_yaxes(rangemode="tozero", dtick=1 if counts["count"].max() < 8 else None)
    return _style(figure, 440)


def usage_chart(counts: pd.DataFrame) -> go.Figure:
    ordered = counts.sort_values("count", ascending=True, kind="stable")
    figure = px.bar(
        ordered, x="count", y="message", color="urgency", orientation="h",
        color_discrete_map=URGENCY_COLORS, text="count",
        labels={"count": "Solicitações", "message": "", "urgency": "Urgência"},
        category_orders={"urgency": list(URGENCIES)},
    )
    figure.update_traces(textposition="outside", cliponaxis=False)
    figure.update_layout(showlegend=False, bargap=0.35)
    figure.update_yaxes(categoryorder="array", categoryarray=ordered["message"].tolist())
    figure.update_xaxes(rangemode="tozero")
    return _style(figure, 420)


def urgency_chart(counts: pd.DataFrame) -> go.Figure:
    figure = px.pie(
        counts.loc[counts["count"] > 0], values="count", names="urgency", color="urgency",
        hole=0.72, color_discrete_map=URGENCY_COLORS,
        category_orders={"urgency": list(URGENCIES)},
    )
    figure.update_traces(
        textinfo="none", sort=False,
        hovertemplate="Urgência %{label}<br>%{value} solicitações · %{percent}<extra></extra>",
    )
    figure.update_layout(
        legend=dict(orientation="h", y=-0.05, x=0.5, xanchor="center"),
        annotations=[dict(text=f"<b>{int(counts['count'].sum())}</b><br>solicitações",
                          x=0.5, y=0.5, showarrow=False, font_size=19)],
    )
    return _style(figure, 300)
