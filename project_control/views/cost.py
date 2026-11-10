import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .common import page_header, stat_card
from .project_data import get_project_data, monthly_amounts


def peso_millions(value):
    return f"₱{value / 1_000_000:.2f}M"


def render(project, report_date, project_year="All Years"):
    data = get_project_data(project_year)
    if not data:
        st.info("Upload the four SOCOCA Project Monitoring CSV files to populate this dashboard.")
        return
    months = data["months"]
    target_cost = data["target_cost_cumulative"]
    actual_cost = data["actual_cost_cumulative"]
    components = data["components"]
    total_cost = data["total_project_cost"]
    page_header("PROJECT COST CONTROL", "Monitor monthly cost targets, accomplishments, and component budgets.")
    component_metrics = [(item["component"], peso_millions(item["budget"]), "account_balance_wallet") for item in components[:4]]
    metrics = [("Approved Budget", peso_millions(total_cost), "account_balance_wallet"), *component_metrics]
    while len(metrics) < 5:
        metrics.append(("Project Component", "₱0.00M", "account_balance_wallet"))
    for col, item, index in zip(st.columns(5, gap="small"), metrics, range(5)):
        with col.container(border=True, key=f"whitecard_cost_kpi_{index}"):
            stat_card(*item)

    content, side = st.columns([4, 1], gap="small")
    with content:
        curve_col, budget_col = st.columns([1.55, 1.2], gap="small")
        with curve_col.container(border=True, key="whitecard_cost_scurve"):
            st.markdown('<div class="section-title">Cost S-Curve</div>', unsafe_allow_html=True)
            figure = go.Figure()
            figure.add_trace(go.Scatter(x=months, y=[v / 1_000_000 if v is not None else None for v in target_cost], name="Target", mode="lines+markers", line=dict(color="#2d7ce5", width=3)))
            figure.add_trace(go.Scatter(x=months, y=[v / 1_000_000 if v is not None else None for v in actual_cost], name="Accomplishment", mode="lines+markers", line=dict(color="#16a6a1", width=3)))
            figure.update_layout(height=285, margin=dict(l=8, r=8, t=3, b=8), paper_bgcolor="white", plot_bgcolor="white", legend=dict(orientation="h", y=-.18), hovermode="x unified")
            figure.update_yaxes(title="Cumulative Cost (₱ Millions)", gridcolor="#e6edf3")
            figure.update_xaxes(title="Project Month", gridcolor="#eef3f7")
            st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})

        with budget_col.container(border=True, key="whitecard_cost_work_package"):
            st.markdown('<div class="section-title">Budget by Project Component</div>', unsafe_allow_html=True)
            labels = [item["component"] for item in components][::-1]
            budgets = [item["budget"] / 1_000_000 for item in components][::-1]
            chart = go.Figure(go.Bar(y=labels, x=budgets, orientation="h", marker_color=["#8fc4f4", "#16a6a1", "#2d7ce5", "#123f66"]))
            chart.update_layout(height=285, margin=dict(l=5, r=5, t=3, b=8), paper_bgcolor="white", plot_bgcolor="white", showlegend=False)
            chart.update_xaxes(title="Budget (₱ Millions)", gridcolor="#e6edf3")
            st.plotly_chart(chart, use_container_width=True, config={"displayModeBar": False})

        cash_col, summary_col = st.columns([1, 1.3], gap="small")
        with cash_col.container(border=True, key="whitecard_cost_cashflow"):
            st.markdown('<div class="section-title">Monthly Cost Flow</div>', unsafe_allow_html=True)
            target_monthly = [v / 1_000_000 if v is not None else None for v in monthly_amounts(target_cost, data.get("target_cost_previous", 0.0))]
            actual_monthly = [v / 1_000_000 if v is not None else None for v in monthly_amounts(actual_cost, data.get("actual_cost_previous", 0.0))]
            chart = go.Figure([go.Bar(x=months, y=target_monthly, name="Target", marker_color="#2d7ce5"), go.Bar(x=months, y=actual_monthly, name="Actual", marker_color="#16a6a1")])
            chart.update_layout(barmode="group", height=235, margin=dict(l=5, r=5, t=3, b=5), paper_bgcolor="white", plot_bgcolor="white", legend=dict(orientation="h", y=-.2))
            chart.update_yaxes(title="₱ Millions", gridcolor="#e6edf3")
            st.plotly_chart(chart, use_container_width=True, config={"displayModeBar": False})
        with summary_col.container(border=True, key="whitecard_cost_summary"):
            st.markdown('<div class="section-title">Component Cost Summary</div>', unsafe_allow_html=True)
            summary = pd.DataFrame({"Project Component": [item["component"] for item in components], "Budget": [peso_millions(item["budget"]) for item in components], "Final Accomplishment": [peso_millions(item["budget"]) for item in components], "Variance": ["₱0"] * len(components), "Status": ["Completed"] * len(components)})
            summary_rows = []
            for _, row in summary.iterrows():
                summary_rows.append(
                    '<div class="cost-summary-row">'
                    f'<div class="cost-component">{html.escape(str(row["Project Component"]))}</div>'
                    f'<div>{html.escape(str(row["Budget"]))}</div>'
                    f'<div>{html.escape(str(row["Final Accomplishment"]))}</div>'
                    f'<div class="cost-variance">{html.escape(str(row["Variance"]))}</div>'
                    f'<div><span class="cost-status">{html.escape(str(row["Status"]))}</span></div>'
                    '</div>'
                )
            st.markdown(
                """
                <style>
                .cost-summary-table{height:235px;overflow-y:auto;overflow-x:hidden;
                    border:1px solid #e1eaf1;border-radius:9px;background:#fff}
                .cost-summary-row{display:grid;grid-template-columns:minmax(150px,2fr) 82px 118px 68px 82px;
                    align-items:center;border-bottom:1px solid #e5edf3;min-width:0}
                .cost-summary-row>div{min-width:0;padding:10px 8px;font-size:10px;line-height:1.3;
                    color:#233f58;white-space:normal;overflow-wrap:anywhere}
                .cost-summary-head{position:sticky;top:0;z-index:2;background:#f6f8fb;font-weight:700}
                .cost-summary-head>div{color:#667b8d;white-space:normal}
                .cost-component{font-weight:700;color:#174f8a!important}
                .cost-variance{font-weight:800;color:#177245!important}
                .cost-status{display:inline-block;max-width:100%;padding:3px 7px;border-radius:999px;
                    background:#e8f7ee;color:#177245;font-size:8px;font-weight:800;white-space:nowrap;
                    overflow:hidden;text-overflow:ellipsis}
                @media(max-width:1000px){
                    .cost-summary-row{grid-template-columns:minmax(125px,1.8fr) 70px 100px 58px 72px}
                    .cost-summary-row>div{padding:8px 5px;font-size:9px}
                    .cost-status{padding:3px 5px;font-size:7px}
                }
                </style>
                <div class="cost-summary-table">
                  <div class="cost-summary-row cost-summary-head">
                    <div>Project Component</div><div>Budget</div><div>Final Accomplishment</div>
                    <div>Variance</div><div>Status</div>
                  </div>
                """ + "".join(summary_rows) + "</div>",
                unsafe_allow_html=True,
            )

    with side:
        with st.container(border=True, key="whitecard_cost_health"):
            st.markdown('<div class="section-title">Cost Health</div>', unsafe_allow_html=True)
            final_actual = next((value for value in reversed(actual_cost) if value is not None), 0)
            final_target = next((value for value in reversed(target_cost) if value is not None), 0)
            utilized = round(final_actual / total_cost * 100) if total_cost else 0
            variance = final_actual - final_target
            for label, value, color in [("Budget Utilized", f"{utilized}%", "#16a6a1"), ("Cost Variance", peso_millions(variance), "#16a6a1" if variance <= 0 else "#ef5261"), ("Cost Completion", f"{utilized}%", "#16a6a1")]:
                st.markdown(f'<div class="compact-health"><span>{label}</span><strong style="color:{color}">{value}</strong></div>', unsafe_allow_html=True)
        with st.container(border=True, key="whitecard_cost_changes"):
            st.markdown('<div class="section-title">Change Orders</div>', unsafe_allow_html=True)
            st.info("No change-order records were included in the source workbook.")
        with st.container(border=True, key="whitecard_cost_risks"):
            st.markdown('<div class="section-title">Cost Risks</div>', unsafe_allow_html=True)
            st.info("No cost-risk records were included in the source workbook.")
    st.caption(f"Source: Project Monitoring Template | {project_year} | {report_date:%d %b %Y}")
