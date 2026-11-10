"""Project Monitoring data model populated from SOCOCA CSV/Excel uploads."""

from __future__ import annotations

import re

import pandas as pd
import streamlit as st


REQUIRED_TABLES = {
    "Basic Project Information", "Project Components",
    "Project Targets", "Project Accomplishment",
}


def _money(value) -> float:
    if value is None or pd.isna(value) or str(value).strip() == "":
        return 0.0
    text = str(value).replace("₱", "").replace(",", "").strip()
    if text.count(".") > 1:
        parts = text.split(".")
        text = "".join(parts[:-1]) + "." + parts[-1]
    try:
        return float(text)
    except ValueError:
        return 0.0


def _month_number(value) -> int | None:
    match = re.search(r"(\d+)", str(value or ""))
    if not match:
        return None
    month = int(match.group(1))
    return month if month >= 1 else None


def _physical_percent(value, month_number: int) -> float:
    text = str(value or "").strip().lower().replace(" ", "")
    ratio = re.search(r"(\d*\.?\d+)/(\d*\.?\d+)", text)
    if ratio:
        denominator = float(ratio.group(2))
        return round(float(ratio.group(1)) / denominator * 100, 2) if denominator else 0.0
    if month_number < 5:
        return 0.0
    percent = re.search(r"(\d+(?:\.\d+)?)%", text)
    return float(percent.group(1)) if percent else 0.0


def _monthly_values(frame: pd.DataFrame, total_months: int):
    costs = [None] * total_months
    physical = [None] * total_months
    physical_percent = [0.0] * total_months
    for _, row in frame.iterrows():
        month_number = _month_number(row.get("Month"))
        if not month_number:
            continue
        index = month_number - 1
        costs[index] = _money(row.get("Cost"))
        physical[index] = row.get("Physical")
        physical_percent[index] = _physical_percent(
            row.get("Physical Weight", row.get("Physical")), month_number
        )
    return costs, physical, physical_percent


def build_project_data(tables: dict[str, pd.DataFrame]):
    if not REQUIRED_TABLES.issubset(tables):
        return None
    basic = tables["Basic Project Information"]
    components_frame = tables["Project Components"]
    if basic.empty or components_frame.empty:
        return None
    basic_row = basic.iloc[0]
    components = []
    for _, row in components_frame.iterrows():
        component = str(row.get("Project Components", "")).strip()
        if not component:
            continue
        components.append({
            "component": component,
            "details": str(row.get("Details", "") or "").strip(),
            "target": str(row.get("Total Physical Target", "") or "").strip(),
            "budget": _money(row.get("Total Project Cost")),
        })
    def component_order(item):
        label = item["component"].lower()
        if "pre-implementation" in label or "pre implementation" in label:
            return 0
        if "implementation" in label:
            return 1
        if "monitoring" in label:
            return 2
        if "completion" in label or "turn-over" in label or "turnover" in label:
            return 3
        return 4
    components.sort(key=component_order)
    month_numbers = [
        month
        for table_name in ("Project Targets", "Project Accomplishment")
        for month in tables[table_name].get("Month", pd.Series(dtype=object)).map(_month_number).dropna().astype(int)
    ]
    total_months = max(month_numbers, default=12)
    months = [f"M{i}" for i in range(1, total_months + 1)]
    target_cost, target_physical, target_percent = _monthly_values(tables["Project Targets"], total_months)
    actual_cost, actual_physical, actual_percent = _monthly_values(tables["Project Accomplishment"], total_months)
    return {
        "project_name": str(basic_row.get("Project Name", "") or "").strip(),
        "implementing_unit": str(basic_row.get("Implementing Unit", "") or "").strip(),
        "target_area": str(basic_row.get("Project Target Area", "") or "").strip(),
        "beneficiaries": str(basic_row.get("Intended Beneficiaries", "") or "").strip(),
        "province": str(basic_row.get("Address", "") or "").strip(),
        "spot_name": str(basic_row.get("Spot name", "") or "").strip(),
        "total_project_cost": sum(item["budget"] for item in components),
        "months": months,
        "total_months": total_months,
        "duration_years": (total_months + 11) // 12,
        "target_cost_cumulative": target_cost,
        "actual_cost_cumulative": actual_cost,
        "target_physical": target_physical,
        "actual_physical": actual_physical,
        "target_physical_percent": target_percent,
        "actual_physical_percent": actual_percent,
        "components": components,
        "risk_register": tables.get("Project Risks", pd.DataFrame()).copy(),
    }


def get_project_data(project_year="All Years"):
    data = st.session_state.get("project_monitoring_data")
    if not data or project_year == "All Years":
        return data
    match = re.search(r"(\d+)", str(project_year))
    if not match:
        return data
    year = int(match.group(1))
    start = (year - 1) * 12
    end = min(start + 12, data.get("total_months", len(data["months"])))
    if start >= end:
        return None
    filtered = data.copy()
    series_keys = [
        "months", "target_cost_cumulative", "actual_cost_cumulative",
        "target_physical", "actual_physical", "target_physical_percent",
        "actual_physical_percent",
    ]
    for key in series_keys:
        filtered[key] = data[key][start:end]
    filtered["selected_year"] = year
    filtered["period_start_index"] = start
    filtered["target_cost_previous"] = data["target_cost_cumulative"][start - 1] if start else 0.0
    filtered["actual_cost_previous"] = data["actual_cost_cumulative"][start - 1] if start else 0.0
    return filtered


def percentages(values, total_project_cost):
    if not total_project_cost:
        return [None for _ in values]
    return [round(value / total_project_cost * 100, 2) if value is not None else None for value in values]


def monthly_amounts(cumulative, previous=0.0):
    result = []
    for value in cumulative:
        if value is None:
            result.append(None)
            continue
        result.append(value - previous)
        previous = value
    return result


def risk_delay_by_month(risk_frame):
    """Return delay days keyed by project month from an uploaded risk register."""
    if risk_frame is None or risk_frame.empty:
        return {}
    normalized = {
        re.sub(r"[^a-z0-9]+", "_", str(column).strip().lower()).strip("_"): column
        for column in risk_frame.columns
    }
    month_column = normalized.get("affected_month")
    delay_column = normalized.get("delay_days")
    if not month_column or not delay_column:
        return {}
    delays = {}
    for _, row in risk_frame.iterrows():
        month = _month_number(row.get(month_column))
        delay = pd.to_numeric(row.get(delay_column), errors="coerce")
        if month and pd.notna(delay) and delay > 0:
            delays[month] = delays.get(month, 0.0) + float(delay)
    return delays
