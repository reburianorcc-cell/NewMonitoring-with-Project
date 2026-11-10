"""Parser for the standard single-sheet SOCOCA Project Monitoring Template."""

from __future__ import annotations

import io
import re

import pandas as pd


def _normal(value) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").strip().lower()).strip()


def _nonempty(value) -> bool:
    return not pd.isna(value) and str(value).strip() != ""


def _numeric_total(values) -> float:
    total = 0.0
    for value in values:
        if isinstance(value, (int, float)) and not pd.isna(value):
            total += float(value)
    return total


def _money(value) -> float | None:
    if pd.isna(value) or str(value).strip() == "":
        return None
    text = str(value).strip().replace(",", "").replace("₱", "")
    # Some SOCOCA exports contain a second decimal separator (for example
    # 19,300.000.00). Preserve the intended numeric value by keeping the final
    # decimal point only.
    if text.count(".") > 1:
        parts = text.split(".")
        text = "".join(parts[:-1]) + "." + parts[-1]
    try:
        return float(text)
    except ValueError:
        return None


def _month_number(value) -> int | None:
    match = re.search(r"(\d+)", str(value or ""))
    if not match:
        return None
    number = int(match.group(1))
    return number if number >= 1 else None


def _first_present(frame: pd.DataFrame, column: str):
    if column not in frame:
        return None
    values = frame[column].dropna()
    values = values[values.astype(str).str.strip().ne("")]
    return values.iloc[0] if not values.empty else None


def _sococa_month_table(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    detected_months = frame["Month"].map(_month_number).dropna().astype(int)
    for month_number in range(1, detected_months.max() + 1 if not detected_months.empty else 1):
        month_rows = frame[
            frame["Month"].map(_month_number).eq(month_number)
        ].copy()
        if month_rows.empty:
            rows.append({
                "Month": f"M{month_number}", "Physical": None,
                "Cost": None, "Physical Weight": None,
            })
            continue

        phase_column = "Initiation & Planning Phase"
        implementation = month_rows[
            month_rows.get(phase_column, pd.Series(index=month_rows.index, dtype=object))
            .astype(str).str.contains("Implementation Phase", case=False, na=False)
        ]
        milestone_row = implementation.iloc[0] if not implementation.empty else month_rows.iloc[0]
        physical = _first_present(implementation if not implementation.empty else month_rows, "Physical")
        rows.append({
            "Month": f"M{month_number}",
            "Physical": physical,
            "Cost": _money(milestone_row.get("Milestone Cost")),
            "Physical Weight": milestone_row.get("Physical Weight"),
        })
    return pd.DataFrame(rows)


def parse_sococa_csv_export(file_name: str, content: bytes):
    """Normalize one of the four SOCOCA Project Monitoring CSV exports."""
    frame = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig").dropna(how="all")
    columns = set(frame.columns)

    basic_columns = {
        "Project Name", "Implementing Unit", "Project Target Area",
        "Intended Beneficiaries",
    }
    if basic_columns.issubset(columns):
        selected = frame[[
            *basic_columns,
            *(["Address"] if "Address" in frame else []),
            *(["Spot name"] if "Spot name" in frame else []),
        ]].copy()
        # Sets are unordered; return the required columns in dashboard order.
        ordered = [
            "Project Name", "Implementing Unit", "Project Target Area",
            "Intended Beneficiaries",
        ]
        if "Address" in selected:
            ordered.append("Address")
        if "Spot name" in selected:
            ordered.append("Spot name")
        return "Basic Project Information", selected[ordered]

    if {"Project Components", "Total Physical Target", "Cost"}.issubset(columns):
        selected = frame[[
            "Project Components",
            *(["Details"] if "Details" in frame else []),
            "Total Physical Target", "Cost",
        ]].copy()
        selected["Total Project Cost"] = selected["Cost"].map(_money)
        selected = selected.drop(columns=["Cost"])
        return "Project Components", selected

    if {"Month", "Physical Weight", "Milestone Cost"}.issubset(columns):
        normalized_name = _normal(file_name)
        marker_values = " ".join(
            str(value) for value in frame.filter(regex=r"^Item name\(").stack().tolist()
        ).lower()
        if "accomplishment" in normalized_name or "accomplishment" in marker_values:
            return "Project Accomplishment", _sococa_month_table(frame)
        if "target" in normalized_name or "target" in marker_values:
            return "Project Targets", _sococa_month_table(frame)
    return None


def _month_table(raw: pd.DataFrame, start_column: int, end_column: int) -> pd.DataFrame:
    rows = []
    cumulative_cost = 0.0
    column = start_column
    while column <= end_column and column < raw.shape[1]:
        month = raw.iat[2, column] if raw.shape[0] > 2 else None
        if not _normal(month).startswith("m"):
            column += 1
            continue

        physical = raw.iat[4, column] if raw.shape[0] > 4 else None
        cost_column = column + 1
        monthly_cost = 0.0
        if cost_column < raw.shape[1]:
            monthly_cost = _numeric_total(raw.iloc[5:, cost_column].tolist())
            if not monthly_cost and raw.shape[0] > 4:
                summary_cost = raw.iat[4, cost_column]
                if isinstance(summary_cost, (int, float)) and not pd.isna(summary_cost):
                    monthly_cost = float(summary_cost)
        cumulative_cost += monthly_cost
        rows.append({"Month": str(month).strip(), "Physical": physical, "Cost": cumulative_cost})
        column += 2
    return pd.DataFrame(rows, columns=["Month", "Physical", "Cost"])


def parse_project_monitoring_template(content: bytes) -> dict[str, pd.DataFrame] | None:
    """Return four normalized tables when *content* matches the wide template."""
    raw = pd.read_excel(io.BytesIO(content), sheet_name=0, header=None)
    if raw.empty or "project monitoring template" not in _normal(raw.iat[0, 0]):
        return None

    section_row = [_normal(value) for value in raw.iloc[1].tolist()]
    try:
        targets_start = next(i for i, value in enumerate(section_row) if value == "project targets")
        accomplishments_start = next(
            i for i, value in enumerate(section_row)
            if value in {"project accomplishment", "project accomplishments"}
        )
    except StopIteration:
        return None

    basic_headers = [raw.iat[2, column] for column in range(4)]
    basic_values = [raw.iat[5, column] for column in range(4)]
    basic = pd.DataFrame([basic_values], columns=basic_headers).dropna(how="all")

    component_headers = [raw.iat[2, column] for column in range(4, 7)]
    component_rows = []
    for row in range(5, raw.shape[0]):
        values = [raw.iat[row, column] for column in range(4, 7)]
        if not any(_nonempty(value) for value in values):
            if component_rows:
                break
            continue
        component_rows.append(values)
    components = pd.DataFrame(component_rows, columns=component_headers).dropna(how="all")

    targets = _month_table(raw, targets_start, accomplishments_start - 1)
    accomplishments = _month_table(raw, accomplishments_start, raw.shape[1] - 1)

    if basic.empty or components.empty or targets.empty or accomplishments.empty:
        return None
    return {
        "Basic Project Information": basic,
        "Project Components": components,
        "Project Targets": targets,
        "Project Accomplishment": accomplishments,
    }
