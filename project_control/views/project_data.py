"""Project Monitoring data model populated from SOCOCA CSV/Excel uploads."""

from __future__ import annotations

import re

import pandas as pd
import streamlit as st


MONTHS = [f"M{i}" for i in range(1, 13)]
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
    match = re.search(r"(\d{1,2})", str(value or ""))
    if not match:
        return None
    month = int(match.group(1))
    return month if 1 <= month <= 12 else None


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


def _monthly_values(frame: pd.DataFrame):
    costs = [None] * 12
    physical = [None] * 12
    physical_percent = [0.0] * 12
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
    target_cost, target_physical, target_percent = _monthly_values(tables["Project Targets"])
    actual_cost, actual_physical, actual_percent = _monthly_values(tables["Project Accomplishment"])
    return {
        "project_name": str(basic_row.get("Project Name", "") or "").strip(),
        "implementing_unit": str(basic_row.get("Implementing Unit", "") or "").strip(),
        "target_area": str(basic_row.get("Project Target Area", "") or "").strip(),
        "beneficiaries": str(basic_row.get("Intended Beneficiaries", "") or "").strip(),
        "province": str(basic_row.get("Address", "") or "").strip(),
        "spot_name": str(basic_row.get("Spot name", "") or "").strip(),
        "total_project_cost": sum(item["budget"] for item in components),
        "months": MONTHS,
        "target_cost_cumulative": target_cost,
        "actual_cost_cumulative": actual_cost,
        "target_physical": target_physical,
        "actual_physical": actual_physical,
        "target_physical_percent": target_percent,
        "actual_physical_percent": actual_percent,
        "components": components,
    }


def get_project_data():
    return st.session_state.get("project_monitoring_data")


def percentages(values, total_project_cost):
    if not total_project_cost:
        return [None for _ in values]
    return [round(value / total_project_cost * 100, 2) if value is not None else None for value in values]


def monthly_amounts(cumulative):
    previous = 0.0
    result = []
    for value in cumulative:
        if value is None:
            result.append(None)
            continue
        result.append(value - previous)
        previous = value
    return result
