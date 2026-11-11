from __future__ import annotations

from datetime import datetime
import io
import re

import pandas as pd
import streamlit as st

from .common import page_header, stat_card
from .project_data import get_project_data, monthly_amounts


def _last_number(values):
    for value in reversed(list(values or [])):
        number = pd.to_numeric(value, errors="coerce")
        if pd.notna(number):
            return float(number)
    return 0.0


def _safe_name(value):
    name = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value or "Project")).strip("_")
    return name or "Project"


def _summary_table(data, project, project_year, report_date):
    planned = _last_number(data.get("target_physical_percent", []))
    actual = _last_number(data.get("actual_physical_percent", []))
    target_cost = _last_number(data.get("target_cost_cumulative", []))
    actual_cost = _last_number(data.get("actual_cost_cumulative", []))
    return pd.DataFrame([
        ("Project Name", data.get("project_name") or project),
        ("Province", data.get("province", "")),
        ("Implementing Unit", data.get("implementing_unit", "")),
        ("Target Area", data.get("target_area", "")),
        ("Intended Beneficiaries", data.get("beneficiaries", "")),
        ("Project Period", project_year),
        ("Reporting Date", report_date.strftime("%d %b %Y")),
        ("Total Project Cost", data.get("total_project_cost", 0)),
        ("Planned Physical Progress (%)", planned),
        ("Actual Physical Progress (%)", actual),
        ("Physical Variance (percentage points)", actual - planned),
        ("Target Cost to Date", target_cost),
        ("Actual Cost to Date", actual_cost),
        ("Cost Variance", actual_cost - target_cost),
    ], columns=["Project Summary", "Value"])


def _monthly_table(data):
    target_cost = data.get("target_cost_cumulative", [])
    actual_cost = data.get("actual_cost_cumulative", [])
    return pd.DataFrame({
        "Month": data.get("months", []),
        "Planned Physical (%)": data.get("target_physical_percent", []),
        "Actual Physical (%)": data.get("actual_physical_percent", []),
        "Physical Variance": [
            (actual or 0) - (planned or 0)
            for planned, actual in zip(
                data.get("target_physical_percent", []),
                data.get("actual_physical_percent", []),
            )
        ],
        "Target Monthly Cost": monthly_amounts(target_cost, data.get("target_cost_previous", 0)),
        "Actual Monthly Cost": monthly_amounts(actual_cost, data.get("actual_cost_previous", 0)),
        "Target Cumulative Cost": target_cost,
        "Actual Cumulative Cost": actual_cost,
    })


def _build_report(data, project, project_year, report_date, sections):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        if "Overview" in sections:
            _summary_table(data, project, project_year, report_date).to_excel(
                writer, sheet_name="Project Overview", index=False
            )
        if "Cost" in sections:
            _monthly_table(data)[[
                "Month", "Target Monthly Cost", "Actual Monthly Cost",
                "Target Cumulative Cost", "Actual Cumulative Cost",
            ]].to_excel(writer, sheet_name="Cost Monitoring", index=False)
        if "Risk" in sections:
            risks = data.get("risk_register", pd.DataFrame())
            (risks if risks is not None else pd.DataFrame()).to_excel(
                writer, sheet_name="Risk Register", index=False
            )
        for worksheet in writer.book.worksheets:
            worksheet.freeze_panes = "A2"
            worksheet.auto_filter.ref = worksheet.dimensions
            for cell in worksheet[1]:
                cell.font = cell.font.copy(bold=True, color="FFFFFF")
                cell.fill = cell.fill.copy(fill_type="solid", fgColor="174F8A")
            for column_cells in worksheet.columns:
                values = [str(cell.value or "") for cell in column_cells[:100]]
                width = min(max(max(map(len, values), default=10) + 2, 12), 45)
                worksheet.column_dimensions[column_cells[0].column_letter].width = width
    output.seek(0)
    return output.getvalue()


