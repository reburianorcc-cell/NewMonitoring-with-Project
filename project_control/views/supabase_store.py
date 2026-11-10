"""Persistent SOCOCA monitoring storage backed by Supabase."""

from __future__ import annotations

from datetime import datetime, timezone
import re

import pandas as pd
import streamlit as st

try:
    from supabase import create_client
except ImportError:  # Keeps the prototype usable before dependencies are installed.
    create_client = None


BUCKET = "project-monitoring-files"


def _credentials():
    try:
        section = st.secrets.get("supabase", {})
        url = section.get("url") or st.secrets.get("SUPABASE_URL")
        key = (
            section.get("service_role_key")
            or section.get("secret_key")
            or st.secrets.get("SUPABASE_SERVICE_ROLE_KEY")
        )
        return url, key
    except Exception:
        return None, None


def is_configured():
    url, key = _credentials()
    return bool(create_client and url and key)


def client():
    url, key = _credentials()
    if not create_client:
        raise RuntimeError("The supabase package is not installed.")
    if not url or not key:
        raise RuntimeError("Supabase credentials are missing from Streamlit Secrets.")
    return create_client(url, key)


def _slug(value):
    return re.sub(r"[^a-z0-9]+", "-", str(value).strip().lower()).strip("-") or "item"


def _json_rows(dataframe):
    clean = dataframe.copy().astype(object)
    clean = clean.where(pd.notna(clean), None)
    for column in clean.columns:
        clean[column] = clean[column].map(
            lambda value: (
                value.isoformat() if hasattr(value, "isoformat")
                else value.item() if hasattr(value, "item")
                else value
            )
        )
    return clean.to_dict(orient="records")


def _upsert_identity(db, province, project_name):
    province_result = db.table("provinces").upsert(
        {"name": province}, on_conflict="name"
    ).execute()
    province_id = province_result.data[0]["id"]
    project_result = db.table("projects").upsert(
        {"province_id": province_id, "name": project_name},
        on_conflict="province_id,name",
    ).execute()
    return project_result.data[0]["id"]


def save_upload_bundle(province, project_name, project_year, mapped_items, uploaded_files, replace=False):
    db = client()
    project_id = _upsert_identity(db, province.strip(), project_name.strip())
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stored_paths = {}

    for uploaded_file in uploaded_files:
        path = "/".join([
            _slug(province), _slug(project_name), _slug(project_year),
            f"{stamp}-{_slug(uploaded_file.name.rsplit('.', 1)[0])}.{uploaded_file.name.rsplit('.', 1)[-1].lower()}",
        ])
        db.storage.from_(BUCKET).upload(
            path, uploaded_file.getvalue(),
            {"content-type": uploaded_file.type or "application/octet-stream", "upsert": "true"},
        )
        stored_paths[uploaded_file.name] = path

    saved = []
    for item in mapped_items:
        sheet_name = item["source_label"].split(" · ", 1)[1] if " · " in item["source_label"] else None
        upload = db.table("project_uploads").insert({
            "project_id": project_id,
            "project_year": project_year,
            "content_type": item["content_type"],
            "file_name": item["source_file"],
            "sheet_name": sheet_name,
            "record_count": len(item["dataframe"]),
            "storage_path": stored_paths[item["source_file"]],
            "action": "Replaced" if replace else "Uploaded",
        }).execute().data[0]
        db.table("project_dataset_rows").insert({
            "upload_id": upload["id"], "rows": _json_rows(item["dataframe"])
        }).execute()
        saved.append(upload)
    return saved


def fetch_registry(province=None):
    if not is_configured():
        return []
    db = client()
    provinces = {row["id"]: row["name"] for row in db.table("provinces").select("id,name").execute().data}
    projects = db.table("projects").select("id,province_id,name").order("name").execute().data
    return [
        {"province": provinces.get(row["province_id"], ""), "project_name": row["name"]}
        for row in projects
        if row["province_id"] in provinces
        and (not province or provinces[row["province_id"]].casefold() == province.casefold())
    ]


def fetch_accessible_provinces(account_id, role):
    """Return all provinces for admins or the assigned province for an operator."""
    if not is_configured():
        return []
    db = client()
    provinces = db.table("provinces").select("id,name").order("name").execute().data or []
    if role in {"admin", "super_admin"}:
        projects = db.table("projects").select("province_id").execute().data or []
        used_province_ids = {row["province_id"] for row in projects}
        return [row["name"] for row in provinces if row["id"] in used_province_ids]
    if not account_id:
        return []
    assignments = db.table("project_province_access").select("province_id").eq(
        "account_id", str(account_id)
    ).execute().data or []
    allowed_ids = {row["province_id"] for row in assignments}
    return [row["name"] for row in provinces if row["id"] in allowed_ids]


def fetch_project_control_accounts():
    """Return active accounts that can be assigned Project Control province access."""
    if not is_configured():
        return []
    rows = client().table("accounts").select(
        "id,email,username,role,assigned_dashboard,active"
    ).eq("active", True).order("username").execute().data or []
    return [
        row for row in rows
        if row.get("role") == "operator"
        and row.get("assigned_dashboard") == "Project Control"
    ]


def assign_account_province(account_id, province):
    """Assign one Project Control province to an account without changing accounts."""
    db = client()
    province_result = db.table("provinces").upsert(
        {"name": province.strip()}, on_conflict="name"
    ).execute()
    province_id = province_result.data[0]["id"]
    db.table("project_province_access").delete().eq(
        "account_id", str(account_id)
    ).execute()
    db.table("project_province_access").insert({
        "account_id": str(account_id), "province_id": province_id
    }).execute()
    return province_result.data[0]["name"]


