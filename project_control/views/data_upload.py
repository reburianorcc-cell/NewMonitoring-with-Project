from datetime import datetime
import io
import re

import pandas as pd
import streamlit as st

from .common import page_header
from .project_data import build_project_data
from .project_template_parser import (
    parse_project_monitoring_template,
    parse_sococa_csv_export,
)
from .supabase_store import (
    delete_project,
    delete_uploads,
    fetch_history,
    fetch_latest_datasets,
    is_configured,
    save_upload_bundle,
)


PROJECT_FILE_TYPES = {
    "Basic Project Information": ["project_name", "implementing_unit", "project_target_area", "intended_beneficiaries"],
    "Project Components": ["project_components", "total_physical_target", "total_project_cost"],
    "Project Targets": ["month", "physical", "cost"],
    "Project Accomplishment": ["month", "physical", "cost"],
    "Project Risks": ["risk_id", "risk_description", "category", "observation", "potential_impact", "affected_month", "delay_days", "owner", "mitigation_action", "status"],
}

def _normalize(value):
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _suggest_type(name, dataframe):
    key = _normalize(name)
    if "risk" in key:
        return "Project Risks"
    if "accompl" in key or "actual" in key:
        return "Project Accomplishment"
    if "target" in key or "plan" in key:
        return "Project Targets"
    if "component" in key:
        return "Project Components"
    if "basic" in key or "information" in key or "overview" in key:
        return "Basic Project Information"
    columns = {_normalize(column) for column in dataframe.columns}
    if {"risk_id", "risk_description", "delay_days"}.issubset(columns):
        return "Project Risks"
    if {"project_components", "total_physical_target", "total_project_cost"}.issubset(columns):
        return "Project Components"
    if {"project_name", "implementing_unit"}.issubset(columns):
        return "Basic Project Information"
    return "Project Targets"


def _read_uploaded_files(uploaded_files):
    items = []
    for uploaded_file in uploaded_files:
        content = uploaded_file.getvalue()
        if uploaded_file.name.lower().endswith(".csv"):
            sococa_export = parse_sococa_csv_export(uploaded_file.name, content)
            if sococa_export:
                content_type, dataframe = sococa_export
                items.append({
                    "source_file": uploaded_file.name,
                    "source_label": uploaded_file.name,
                    "dataframe": dataframe,
                    "suggested_type": content_type,
                })
                continue
            dataframe = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig").dropna(how="all")
            items.append({
                "source_file": uploaded_file.name,
                "source_label": uploaded_file.name,
                "dataframe": dataframe,
                "suggested_type": _suggest_type(uploaded_file.name, dataframe),
            })
            continue

        workbook = pd.ExcelFile(io.BytesIO(content))
        parsed_template = parse_project_monitoring_template(content)
        if parsed_template:
            for content_type, dataframe in parsed_template.items():
                items.append({
                    "source_file": uploaded_file.name,
                    "source_label": f"{uploaded_file.name} · {content_type}",
                    "dataframe": dataframe,
                    "suggested_type": content_type,
                })
            continue

        matched_sheet = False
        for sheet_name in workbook.sheet_names:
            dataframe = pd.read_excel(io.BytesIO(content), sheet_name=sheet_name).dropna(how="all")
            normalized_sheet = _normalize(sheet_name)
            exact_type = next((name for name in PROJECT_FILE_TYPES if _normalize(name) == normalized_sheet), None)
            if exact_type:
                matched_sheet = True
                items.append({
                    "source_file": uploaded_file.name,
                    "source_label": f"{uploaded_file.name} · {sheet_name}",
                    "dataframe": dataframe,
                    "suggested_type": exact_type,
                })
        if not matched_sheet:
            dataframe = pd.read_excel(io.BytesIO(content), sheet_name=workbook.sheet_names[0]).dropna(how="all")
            items.append({
                "source_file": uploaded_file.name,
                "source_label": f"{uploaded_file.name} · {workbook.sheet_names[0]}",
                "dataframe": dataframe,
                "suggested_type": _suggest_type(uploaded_file.name, dataframe),
            })
    return items


