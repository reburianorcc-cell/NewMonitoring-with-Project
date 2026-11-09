import plotly.graph_objects as go
import streamlit as st

from .common import kpi_card, page_header
from .project_data import get_project_data


def render(project, report_date, project_year="All Years"):
    data = get_project_data()
    if not data:
        st.info("Upload the four SOCOCA Project Monitoring CSV files to populate this dashboard.")
        return
    page_header("PROJECT CONTROL DASHBOARD", show_motto=True)
    months = data["months"]
    planned_progress = data["target_physical_percent"]
    actual_progress = data["actual_physical_percent"]
    total_cost = data["total_project_cost"]
    last_actual = next((value for value in reversed(actual_progress) if value is not None), 0)
    actual_cost = next((value for value in reversed(data["actual_cost_cumulative"]) if value is not None), 0)
    reported_months = sum(value is not None for value in data["actual_cost_cumulative"])
    budget_percent = round(actual_cost / total_cost * 100) if total_cost else 0
    remaining = max(0, 12 - reported_months)
    main, side = st.columns([4, 1], gap="small")

    with main:
        cards = [
            ("Overall Progress", f"{last_actual:g}%", "Physical progress<br>accomplished", last_actual, "#16a6a1"),
            ("Time Elapsed", f"{reported_months / 12 * 100:.0f}%", f"{reported_months} of 12 project<br>months reported", reported_months / 12 * 100, "#2d7ce5"),
            ("Budget Utilized", f"{budget_percent}%", f"₱{actual_cost/1_000_000:.2f}M total<br>accomplishment", budget_percent, "#16a6a1"),
            ("Months Remaining", str(remaining), "Based on reported<br>project months", 100 - remaining / 12 * 100, "#153a57"),
        ]
        for col, card, key in zip(st.columns(4, gap="small"), cards, ["progress", "elapsed", "budget", "remaining"]):
            with col.container(border=True, key=f"whitecard_overview_{key}"):
                kpi_card(*card)

        chart_left, chart_right = st.columns([1.45, 1], gap="small")
        with chart_left.container(border=True, key="whitecard_planned_actual"):
            st.markdown('<div class="section-title">Physical Progress S-Curve</div>', unsafe_allow_html=True)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=months, y=planned_progress, name="Planned", mode="lines+markers", line=dict(color="#2d7ce5", width=3)))
            fig.add_trace(go.Scatter(x=months, y=actual_progress, name="Actual", mode="lines+markers", line=dict(color="#16a6a1", width=3)))
            fig.update_layout(height=300, margin=dict(l=12, r=8, t=3, b=8), paper_bgcolor="white", plot_bgcolor="white", legend=dict(orientation="h", y=-.18, x=.3), hovermode="x unified")
            fig.update_yaxes(title="Physical Progress (% of 10 km)", range=[0, 105], gridcolor="#e6edf3")
            fig.update_xaxes(title="Project Month", gridcolor="#eef3f7")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        with chart_right.container(border=True, key="whitecard_schedule_variance"):
            st.markdown('<div class="section-title">Physical Progress Variance</div>', unsafe_allow_html=True)
            variance = [round(actual - planned, 2) for actual, planned in zip(actual_progress, planned_progress)]
            chart = go.Figure(go.Scatter(x=months, y=variance, mode="lines+markers", line=dict(color="#123f66", width=2), marker=dict(size=8, color=["#ef5261" if value < -5 else "#123f66" for value in variance])))
            for value, label, color in [(5, "UCL", "#ef5261"), (0, "Mean", "#8596a6"), (-5, "LCL", "#ef5261")]:
                chart.add_hline(y=value, line=dict(color=color, dash="dash", width=1), annotation_text=label, annotation_position="right")
            chart.update_layout(height=300, margin=dict(l=8, r=40, t=3, b=8), paper_bgcolor="white", plot_bgcolor="white", showlegend=False)
            chart.update_yaxes(title="Variance (percentage points)", gridcolor="#e6edf3")
            chart.update_xaxes(title="Project Month", gridcolor="#eef3f7")
            st.plotly_chart(chart, use_container_width=True, config={"displayModeBar": False})

    with side:
        with st.container(border=True, key="whitecard_project_overview"):
            st.markdown('<div class="section-title">Project Overview</div>', unsafe_allow_html=True)
            status = "Completed" if last_actual >= 100 else "In Progress"
            st.markdown(f'''<div class="overview"><div class="row"><span>Project:</span><b>{data["project_name"]}</b></div><div class="row"><span>Unit:</span><b>{data["implementing_unit"]}</b></div><div class="row"><span>Target Area:</span><b>{data["target_area"]}</b></div><div class="row"><span>Beneficiaries:</span><b>{data["beneficiaries"]}</b></div><div class="row"><span>Total Cost:</span><b>₱{total_cost/1_000_000:.2f}M</b></div><div class="row"><span>Status:</span><b><i class="pill">{status}</i></b></div></div>''', unsafe_allow_html=True)
        with st.container(border=True, key="whitecard_project_health"):
            st.markdown('<div class="section-title">Project Health</div>', unsafe_allow_html=True)
            for metric, state in [("Cost", f"{budget_percent}% utilized"), ("Schedule", f"M{reported_months} reported"), ("Physical", f"{last_actual:g}% complete"), ("Turnover", "Completed" if last_actual >= 100 else "Pending")]:
                st.markdown(f'<div class="health-row"><b>{metric}</b><i class="dot ok"></i>{state}</div>', unsafe_allow_html=True)

    with st.container(border=True, key="whitecard_project_timeline"):
        st.markdown('<div class="section-title">Project Timeline</div>', unsafe_allow_html=True)
        st.markdown('''<div class="phase-wrap"><div class="phase done">Pre-implementation</div><div class="phase done">Survey & Mapping</div><div class="phase done">DED</div><div class="phase done">Road Works</div><div class="phase done">Turnover</div></div><div class="milestones"><div class="mile"><i class="diamond done"></i>NOA<br>M1</div><div class="mile"><i class="diamond done"></i>NTP Issued<br>M2</div><div class="mile"><i class="diamond done"></i>Survey Complete<br>M3</div><div class="mile"><i class="diamond done"></i>DED Complete<br>M4</div><div class="mile"><i class="diamond done"></i>3.5 km<br>M8</div><div class="mile"><i class="diamond done"></i>8 km<br>M10</div><div class="mile"><i class="diamond done"></i>10 km / Turnover<br>M12</div></div>''', unsafe_allow_html=True)
    st.caption(f"Source: Project Monitoring Template | {project_year} | Reporting date {report_date:%d %b %Y}")