def fetch_latest_identity(province=None):
    """Return the province/project owning the most recent permitted upload."""
    if not is_configured():
        return None
    db = client()
    provinces = {row["id"]: row["name"] for row in db.table("provinces").select("id,name").execute().data or []}
    projects = db.table("projects").select("id,province_id,name").execute().data or []
    permitted = {
        row["id"]: row for row in projects
        if row["province_id"] in provinces
        and (not province or provinces[row["province_id"]].casefold() == province.casefold())
    }
    if not permitted:
        return None
    uploads = db.table("project_uploads").select("project_id,uploaded_at").in_(
        "project_id", list(permitted)
    ).order("uploaded_at", desc=True).limit(1).execute().data or []
    if not uploads:
        return None
    project = permitted[uploads[0]["project_id"]]
    return {
        "province": provinces[project["province_id"]],
        "project_name": project["name"],
    }


def fetch_history(province=None):
    if not is_configured():
        return []
    db = client()
    provinces = {row["id"]: row["name"] for row in db.table("provinces").select("id,name").execute().data}
    projects = db.table("projects").select("id,province_id,name").execute().data
    project_map = {
        row["id"]: {"project": row["name"], "province": provinces.get(row["province_id"], "")}
        for row in projects
    }
    uploads = db.table("project_uploads").select(
        "id,project_id,project_year,content_type,file_name,sheet_name,record_count,action,uploaded_at"
    ).order("uploaded_at", desc=True).limit(500).execute().data
    result = []
    for row in uploads:
        identity = project_map.get(row["project_id"], {"project": "", "province": ""})
        if province and identity["province"].casefold() != province.casefold():
            continue
        file_label = row["file_name"] + (f" · {row['sheet_name']}" if row.get("sheet_name") else "")
        result.append({
            "Upload ID": row["id"], "Project ID": row["project_id"],
            "Uploaded At": row["uploaded_at"], "Province": identity["province"],
            "Project Name": identity["project"], "Project Year": row["project_year"],
            "Content Type": row["content_type"], "File / Sheet": file_label,
            "Records": row["record_count"], "Action": row["action"],
        })
    return result


def delete_uploads(upload_ids):
    """Delete selected upload versions and unreferenced raw files."""
    if not upload_ids:
        return 0
    db = client()
    uploads = db.table("project_uploads").select("id,storage_path").in_(
        "id", list(upload_ids)
    ).execute().data or []
    db.table("project_uploads").delete().in_("id", list(upload_ids)).execute()
    for storage_path in {row["storage_path"] for row in uploads if row.get("storage_path")}:
        remaining = db.table("project_uploads").select("id").eq(
            "storage_path", storage_path
        ).limit(1).execute().data or []
        if not remaining:
            db.storage.from_(BUCKET).remove([storage_path])
    return len(uploads)


def delete_project(province, project_name):
    """Delete one project, its upload versions, dataset rows, and raw files."""
    db = client()
    province_rows = db.table("provinces").select("id,name").execute().data or []
    province_id = next(
        (row["id"] for row in province_rows if row["name"].casefold() == province.casefold()),
        None,
    )
    if not province_id:
        return False
    projects = db.table("projects").select("id,name").eq(
        "province_id", province_id
    ).execute().data or []
    project_id = next(
        (row["id"] for row in projects if row["name"].casefold() == project_name.casefold()),
        None,
    )
    if not project_id:
        return False
    uploads = db.table("project_uploads").select("storage_path").eq(
        "project_id", project_id
    ).execute().data or []
    db.table("projects").delete().eq("id", project_id).execute()
    paths = sorted({row["storage_path"] for row in uploads if row.get("storage_path")})
    if paths:
        db.storage.from_(BUCKET).remove(paths)
    remaining_projects = db.table("projects").select("id").eq(
        "province_id", province_id
    ).limit(1).execute().data or []
    if not remaining_projects:
        db.table("provinces").delete().eq("id", province_id).execute()
    return True


def fetch_latest_datasets(province=None, project_name=None):
    """Return the newest saved table for each Project Monitoring content type."""
    if not is_configured():
        return {}
    db = client()
    project_ids = None
    if province or project_name:
        provinces = db.table("provinces").select("id,name").execute().data or []
        province_ids = {
            row["id"] for row in provinces
            if not province or row["name"].casefold() == province.casefold()
        }
        projects = db.table("projects").select("id,province_id,name").execute().data or []
        project_ids = {
            row["id"] for row in projects
            if row["province_id"] in province_ids
            and (not project_name or row["name"].casefold() == project_name.casefold())
        }
        if not project_ids:
            return {}
    query = db.table("project_uploads").select("id,project_id,content_type,uploaded_at")
    if project_ids is not None:
        query = query.in_("project_id", list(project_ids))
    # Use the upload id as a deterministic tie-breaker when multiple files are
    # saved within the same database timestamp.
    uploads = query.order("uploaded_at", desc=True).order("id", desc=True).limit(200).execute().data or []
    newest = {}
    for upload in uploads:
        content_type = upload.get("content_type")
        if content_type and content_type not in newest:
            newest[content_type] = upload["id"]
    result = {}
    for content_type, upload_id in newest.items():
        response = db.table("project_dataset_rows").select("rows").eq(
            "upload_id", upload_id
        ).maybe_single().execute()
        if response.data and isinstance(response.data.get("rows"), list):
            result[content_type] = pd.DataFrame(response.data["rows"])
    return result
