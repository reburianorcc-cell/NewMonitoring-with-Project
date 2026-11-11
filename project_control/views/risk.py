import html
import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .common import page_header, stat_card
from .project_data import get_project_data


RISK_COLUMNS = [
    "Risk ID", "Risk Description", "Category", "Observation", "Potential Impact",
    "Affected Month", "Delay Days", "Description of the Impact", "Cost Impact",
    "Owner", "Mitigation Action", "Deadline for the Mitigation Action", "Status",
]

RISK_COLUMN_ALIASES = {
    "risk_id": "Risk ID",
    "risk_description": "Risk Description",
    "category": "Category",
    "observation": "Observation",
    "probability": "Observation",
    "potential_impact": "Potential Impact",
    "impact": "Potential Impact",
    "affected_month": "Affected Month",
    "delay_days": "Delay Days",
    "description_of_the_impact": "Description of the Impact",
    "schedule_impact": "Description of the Impact",
    "cost_impact": "Cost Impact",
    "owner": "Owner",
    "mitigation_action": "Mitigation Action",
    "deadline_for_the_mitigation_action": "Deadline for the Mitigation Action",
    "due_date": "Deadline for the Mitigation Action",
    "status": "Status",
}


def _normalize(value):
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _score(value):
    labels = {"very low": 1, "low": 2, "medium": 3, "moderate": 3, "high": 4, "very high": 5, "critical": 5}
    text = str(value or "").strip().lower()
    if text in labels:
        return labels[text]
    number = pd.to_numeric(value, errors="coerce")
    return int(max(1, min(5, number))) if pd.notna(number) else 1


def _month_number(value):
    match = re.search(r"(\d+)", str(value or ""))
    return int(match.group(1)) if match else None


def _money(value):
    cleaned = re.sub(r"[^0-9.\-]", "", str(value or ""))
    return float(cleaned) if cleaned not in {"", "-", "."} else 0.0


def _prepare_risks(frame, project_year):
    def canonical_column(column):
        normalized = _normalize(column)
        if normalized.startswith("affected_month"):
            return "Affected Month"
        return RISK_COLUMN_ALIASES.get(normalized, column)

    renamed = frame.rename(columns={column: canonical_column(column) for column in frame.columns}).copy()
    for column in RISK_COLUMNS:
        if column not in renamed:
            renamed[column] = None
    risks = renamed[RISK_COLUMNS].dropna(how="all").copy()
    risks["Observation Score"] = risks["Observation"].map(_score)
    risks["Potential Impact Score"] = risks["Potential Impact"].map(_score)
    risks["Risk Score"] = risks["Observation Score"] * risks["Potential Impact Score"]
    risks["Month Number"] = risks["Affected Month"].map(_month_number)
    risks["Delay Days"] = pd.to_numeric(risks["Delay Days"], errors="coerce").fillna(0).clip(lower=0)
    risks["Cost Impact Value"] = risks["Cost Impact"].map(_money)
    risks["Status"] = risks["Status"].fillna("Unspecified").astype(str).replace("", "Unspecified")
    risks["Category"] = risks["Category"].fillna("Unspecified").astype(str).replace("", "Unspecified")
    if project_year != "All Years":
        year = int(re.search(r"(\d+)", project_year).group(1))
        start, end = (year - 1) * 12 + 1, year * 12
        risks = risks[risks["Month Number"].between(start, end, inclusive="both")]
    return risks