def render(project, report_date, project_year="All Years"):
    data = get_project_data(project_year)
    page_header(
        "PROJECT REPORTS",
        "Generate reports from the selected project's actual Overview, Cost, and Risk data.",
    )
    if not data:
        st.info("Upload and select a Project Monitoring dataset before generating a report.")
        return

    generated = st.session_state.setdefault("project_generated_reports", [])
    risks = data.get("risk_register", pd.DataFrame())
    risk_count = len(risks) if risks is not None else 0
    metrics = [
        ("Reports Generated", f"{len(generated):,}", "description"),
        ("Project Months", f"{data.get('total_months', len(data.get('months', []))):,}", "calendar_month"),
        ("Total Project Cost", f"₱{data.get('total_project_cost', 0):,.2f}", "payments"),
        ("Risk Records", f"{risk_count:,}", "warning"),
        ("Reporting Date", report_date.strftime("%d %b %Y"), "update"),
    ]
    for column, (label, value, icon), index in zip(st.columns(5, gap="small"), metrics, range(5)):
        with column.container(border=True, key=f"whitecard_reports_kpi_{index}"):
            stat_card(label, value, icon)

    options_col, preview_col = st.columns([1, 1.8], gap="small")
    with options_col.container(border=True, key="whitecard_reports_generate"):
        st.markdown('<div class="section-title">Generate Report</div>', unsafe_allow_html=True)
        report_name = st.text_input("Report Name", value=f"{project or 'Project'} Monitoring Report")
        sections = []
        if st.checkbox("Project Overview", value=True):
            sections.append("Overview")
        if st.checkbox("Cost Monitoring", value=True):
            sections.append("Cost")
        if st.checkbox("Risk Register", value=risk_count > 0):
            sections.append("Risk")
        if st.button("Generate Excel Report", type="primary", use_container_width=True, disabled=not sections):
            report_bytes = _build_report(data, project, project_year, report_date, sections)
            file_name = f"{_safe_name(report_name)}_{report_date:%Y%m%d}.xlsx"
            st.session_state.project_ready_report = {
                "name": file_name, "bytes": report_bytes, "sections": sections,
            }
            generated.insert(0, {
                "Report": report_name,
                "Period": project_year,
                "Generated": datetime.now().strftime("%d %b %Y %H:%M"),
                "File": file_name,
            })

        ready = st.session_state.get("project_ready_report")
        if ready:
            st.success("The report is ready to download.")
            st.download_button(
                "Download Generated Report", data=ready["bytes"],
                file_name=ready["name"],
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

    with preview_col.container(border=True, key="whitecard_reports_preview"):
        st.markdown('<div class="section-title">Actual Project Overview</div>', unsafe_allow_html=True)
        st.dataframe(
            _summary_table(data, project, project_year, report_date),
            hide_index=True, use_container_width=True, height=330,
        )

    cost_col, risk_col = st.columns([1.2, 1], gap="small")
    with cost_col.container(border=True, key="whitecard_reports_cost"):
        st.markdown('<div class="section-title">Actual Cost Monitoring</div>', unsafe_allow_html=True)
        st.dataframe(
            _monthly_table(data)[[
                "Month", "Target Cumulative Cost", "Actual Cumulative Cost"
            ]], hide_index=True, use_container_width=True, height=260,
        )
    with risk_col.container(border=True, key="whitecard_reports_risk"):
        st.markdown('<div class="section-title">Actual Risk Register</div>', unsafe_allow_html=True)
        if risk_count:
            st.dataframe(risks, hide_index=True, use_container_width=True, height=260)
        else:
            st.info("No risk register has been uploaded for this project.")

    with st.container(border=True, key="whitecard_reports_history"):
        st.markdown('<div class="section-title">Generated Report History</div>', unsafe_allow_html=True)
        if generated:
            st.dataframe(pd.DataFrame(generated[:25]), hide_index=True, use_container_width=True, height=180)
        else:
            st.info("No report has been generated during this session.")

    st.caption(f"Reports workspace for {project} | {project_year} | {report_date:%d %b %Y}")
