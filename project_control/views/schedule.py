import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from .common import page_header, stat_card
from .project_data import get_project_data, percentages


def render(project, report_date, project_year="All Years"):
    data = get_project_data()
    if not data:
        st.info("Upload the four SOCOCA Project Monitoring CSV files to populate this dashboard.")
        return
    months = data["months"]
    target_cost = data["target_cost_cumulative"]
    actual_cost = data["actual_cost_cumulative"]
    target_percent = data["target_physical_percent"]
    actual_percent = data["actual_physical_percent"]
    planned = next((value for value in reversed(target_percent) if value is not None), 0)
    actual = next((value for value in reversed(actual_percent) if value is not None), 0)
    reported_months = sum(value is not None for value in actual_cost)
    page_header("PROJECT SCHEDULE", "Monitor the 12-month physical targets, milestones, and accomplishments.")
    cards = [("Planned Progress", f"{planned:g}%", "calendar_month"), ("Actual Progress", f"{actual:g}%", "task_alt"), ("Schedule Variance", f"{actual-planned:g}%", "trending_flat"), ("Completion", f"M{reported_months}", "flag")]
    for col, card, key in zip(st.columns(4, gap="small"), cards, ["planned", "actual", "variance", "completion"]):
        with col.container(border=True, key=f"whitecard_schedule_{key}"):
            stat_card(*card)

    schedule = pd.DataFrame([
        ["Pre-implementation", "2026-01-01", "2026-02-28", "Completed"],
        ["Survey and Mapping", "2026-03-01", "2026-03-31", "Completed"],
        ["Detailed Engineering Design", "2026-04-01", "2026-04-30", "Completed"],
        ["Road Engineering Works", "2026-05-01", "2026-12-15", "Completed"],
        ["Monitoring and Supervision", "2026-03-01", "2026-12-20", "Completed"],
        ["Project Turnover to LGU", "2026-12-16", "2026-12-31", "Completed"],
    ], columns=["Activity", "Start", "Finish", "Status"])
    schedule[["Start", "Finish"]] = schedule[["Start", "Finish"]].apply(pd.to_datetime)

    gantt_col, status_col = st.columns([3, 1.05], gap="small")
    with gantt_col.container(border=True, key="whitecard_schedule_master"):
        st.markdown('<div class="section-title">12-Month Master Schedule</div>', unsafe_allow_html=True)
        gantt = px.timeline(schedule, x_start="Start", x_end="Finish", y="Activity", color="Status", color_discrete_map={"Completed": "#16a6a1"}, category_orders={"Activity": schedule["Activity"].tolist()[::-1]})
        milestones = pd.to_datetime(["2026-01-31", "2026-02-28", "2026-03-31", "2026-04-30", "2026-08-31", "2026-10-31", "2026-12-31"])
        milestone_tasks = ["Pre-implementation", "Pre-implementation", "Survey and Mapping", "Detailed Engineering Design", "Road Engineering Works", "Road Engineering Works", "Project Turnover to LGU"]
        gantt.add_trace(go.Scatter(x=milestones, y=milestone_tasks, mode="markers", name="Milestone", marker=dict(symbol="diamond", size=10, color="#164f9b")))
        gantt.update_layout(height=275, margin=dict(l=5, r=5, t=10, b=5), paper_bgcolor="white", plot_bgcolor="white", legend=dict(orientation="h", y=-.16))
        gantt.update_xaxes(range=[pd.Timestamp("2026-01-01"), pd.Timestamp("2026-12-31")], tickformat="M%-m", dtick="M1", gridcolor="#e5edf3", side="top")
        gantt.update_yaxes(title=None, gridcolor="#edf2f6")
        st.plotly_chart(gantt, use_container_width=True, config={"displayModeBar": False})

    with status_col.container(border=True, key="whitecard_schedule_status"):
        st.markdown('<div class="section-title">Schedule Status</div>', unsafe_allow_html=True)
        pie = go.Figure(go.Pie(labels=["Completed", "Open", "Delayed"], values=[6, 0, 0], hole=.58, marker=dict(colors=["#16a6a1", "#8fc4f4", "#ef5261"]), textinfo="none"))
        pie.add_annotation(text="<b>6</b><br><span style='font-size:11px'>Components</span>", showarrow=False, font=dict(size=18, color="#15324b"))
        pie.update_layout(height=150, margin=dict(l=5, r=5, t=0, b=0), paper_bgcolor="white", showlegend=False)
        st.plotly_chart(pie, use_container_width=True, config={"displayModeBar": False})
        for label, value, color in [("Completed", 6, "#16a6a1"), ("Open", 0, "#8fc4f4"), ("Delayed", 0, "#ef5261")]:
            st.markdown(f'<div class="compact-health"><span>{label}</span><strong style="color:{color}">{value}</strong></div>', unsafe_allow_html=True)

    progress_col, milestone_col = st.columns([1.5, 1], gap="small")
    with progress_col.container(border=True, key="whitecard_schedule_progress"):
        st.markdown('<div class="section-title">Planned vs Actual Progress</div>', unsafe_allow_html=True)
        figure = go.Figure()
        figure.add_trace(go.Scatter(x=months, y=percentages(target_cost, data["total_project_cost"]), name="Planned", mode="lines+markers", line=dict(color="#2d7ce5", width=3)))
        figure.add_trace(go.Scatter(x=months, y=percentages(actual_cost, data["total_project_cost"]), name="Actual", mode="lines+markers", line=dict(color="#16a6a1", width=3)))
        figure.update_layout(height=230, margin=dict(l=5, r=5, t=0, b=5), paper_bgcolor="white", plot_bgcolor="white", legend=dict(orientation="h", y=-.2, x=.25))
        figure.update_yaxes(title="Cumulative Progress (%)", range=[0, 105], gridcolor="#e6edf3")
        figure.update_xaxes(title="Project Month", gridcolor="#eef3f7")
        st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})

    with milestone_col.container(border=True, key="whitecard_schedule_milestones"):
        st.markdown('<div class="section-title">Monthly Physical Milestones</div>', unsafe_allow_html=True)
        statuses = [
            "Completed" if actual_percent[index] >= target_percent[index]
            else "Delayed" if actual_cost[index] is not None else "Open"
            for index in range(12)
        ]
        milestones = pd.DataFrame({"Month": months, "Target": data["target_physical"], "Accomplishment": data["actual_physical"], "Status": statuses})
        st.dataframe(milestones, hide_index=True, use_container_width=True, height=230)

    st.caption(f"Source: Project Monitoring Template | {project_year} | Reporting date {report_date:%d %b %Y}")