def _render_history(province=None):
    if is_configured():
        try:
            history = fetch_history(province)
        except Exception as exc:
            st.error(f"Supabase upload history could not be loaded: {exc}")
            history = st.session_state.setdefault("upload_history", [])
    else:
        history = st.session_state.setdefault("upload_history", [])
    with st.container(border=True, key="whitecard_upload_history"):
        st.markdown('<div class="section-title">Upload History</div>', unsafe_allow_html=True)
        if not history:
            st.info("No monitoring files have been uploaded yet.")
            return
        frame = pd.DataFrame(history)
        empty_identity = [column for column in ["Province", "Project Name", "Project Year"] if column in frame and frame[column].fillna("").eq("").all()]
        frame = frame.drop(columns=empty_identity)
        display_frame = frame.copy()
        display_frame.insert(0, "Select", False)
        edited = st.data_editor(
            display_frame,
            use_container_width=True,
            hide_index=True,
            height=250,
            disabled=[column for column in display_frame.columns if column != "Select"],
            column_config={
                "Select": st.column_config.CheckboxColumn("Select"),
                "Upload ID": None,
                "Project ID": None,
            },
            key="project_upload_history_editor",
        )
        st.download_button(
            "Download Upload History",
            frame.drop(columns=["Upload ID", "Project ID"], errors="ignore").to_csv(index=False).encode("utf-8"),
            file_name="sococa_monitoring_upload_history.csv",
            mime="text/csv", use_container_width=True,
        )
        if is_configured() and st.session_state.get("admin_role") in {"admin", "super_admin"}:
            selected = edited.loc[edited["Select"]]
            confirm_remove = st.checkbox(
                "I confirm removal of the selected upload version(s)",
                key="confirm_remove_project_uploads",
            )
            if st.button(
                "Remove Selected Upload",
                use_container_width=True,
                disabled=selected.empty or not confirm_remove,
            ):
                restore_province = str(selected.iloc[0].get("Province", ""))
                restore_project = str(selected.iloc[0].get("Project Name", ""))
                removed = delete_uploads(selected["Upload ID"].tolist())
                tables = fetch_latest_datasets(restore_province, restore_project)
                restored = build_project_data(tables)
                st.session_state.project_monitoring_tables = tables
                if restored:
                    restored["province"] = restore_province
                    restored["project_name"] = restore_project
                    st.session_state.project_monitoring_data = restored
                    message = " The previous saved version is now displayed."
                else:
                    st.session_state.pop("project_monitoring_data", None)
                    message = " No complete previous version remains for this project."
                st.session_state.project_upload_notice = f"{removed} upload record(s) removed.{message}"
                st.rerun()

            projects = (
                frame[["Province", "Project Name"]]
                .drop_duplicates()
                .assign(Label=lambda data: data["Province"] + " — " + data["Project Name"])
            )
            st.markdown('<div class="section-title">Delete Entire Project</div>', unsafe_allow_html=True)
            project_label = st.selectbox(
                "Uploaded Project",
                projects["Label"].tolist(),
                key="delete_uploaded_project_selection",
            )
            confirm_project = st.checkbox(
                "I understand this removes all uploaded versions for the selected project",
                key="confirm_delete_uploaded_project",
            )
            if st.button(
                "Delete Entire Project",
                use_container_width=True,
                disabled=not confirm_project,
            ):
                selected_project = projects.loc[projects["Label"] == project_label].iloc[0]
                deleted = delete_project(
                    selected_project["Province"], selected_project["Project Name"]
                )
                if deleted:
                    st.session_state.pop("project_monitoring_data", None)
                    st.session_state.pop("project_monitoring_tables", None)
                    st.session_state.pop("project_registry", None)
                    st.session_state.project_monitoring_loaded = False
                    st.session_state.project_upload_notice = f"{project_label} was deleted."
                    st.rerun()
                st.error("The selected project could not be found.")


