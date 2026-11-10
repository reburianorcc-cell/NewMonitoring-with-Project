import __main__

import streamlit as st

from .common import page_header
from .supabase_store import (
    assign_account_province,
    delete_project,
    fetch_accessible_provinces,
    fetch_project_control_accounts,
    fetch_registry,
    is_configured,
)


def render(project, report_date, project_year="All Years"):
    page_header(
        "PROJECT MONITORING SETTINGS",
        "Manage account access using the same controls as Incident Monitoring.",
    )
    role = st.session_state.get("admin_role", "operator")
    username = st.session_state.get("admin_username", "")

    with st.container(border=True, key="whitecard_project_account_access"):
        st.markdown('<div class="section-title">Account Access</div>', unsafe_allow_html=True)
        st.write(f"Signed in as **{username}**")
        st.write(f"Account role: **{role.replace('_', ' ').title()}**")
        st.caption(
            "Project Monitoring uses the shared SOCOCA account, password, role, "
            "active status, and dashboard assignment from Incident Monitoring."
        )
        if role in {"admin", "super_admin"}:
            if st.button(
                "Open Account and Access Settings",
                icon=":material/manage_accounts:",
                type="primary",
                use_container_width=True,
            ):
                __main__.show_admin_settings(
                    username,
                    role,
                    [
                        "Incident Dashboard", "Evacuation Dashboard",
                        "CLUP Monitoring", "Project Monitoring",
                    ],
                    upload_history_scope="project",
                )
        else:
            st.info("Only Admin and Super Admin accounts can manage user access.")

    with st.container(border=True, key="whitecard_project_access_rules"):
        st.markdown('<div class="section-title">Access Rules</div>', unsafe_allow_html=True)
        st.markdown(
            "- **Super Admin:** full account, access, upload, and dashboard control.\n"
            "- **Admin:** account management and Project Monitoring uploads.\n"
            "- **Operator:** access only to the dashboard assigned by an Admin."
        )

    if role in {"admin", "super_admin"}:
        with st.container(border=True, key="whitecard_project_province_access"):
            st.markdown('<div class="section-title">Project Province Access</div>', unsafe_allow_html=True)
            st.caption(
                "Assign one province to each Project Monitoring operator. This does not change the shared accounts table."
            )
            if not is_configured():
                st.warning("Connect Supabase before assigning province access.")
                return
            accounts = fetch_project_control_accounts()
            if not accounts:
                st.info("Assign an account to the Project Monitoring dashboard first.")
                return
            labels = {
                f"{row['username']} — {row['email']}": row for row in accounts
            }
            account_label = st.selectbox("Project Monitoring Account", list(labels))
            province_name = st.text_input(
                "Assigned Province", placeholder="Example: Bohol"
            ).strip()
            if st.button(
                "Save Province Access", type="primary", use_container_width=True,
                disabled=not province_name,
            ):
                saved = assign_account_province(labels[account_label]["id"], province_name)
                st.success(f"{labels[account_label]['username']} can now access {saved} projects.")

        with st.container(border=True, key="whitecard_delete_project_dashboard"):
            st.markdown('<div class="section-title">Delete Project Dashboard</div>', unsafe_allow_html=True)
            st.caption("Delete one Province + Project dashboard and all of its uploaded versions.")
            projects = fetch_registry()
            if not projects:
                st.info("No uploaded project dashboard is available.")
            else:
                labels = {
                    f"{item['province']} — {item['project_name']}": item
                    for item in projects
                }
                selected_label = st.selectbox(
                    "Project Dashboard", list(labels), key="settings_delete_project_dashboard"
                )
                confirm_delete = st.checkbox(
                    "I confirm permanent deletion of this project dashboard",
                    key="settings_confirm_delete_project_dashboard",
                )
                if st.button(
                    "Delete Project Dashboard",
                    use_container_width=True,
                    disabled=not confirm_delete,
                ):
                    selected = labels[selected_label]
                    if delete_project(selected["province"], selected["project_name"]):
                        for key in (
                            "project_monitoring_data", "project_monitoring_tables",
                            "project_registry", "loaded_project_identity",
                        ):
                            st.session_state.pop(key, None)
                        st.success(f"{selected_label} was deleted.")
                        st.rerun()
                    st.error("The selected project dashboard could not be deleted.")
