import plotly.graph_objects as go
import streamlit as st

from .common import kpi_card, page_header
from .project_data import get_project_data, risk_delay_by_month


def render(project, report_date, project_year="All Years"):
    data = get_project_data(project_year)
    if not data:
        st.info("Upload the four SOCOCA Project Monitoring CSV files to populate this dashboard.")
        return
    page_header("PROJECT CONTROL DASHBOARD", show_motto=True)
    months = data["months"]
    planned_progress = data["target_physical_percent"]
    actual_progress = data["actual_physical_percent"]
    risk_delays = risk_delay_by_month(data.get("risk_register"))
    visible_risk_delays = {f"M{month}": days for month, days in risk_delays.items() if f"M{month}" in months}
    total_cost = data["total_project_cost"]
    last_actual = next((value for value in reversed(actual_progress) if value is not None), 0)
    actual_cost = next((value for value in reversed(data["actual_cost_cumulative"]) if value is not None), 0)
    overall_data = get_project_data()
    total_months = overall_data.get("total_months", len(overall_data["months"]))
    reported_months = sum(value is not None for value in overall_data["actual_cost_cumulative"])
    budget_percent = round(actual_cost / total_cost * 100) if total_cost else 0
    remaining = max(0, total_months - reported_months)
    last_planned = next((value for value in reversed(planned_progress) if value is not None), 0)
    current_variance = round(last_actual - last_planned, 2)
    visible_delay_days = sum(visible_risk_delays.values())
    main, side = st.columns([4, 1], gap="small")

    with main:
        cards = [
            ("Overall Progress", f"{last_actual:g}%", "Physical progress<br>accomplished", last_actual, "#16a6a1"),
            ("Time Elapsed", f"{reported_months / total_months * 100:.0f}%", f"{reported_months} of {total_months} project<br>months reported", reported_months / total_months * 100, "#2d7ce5"),
            ("Budget Utilized", f"{budget_percent}%", f"₱{actual_cost/1_000_000:.2f}M total<br>accomplishment", budget_percent, "#16a6a1"),
            ("Months Remaining", str(remaining), f"Risk delay: {sum(risk_delays.values()):g} days<br>across the project", 100 - remaining / total_months * 100, "#153a57"),
        ]
        for col, card, key in zip(st.columns(4, gap="small"), cards, ["progress", "elapsed", "budget", "remaining"]):
            with col.container(border=True, key=f"whitecard_overview_{key}"):
                kpi_card(*card)

        chart_left, chart_right = st.columns([1.45, 1], gap="small")
        with chart_left.container(border=True, key="whitecard_planned_actual"):
            st.markdown('<div class="section-title">Physical Progress S-Curve</div>', unsafe_allow_html=True)
            variance_color = "#177245" if current_variance >= 0 else "#b42318"
            st.markdown(
                f'''<div style="display:flex;gap:7px;flex-wrap:wrap;margin:1px 0 5px">
                <span style="background:#edf4ff;color:#175cd3;border-radius:999px;padding:4px 9px;font-size:10px;font-weight:700">Planned {last_planned:g}%</span>
                <span style="background:#e8f7f5;color:#087a76;border-radius:999px;padding:4px 9px;font-size:10px;font-weight:700">Actual {last_actual:g}%</span>
                <span style="background:#f4f6f8;color:{variance_color};border-radius:999px;padding:4px 9px;font-size:10px;font-weight:700">Variance {current_variance:+g} pp</span>
                <span style="background:#fff0e8;color:#b54708;border-radius:999px;padding:4px 9px;font-size:10px;font-weight:700">Risk delay {visible_delay_days:g} days</span>
                </div>''',
                unsafe_allow_html=True,
            )
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=months, y=planned_progress, name="Planned", mode="lines+markers",
                line=dict(color="#2d7ce5", width=3), marker=dict(size=6),
                hovertemplate="%{x}<br>Planned: %{y:g}%<extra></extra>",
            ))
            progress_variance = [
                round(actual - planned, 2) if actual is not None and planned is not None else None
                for actual, planned in zip(actual_progress, planned_progress)
            ]
            fig.add_trace(go.Scatter(
                x=months, y=actual_progress, name="Actual", mode="lines+markers",
                line=dict(color="#16a6a1", width=3), marker=dict(size=6),
                customdata=progress_variance,
                hovertemplate="%{x}<br>Actual: %{y:g}%<br>Variance: %{customdata:+g} pp<extra></extra>",
            ))
            if visible_risk_delays:
                delay_values = list(visible_risk_delays.values())
                fig.add_trace(go.Scatter(
                    x=list(visible_risk_delays),
                    y=[103] * len(visible_risk_delays),
                    name="Risk-related delay",
                    mode="markers",
                    customdata=delay_values,
                    marker=dict(
                        symbol="triangle-down", size=10,
                        color=["#ef5261" if value >= 8 else "#f59e0b" for value in delay_values],
                        line=dict(color="white", width=1),
                    ),
                    hovertemplate="%{x}<br>Risk-related delay: %{customdata:.0f} days<extra></extra>",
                ))
                for month, days in visible_risk_delays.items():
                    fig.add_vline(x=month, line=dict(color="#ef5261", width=.7, dash="dot"), opacity=.22)
            fig.update_layout(height=270, margin=dict(l=12, r=8, t=3, b=8), paper_bgcolor="white", plot_bgcolor="white", legend=dict(orientation="h", y=-.2, x=.22), hovermode="closest")
            fig.update_yaxes(title="Physical Progress (% of 10 km)", range=[0, 108], gridcolor="#e6edf3")
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
        checkpoints = sorted(set([1, max(1, round(total_months * .25)), max(1, round(total_months * .5)), max(1, round(total_months * .75)), total_months]))
        labels = ["Start", "25% Duration", "Midpoint", "75% Duration", "Target Completion"][-len(checkpoints):]
        milestone_html = "".join(f'<div class="mile"><i class="diamond done"></i>{label}<br>M{month}</div>' for label, month in zip(labels, checkpoints))
        st.markdown(f'<div class="phase-wrap"><div class="phase done">Mobilization</div><div class="phase done">Implementation</div><div class="phase active">Monitoring</div><div class="phase">Completion</div></div><div class="milestones" style="grid-template-columns:repeat({len(checkpoints)},1fr)">{milestone_html}</div>', unsafe_allow_html=True)
    st.caption(f"Source: Project Monitoring Template | {project_year} | Reporting date {report_date:%d %b %Y}")
