# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Reusable Plotly charts. Owner: Fran.

Used by pages/3_Trends.py (full size) and by pages/1_Check_in.py (compact, next to the mascot).
Pages draw the figure with st.plotly_chart(fig). Contract: AGENTS.md, section 7.
"""
import plotly.graph_objects as go


def indicator_chart(astronaut: str, indicator: str, compact: bool = False) -> go.Figure:
    # STUB (Fran): one indicator over time from core.data.load_measurements(),
    # personal baseline from core.data.get_baseline(), colour bands, episode marks.
    # compact=True: smaller height, no legend, fewer labels.
    fig = go.Figure()
    fig.update_layout(
        title=None if compact else f"{indicator} (not built yet)",
        height=220 if compact else 420,
        margin=dict(l=10, r=10, t=10 if compact else 40, b=10),
    )
    return fig