def render(project, report_date, project_year="All Years"):
    data = get_project_data(project_year)
    page_header("PROJECT RISK MANAGEMENT", "Identify risks and measure their effect on the project schedule.")
    risk_frame = data.get("risk_register", pd.DataFrame()) if data else pd.DataFrame()
    # A risk file may be uploaded independently of the four main monitoring
    # tables. Prefer the active project's table cache when the assembled data
    # object has not refreshed yet.
    if risk_frame.empty:
        risk_frame = st.session_state.get("project_monitoring_tables", {}).get(
            "Project Risks", pd.DataFrame()
        )
    if risk_frame.empty:
        st.info("No project risk register has been uploaded. Upload a Project Risks CSV or Excel file from Data Upload to generate the risk charts.")
        st.caption(f"Risk status for {project} | {project_year} | {report_date:%d %b %Y}")
        return

    risks = _prepare_risks(risk_frame, project_year)
    if risks.empty:
        st.info(f"No risk records are available for {project_year}.")
        return

    open_mask = ~risks["Status"].str.casefold().isin({"closed", "mitigated", "resolved"})
    metrics = [
        ("Total Risks", f"{len(risks):,}", "warning"),
        ("Critical Risks", f"{(risks['Risk Score'] >= 20).sum():,}", "error"),
        ("High Risks", f"{risks['Risk Score'].between(12, 19).sum():,}", "priority_high"),
        ("Open Risks", f"{open_mask.sum():,}", "pending_actions"),
        ("Risk Delay", f"{risks['Delay Days'].sum():,.0f} days", "schedule"),
    ]
    for col, (label, value, icon), index in zip(st.columns(5, gap="small"), metrics, range(5)):
        with col.container(border=True, key=f"whitecard_risk_kpi_{index}"):
            stat_card(label, value, icon)

    matrix_col, status_col, delay_col = st.columns([1.25, .8, 1.35], gap="small")
    with matrix_col.container(border=True, key="whitecard_risk_matrix"):
        st.markdown('<div class="section-title">Risk Matrix</div>', unsafe_allow_html=True)
        heat = go.Figure(go.Heatmap(
            z=[[1, 1, 2, 2, 3], [1, 2, 2, 3, 3], [2, 2, 3, 3, 4], [2, 3, 3, 4, 4], [3, 3, 4, 4, 5]],
            x=[1, 2, 3, 4, 5], y=[1, 2, 3, 4, 5],
            colorscale=[[0, "#56c58a"], [.5, "#ffe174"], [1, "#f15b5b"]], showscale=False, hoverinfo="skip",
        ))
        heat.add_trace(go.Scatter(
            x=risks["Potential Impact Score"], y=risks["Observation Score"], mode="markers",
            customdata=risks[["Risk ID", "Risk Description", "Delay Days"]],
            marker=dict(size=11, color="#174f8a", line=dict(color="white", width=2)),
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<br>Delay: %{customdata[2]} days<extra></extra>",
        ))
        heat.update_layout(height=285, autosize=True, margin=dict(l=35, r=12, t=4, b=35), paper_bgcolor="white", plot_bgcolor="white", showlegend=False)
        heat.update_xaxes(title="Potential Impact", dtick=1, fixedrange=True)
        heat.update_yaxes(title="Observation", dtick=1, fixedrange=True)
        st.plotly_chart(heat, width="stretch", config={"displayModeBar": False, "responsive": True})

    with status_col.container(border=True, key="whitecard_risk_status"):
        st.markdown('<div class="section-title">Risk Status</div>', unsafe_allow_html=True)
        status_counts = risks["Status"].value_counts()
        pie = go.Figure(go.Pie(labels=status_counts.index, values=status_counts.values, hole=.58, marker=dict(colors=["#2569bd", "#16a6a1", "#61c28b", "#8ca0b5", "#f0ad4e"])))
        pie.update_layout(height=285, autosize=True, margin=dict(l=4, r=4, t=4, b=55), paper_bgcolor="white", legend=dict(orientation="h", y=-.08, x=.5, xanchor="center", font=dict(size=9)))
        st.plotly_chart(pie, width="stretch", config={"displayModeBar": False, "responsive": True})

    with delay_col.container(border=True, key="whitecard_risk_delay"):
        st.markdown('<div class="section-title">Delay Due to Risk</div>', unsafe_allow_html=True)
        delay = risks.dropna(subset=["Month Number"]).groupby("Month Number", as_index=False)["Delay Days"].sum().sort_values("Month Number")
        delay["Month"] = delay["Month Number"].astype(int).map(lambda value: f"M{value}")
        chart = go.Figure(go.Bar(x=delay["Month"], y=delay["Delay Days"], marker_color="#ef7d45", hovertemplate="%{x}<br>%{y} delay days<extra></extra>"))
        chart.update_layout(height=285, autosize=True, margin=dict(l=42, r=10, t=4, b=40), paper_bgcolor="white", plot_bgcolor="white", showlegend=False)
        chart.update_yaxes(title="Delay Days", gridcolor="#e6edf3", fixedrange=True)
        chart.update_xaxes(title="Affected Project Month", fixedrange=True)
        st.plotly_chart(chart, width="stretch", config={"displayModeBar": False, "responsive": True})

    register_col, summary_col = st.columns([1.85, 1], gap="small")
    with register_col.container(border=True, key="whitecard_risk_register"):
        st.markdown('<div class="section-title">Project Risk Register</div>', unsafe_allow_html=True)
        status_colors = {
            "open": ("#fdecec", "#b42318"),
            "in progress": ("#fff4d6", "#8a5700"),
            "monitoring": ("#eaf2ff", "#175cd3"),
            "mitigated": ("#e8f7ee", "#177245"),
            "closed": ("#edf3f8", "#405c73"),
        }
        register_rows = []
        for _, risk in risks.iterrows():
            status = str(risk["Status"])
            status_bg, status_text = status_colors.get(status.casefold(), ("#edf3f8", "#405c73"))
            delay = float(risk["Delay Days"])
            cells = [
                html.escape(str(risk["Risk ID"])),
                html.escape(str(risk["Risk Description"])),
                html.escape(str(risk["Category"])),
                html.escape(str(risk["Affected Month"])),
                f"{delay:,.0f}",
            ]
            register_rows.append(
                '<div class="risk-register-row">'
                f'<div class="risk-id">{cells[0]}</div>'
                f'<div class="risk-description">{cells[1]}</div>'
                f'<div>{cells[2]}</div>'
                f'<div>{cells[3]}</div>'
                f'<div class="risk-delay">{cells[4]}</div>'
                f'<div><span class="risk-status" style="background:{status_bg};color:{status_text}">{html.escape(status)}</span></div>'
                '</div>'
            )
        st.markdown(
            """
            <style>
            .risk-register-wrap{width:100%;height:480px;max-height:480px;overflow-y:auto;overflow-x:hidden;
                border:1px solid #e1eaf1;border-radius:9px;background:#fff}
            .risk-register-row{display:grid;grid-template-columns:82px minmax(150px,2.4fr)
                minmax(90px,.9fr) 58px 58px 92px;gap:0;align-items:center;
                border-bottom:1px solid #e5edf3;min-width:0}
            .risk-register-row>div{min-width:0;padding:9px 8px;font-size:11px;line-height:1.32;
                color:#233f58;overflow-wrap:anywhere}
            .risk-register-head{position:sticky;top:0;z-index:2;background:#f6f8fb;font-weight:700}
            .risk-register-head>div{color:#667b8d;white-space:nowrap}
            .risk-id{font-weight:700;color:#174f8a!important;white-space:nowrap}
            .risk-description{white-space:normal}
            .risk-delay{text-align:center;font-weight:800;color:#b54708!important}
            .risk-status{display:inline-block;max-width:100%;padding:3px 7px;border-radius:999px;
                font-size:9px;font-weight:800;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
            @media(max-width:900px){
                .risk-register-wrap{height:430px;max-height:430px}
                .risk-register-row{grid-template-columns:76px minmax(135px,2fr) 82px 48px 50px 78px}
                .risk-register-row>div{padding:8px 5px;font-size:10px}
                .risk-status{padding:3px 5px;font-size:8px}
            }
            </style>
            <div class="risk-register-wrap">
              <div class="risk-register-row risk-register-head">
                <div>Risk ID</div><div>Risk Description</div><div>Category</div>
                <div>Month</div><div>Delay</div><div>Status</div>
              </div>
            """ + "".join(register_rows) + "</div>",
            unsafe_allow_html=True,
        )

    with summary_col:
        with st.container(border=True, key="whitecard_risk_categories"):
            st.markdown('<div class="section-title">Risks by Category</div>', unsafe_allow_html=True)
            category_counts = risks["Category"].value_counts().sort_values()
            category_chart = go.Figure(go.Bar(y=category_counts.index, x=category_counts.values, orientation="h", marker_color="#4d96dd"))
            category_chart.update_layout(
                height=176, autosize=True,
                margin=dict(l=8, r=12, t=0, b=26),
                paper_bgcolor="white", plot_bgcolor="white", showlegend=False,
                bargap=.22,
            )
            category_chart.update_xaxes(dtick=1, gridcolor="#e6edf3", fixedrange=True, title=None)
            category_chart.update_yaxes(automargin=True, fixedrange=True, tickfont=dict(size=10))
            st.plotly_chart(category_chart, width="stretch", config={"displayModeBar": False, "responsive": True})
        with st.container(border=True, key="whitecard_risk_actions"):
            st.markdown('<div class="section-title">Highest Delay Risks</div>', unsafe_allow_html=True)
            highest = risks.nlargest(4, "Delay Days")[["Risk ID", "Risk Description", "Delay Days"]]
            rows = []
            for _, risk in highest.iterrows():
                risk_id = html.escape(str(risk["Risk ID"]))
                description = html.escape(str(risk["Risk Description"]))
                delay_days = float(risk["Delay Days"])
                delay_label = f"{delay_days:,.0f} days"
                rows.append(
                    '<div style="display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px;'
                    'align-items:center;padding:9px 2px;border-bottom:1px solid #edf2f6">'
                    f'<div style="min-width:0"><div style="font-size:11px;font-weight:800;color:#174f8a">{risk_id}</div>'
                    f'<div style="font-size:11px;line-height:1.35;color:#405c73;white-space:normal;overflow-wrap:anywhere">{description}</div></div>'
                    f'<span style="white-space:nowrap;background:#fff0e8;color:#b54708;border-radius:999px;'
                    f'padding:4px 8px;font-size:10px;font-weight:800">{delay_label}</span></div>'
                )
            st.markdown("".join(rows), unsafe_allow_html=True)

    st.caption(f"Risk status for {project} | {project_year} | {report_date:%d %b %Y}")
