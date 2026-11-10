import html

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from .common import page_header, stat_card
from .project_data import get_project_data, percentages, risk_delay_by_month


def render(project, report_date, project_year="All Years"):
    data = get_project_data(project_year)
    if not data:
        st.info("Upload the four SOCOCA Project Monitoring CSV files to populate this dashboard.")
        return
    months = data["months"]
    target_cost = data["target_cost_cumulative"]
    actual_cost = data["actual_cost_cumulative"]
    target_percent = data["target_physical_percent"]
    actual_percent = data["actual_physical_percent"]
    risk_delays = risk_delay_by_month(data.get("risk_register"))
    visible_risk_delay = sum(risk_delays.get(int(month[1:]), 0) for month in months)
    planned = next((value for value in reversed(target_percent) if value is not None), 0)
    actual = next((value for value in reversed(actual_percent) if value is not None), 0)
    reported_months = sum(value is not None for value in actual_cost)
    total_months = data.get("total_months", len(months))
    page_header("PROJECT SCHEDULE", f"Monitor physical targets, milestones, and accomplishments across {total_months} project months.")
    cards = [("Planned Progress", f"{planned:g}%", "calendar_month"), ("Actual Progress", f"{actual:g}%", "task_alt"), ("Schedule Variance", f"{actual-planned:g}%", "trending_flat"), ("Completion", f"M{reported_months}", "flag")]
    for col, card, key in zip(st.columns(4, gap="small"), cards, ["planned", "actual", "variance", "completion"]):
        with col.container(border=True, key=f"whitecard_schedule_{key}"):
            stat_card(*card)

    component_names = [item["component"] for item in data.get("components", [])] or ["Project Implementation"]
    segment = max(1, total_months // len(component_names))
    schedule_rows = []
    for index, activity in enumerate(component_names):
        start = index * segment + 1
        finish = total_months if index == len(component_names) - 1 else min(total_months, (index + 1) * segment)
        schedule_rows.append([activity, start, max(1, finish - start + 1), "Project Phase"])
    schedule = pd.DataFrame(schedule_rows, columns=["Activity", "Start", "Duration", "Status"])

    gantt_col, status_col = st.columns([3, 1.05], gap="small")
    with gantt_col.container(border=True, key="whitecard_schedule_master"):
        st.markdown('<div class="section-title">Master Project Schedule</div>', unsafe_allow_html=True)
        gantt = go.Figure(go.Bar(y=schedule["Activity"], x=schedule["Duration"], base=schedule["Start"] - 1, orientation="h", name="Project Phase", marker_color="#16a6a1", hovertemplate="%{y}<br>Start: M%{base}<br>Duration: %{x} months<extra></extra>"))
        gantt.add_trace(go.Scatter(x=schedule["Start"] + schedule["Duration"] - 1, y=schedule["Activity"], mode="markers", name="Milestone", marker=dict(symbol="diamond", size=10, color="#164f9b")))
        gantt.update_layout(height=275, margin=dict(l=5, r=5, t=10, b=5), paper_bgcolor="white", plot_bgcolor="white", legend=dict(orientation="h", y=-.16))
        tick_step = max(1, total_months // 12)
        gantt.update_xaxes(range=[0, total_months + 1], tickmode="array", tickvals=list(range(1, total_months + 1, tick_step)), ticktext=[f"M{i}" for i in range(1, total_months + 1, tick_step)], gridcolor="#e5edf3", side="top")
        gantt.update_yaxes(title=None, gridcolor="#edf2f6")
        st.plotly_chart(gantt, use_container_width=True, config={"displayModeBar": False})

    month_statuses = [
        "Completed" if actual_cost[index] is not None and actual_percent[index] >= target_percent[index]
        else "Delayed" if actual_cost[index] is not None and actual_percent[index] < target_percent[index]
        else "Open"
        for index in range(len(months))
    ]
    status_counts = pd.Series(month_statuses).value_counts()
    with status_col.container(border=True, key="whitecard_schedule_status"):
        st.markdown('<div class="section-title">Schedule Status</div>', unsafe_allow_html=True)
        status_labels = ["Completed", "Open", "Delayed"]
        status_values = [int(status_counts.get(label, 0)) for label in status_labels]
        pie = go.Figure(go.Pie(labels=status_labels, values=status_values, hole=.58, marker=dict(colors=["#16a6a1", "#8fc4f4", "#ef5261"]), textinfo="none"))
        pie.add_annotation(text=f"<b>{len(months)}</b><br><span style='font-size:11px'>Months</span>", showarrow=False, font=dict(size=18, color="#15324b"))
        pie.update_layout(height=150, margin=dict(l=5, r=5, t=0, b=0), paper_bgcolor="white", showlegend=False)
        st.plotly_chart(pie, use_container_width=True, config={"displayModeBar": False})
        for label, value, color in zip(status_labels, status_values, ["#16a6a1", "#8fc4f4", "#ef5261"]):
            st.markdown(f'<div class="compact-health"><span>{label}</span><strong style="color:{color}">{value}</strong></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="compact-health"><span>Risk Delay</span><strong style="color:#ef7d45">{visible_risk_delay:g} days</strong></div>', unsafe_allow_html=True)

    progress_col, milestone_col = st.columns([1.5, 1], gap="small")
    with progress_col.container(border=True, key="whitecard_schedule_progress"):
        st.markdown('<div class="section-title">Planned vs Actual Progress</div>', unsafe_allow_html=True)
        figure = go.Figure()
        figure.add_trace(go.Scatter(x=months, y=percentages(target_cost, data["total_project_cost"]), name="Planned", mode="lines+markers", line=dict(color="#2d7ce5", width=3), marker=dict(size=6)))
        figure.add_trace(go.Scatter(x=months, y=percentages(actual_cost, data["total_project_cost"]), name="Actual", mode="lines+markers", line=dict(color="#16a6a1", width=3), marker=dict(size=6)))
        figure.update_layout(
            height=275,
            margin=dict(l=8, r=8, t=8, b=62),
            paper_bgcolor="white", plot_bgcolor="white",
            legend=dict(orientation="h", y=-.31, x=.5, xanchor="center", yanchor="top"),
            hovermode="x unified",
        )
        figure.update_yaxes(title="Cumulative Progress (%)", range=[0, 105], gridcolor="#e6edf3")
        figure.update_xaxes(title=dict(text="Project Month", standoff=10), gridcolor="#eef3f7")
        st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})

    with milestone_col.container(border=True, key="whitecard_schedule_milestones"):
        st.markdown('<div class="section-title">Monthly Physical Milestones</div>', unsafe_allow_html=True)
        milestones = pd.DataFrame({"Month": months, "Target": data["target_physical"], "Accomplishment": data["actual_physical"], "Status": month_statuses, "Risk Delay (Days)": [risk_delays.get(int(month[1:]), 0) for month in months]})
        status_colors = {
            "Completed": ("#e8f7ee", "#177245"),
            "Delayed": ("#fdecec", "#b42318"),
            "Open": ("#eaf2ff", "#175cd3"),
        }
        milestone_rows = []
        for _, row in milestones.iterrows():
            status = str(row["Status"])
            status_bg, status_text = status_colors.get(status, ("#edf3f8", "#405c73"))
            delay_days = float(row["Risk Delay (Days)"] or 0)
            target = "—" if pd.isna(row["Target"]) or str(row["Target"]).strip() == "" else html.escape(str(row["Target"]))
            accomplishment = "—" if pd.isna(row["Accomplishment"]) or str(row["Accomplishment"]).strip() == "" else html.escape(str(row["Accomplishment"]))
            milestone_rows.append(
                '<div class="milestone-table-row">'
                f'<div class="milestone-month">{html.escape(str(row["Month"]))}</div>'
                f'<div>{target}</div><div>{accomplishment}</div>'
                f'<div><span class="milestone-status" style="background:{status_bg};color:{status_text}">{html.escape(status)}</span></div>'
                f'<div class="milestone-delay">{delay_days:,.0f}d</div>'
                '</div>'
            )
        st.markdown(
            """
            <style>
            .milestone-table{height:275px;overflow-y:auto;overflow-x:hidden;border:1px solid #e1eaf1;
                border-radius:9px;background:#fff}
            .milestone-table-row{display:grid;grid-template-columns:48px minmax(100px,1fr)
                minmax(100px,1fr) 76px 44px;align-items:center;border-bottom:1px solid #e5edf3;min-width:0}
            .milestone-table-row>div{min-width:0;padding:8px 7px;font-size:10px;line-height:1.3;
                color:#233f58;white-space:normal;overflow-wrap:anywhere}
            .milestone-table-head{position:sticky;top:0;z-index:2;background:#f6f8fb;font-weight:700}
            .milestone-table-head>div{color:#667b8d;white-space:nowrap}
            .milestone-month{font-weight:800;color:#174f8a!important}
            .milestone-delay{text-align:center;font-weight:800;color:#b54708!important}
            .milestone-status{display:inline-block;max-width:100%;padding:3px 6px;border-radius:999px;
                font-size:8px;font-weight:800;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
            @media(max-width:900px){
                .milestone-table-row{grid-template-columns:42px minmax(85px,1fr) minmax(85px,1fr) 66px 38px}
                .milestone-table-row>div{padding:7px 4px;font-size:9px}
                .milestone-status{padding:3px 4px;font-size:7px}
            }
            </style>
            <div class="milestone-table">
              <div class="milestone-table-row milestone-table-head">
                <div>Month</div><div>Target</div><div>Accomplishment</div><div>Status</div><div>Risk</div>
              </div>
            """ + "".join(milestone_rows) + "</div>",
            unsafe_allow_html=True,
        )

    st.caption(f"Source: Project Monitoring Template | {project_year} | Reporting date {report_date:%d %b %Y}")