def render(project, report_date, project_year="All Years"):
    page_header("PROJECT DATA UPLOAD", "Upload one workbook or multiple CSV/Excel files without assigning a hierarchy.")

    role = st.session_state.get("admin_role", "operator")
    allowed_provinces = st.session_state.get("allowed_project_provinces", [])
    registry = st.session_state.get("project_registry", [])
    province_options = allowed_provinces or sorted({
        item["province"] for item in registry if item.get("province")
    })
    if role in {"admin", "super_admin"} and "Create New Province" not in province_options:
        province_options = [*province_options, "Create New Province"]
    default_province = str(st.session_state.get("active_province") or "").strip()
    if not province_options and default_province:
        province_options = [default_province]
    if not province_options:
        province_options = ["Create New Province"]
    identity = st.container(border=True, key="whitecard_upload_identity")
    with identity:
        st.markdown('<div class="section-title">Project Location and Name</div>', unsafe_allow_html=True)
        province_col, project_col = st.columns(2, gap="small")
        with province_col:
            default_index = province_options.index(default_province) if default_province in province_options else 0
            upload_province = st.selectbox(
                "Province", province_options, index=default_index,
                key="upload_province_select",
            )
            if upload_province == "Create New Province":
                upload_province = st.text_input(
                    "New Province Name", placeholder="Example: Bohol",
                    key="upload_new_province_input",
                ).strip()
        with project_col:
            province_projects = [
                item["project_name"] for item in registry
                if item.get("province", "").casefold() == upload_province.casefold()
            ]
            project_choice = st.selectbox(
                "Project Selection",
                ["Create New Project", *province_projects],
                key="upload_project_selection",
            )
            if project_choice == "Create New Project":
                upload_project = st.text_input(
                    "New Project Name", placeholder="Enter project name",
                    key="upload_project_input",
                ).strip()
            else:
                upload_project = project_choice
        if role == "operator":
            st.caption(f"Your account can upload files only for: {', '.join(allowed_provinces)}")

    setup, guide = st.columns([2.1, 1], gap="small")
    with setup.container(border=True, key="whitecard_upload_setup"):
        st.markdown('<div class="section-title">Upload Project Files</div>', unsafe_allow_html=True)
        selected_files = st.file_uploader(
            "Choose one or multiple Project Monitoring files",
            type=["csv", "xlsx", "xls"],
            accept_multiple_files=True,
            help=(
                "You may upload one file or select multiple files at the same time. "
                "Supported formats: CSV, XLSX, and XLS."
            ),
        )
        uploaded_files = list(selected_files or [])
        st.caption("Accepted formats: CSV, Excel (.xlsx), and Excel 97–2003 (.xls).")
        replace_existing = st.toggle("Replace matching saved files", value=False)
    with guide.container(border=True, key="whitecard_upload_guide"):
        st.markdown('<div class="section-title">Project Files</div>', unsafe_allow_html=True)
        st.markdown(
            "1. **Basic Project Information**  \n"
            "2. **Project Components**  \n"
            "3. **Project Targets** — dynamic project months  \n"
            "4. **Project Accomplishment** — dynamic project months  \n"
            "5. **Project Risks** — optional risk and delay register"
        )
        st.caption("A single Excel workbook may contain the tables as separate sheets. Project duration is detected automatically from the highest month number.")
        if is_configured():
            st.success("Supabase persistent storage is connected.")
        else:
            st.warning("Supabase is not configured. Uploads will remain in this Streamlit session only.")

    if not uploaded_files:
        with st.container(border=True, key="whitecard_upload_empty"):
            st.markdown('<div class="section-title">Upload Status</div>', unsafe_allow_html=True)
            st.info("Upload one Excel workbook or one or multiple CSV/Excel files.")
        _render_history(default_province if role == "operator" else None)
        return

    try:
        items = _read_uploaded_files(uploaded_files)
    except Exception as exc:
        st.error(f"The uploaded file could not be read: {exc}")
        _render_history(default_province if role == "operator" else None)
        return

    mapped_items = []
    all_valid = True
    total_records = 0
    with st.container(border=True, key="whitecard_upload_mapping"):
        st.markdown('<div class="section-title">File Mapping and Preview</div>', unsafe_allow_html=True)
        st.caption("Check the detected content type for each file or workbook sheet before saving.")
        select_all_contents = st.checkbox(
            "Select All File Contents",
            value=True,
            help=(
                "Use the automatically detected content type for every uploaded file. "
                "Turn this off only when you need to change an individual file mapping."
            ),
        )
        if select_all_contents:
            detected_labels = [item["suggested_type"] for item in items]
            st.success(
                "All detected file contents selected: "
                + ", ".join(dict.fromkeys(detected_labels))
            )
        for index, item in enumerate(items):
            with st.expander(item["source_label"], expanded=index == 0):
                default_index = list(PROJECT_FILE_TYPES).index(item["suggested_type"])
                content_type = st.selectbox(
                    "File Content", list(PROJECT_FILE_TYPES), index=default_index,
                    key=f"upload_file_type_{index}_{_normalize(item['source_label'])}",
                    disabled=select_all_contents,
                )
                if select_all_contents:
                    content_type = item["suggested_type"]
                dataframe = item["dataframe"]
                normalized_columns = {_normalize(column) for column in dataframe.columns}
                if content_type == "Project Risks":
                    # Accept both the revised SOCOCA labels and previously
                    # uploaded risk-register headings.
                    if "probability" in normalized_columns:
                        normalized_columns.add("observation")
                    if "impact" in normalized_columns:
                        normalized_columns.add("potential_impact")
                    if any(column.startswith("affected_month") for column in normalized_columns):
                        normalized_columns.add("affected_month")
                missing = [field for field in PROJECT_FILE_TYPES[content_type] if field not in normalized_columns]
                if missing:
                    all_valid = False
                    st.warning("Missing columns: " + ", ".join(missing))
                else:
                    st.success("Required columns are present.")
                st.dataframe(dataframe.head(50), use_container_width=True, hide_index=True, height=220)
                total_records += len(dataframe)
                mapped_items.append(item | {"content_type": content_type, "missing": missing})

    m1, m2, m3, m4 = st.columns(4, gap="small")
    m1.metric("Uploaded Files", len(uploaded_files))
    m2.metric("Detected Tables", len(mapped_items))
    m3.metric("Total Records", f"{total_records:,}")
    m4.metric("Status", "Ready" if all_valid else "Needs Review")

    duplicate_types = pd.Series([item["content_type"] for item in mapped_items]).duplicated().any()
    if duplicate_types:
        st.warning("Two or more uploaded tables are mapped to the same content type. Confirm that this is intentional.")

    if st.button(
        "Save Uploaded Project Files", type="primary", use_container_width=True,
        disabled=not all_valid or not upload_province or not upload_project,
    ):
        collisions = []
        for item in mapped_items:
            storage_key = f"dataset_{_normalize(item['source_label'])}_{_normalize(item['content_type'])}"
            if storage_key in st.session_state and not replace_existing:
                collisions.append(item["content_type"])
        if collisions:
            st.warning("Saved data already exists for: " + ", ".join(sorted(set(collisions))) + ". Enable replacement to overwrite it.")
        else:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                if is_configured():
                    save_upload_bundle(
                        upload_province, upload_project, project_year,
                        mapped_items, uploaded_files, replace_existing,
                    )
                for item in mapped_items:
                    storage_key = f"dataset_{_normalize(item['source_label'])}_{_normalize(item['content_type'])}"
                    existed = storage_key in st.session_state
                    st.session_state[storage_key] = item["dataframe"]
                    if not is_configured():
                        st.session_state.setdefault("upload_history", []).insert(0, {
                            "Uploaded At": timestamp,
                            "Content Type": item["content_type"],
                            "File / Sheet": item["source_label"],
                            "Records": len(item["dataframe"]),
                            "Action": "Replaced" if existed else "Uploaded",
                        })
                # Start from the persisted project tables, then apply the files
                # from this upload last. This guarantees that a just-uploaded
                # risk register cannot be overwritten by a stale cached query.
                tables = {}
                if is_configured():
                    try:
                        tables.update(fetch_latest_datasets(upload_province, upload_project))
                    except Exception:
                        pass
                else:
                    tables.update(st.session_state.get("project_monitoring_tables", {}))
                for item in mapped_items:
                    tables[item["content_type"]] = item["dataframe"]
                st.session_state.project_monitoring_tables = tables
                project_data = build_project_data(tables)
                if project_data:
                    project_data["province"] = upload_province
                    project_data["project_name"] = upload_project
                    st.session_state.project_monitoring_data = project_data
                    st.session_state.pending_project_identity = {
                        "province": upload_province,
                        "project": upload_project,
                    }
                    st.session_state.pop("dashboard_province_select", None)
                    st.session_state.pop("dashboard_project_select", None)
                    st.session_state.pop("project_registry", None)
                    # Force app.py to reload this project's newest Supabase
                    # datasets on the next rerun, even when its identity did
                    # not change.
                    st.session_state.pop("loaded_project_identity", None)
                storage_name = "Supabase" if is_configured() else "the current session"
                if project_data:
                    st.session_state.project_upload_notice = (
                        f"{len(mapped_items)} monitoring table(s) saved to {storage_name}. "
                        "The dashboard now uses the uploaded SOCOCA data."
                    )
                    uploaded_types = {item["content_type"] for item in mapped_items}
                    st.session_state.project_control_page = (
                        "Risk" if "Project Risks" in uploaded_types else "Overview"
                    )
                    st.rerun()
                st.success(f"{len(mapped_items)} monitoring table(s) saved to {storage_name}.")
            except Exception as exc:
                st.error(f"The upload could not be saved to Supabase: {exc}")

    _render_history(default_province if role == "operator" else None)
    st.caption(f"SOCOCA monitoring upload workspace | Reporting date: {report_date:%d %b %Y}")
