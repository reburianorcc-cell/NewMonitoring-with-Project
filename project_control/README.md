# Project Control Dashboard

Interactive Streamlit prototype based on the approved visual mockups. The distributed app starts without sample project data.

- **Overview:** project KPIs, S-curve, schedule-variance control chart, health indicators, and milestone timeline.
- **Schedule:** schedule KPIs, interactive Master Schedule/Gantt chart, activity-status donut, progress S-curve, upcoming milestones, and critical activities.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL shown by Streamlit, normally `http://localhost:8501`.

## Code structure

- `app.py` — shared sidebar, project selector, reporting date, and page router
- `views/overview.py` — Overview dashboard
- `views/schedule.py` — Schedule dashboard
- `views/cost.py` — Cost-control KPIs, S-curve, cash flow, summary, and risks
- `views/quality.py` — Inspections, NCRs, control chart, defects, and corrective actions
- `views/risk.py` — Risk matrix, exposure, categories, drivers, and priority register
- `views/reports.py` — Report library, generation, approvals, compliance, and exports
- `views/data_upload.py` — province/project assignment, single or multi-file CSV/Excel upload, preview, session storage, and province-filtered upload history
- `views/common.py` — reusable headers and KPI cards

## Project data upload

The upload page accepts either:

- one Excel workbook with sheets named `Basic Project Information`, `Project Components`, `Project Targets`, and `Project Accomplishment`; or
- one to four separate CSV/Excel files that contain those tables.

Every upload requires a typed Province and Project Name. One workbook or multiple CSV/Excel files are stored under that exact project, and upload history records the same identity. If Supabase is not configured, files and history remain in the current Streamlit session only.

## SOCOCA monitoring hierarchy

Dashboard data can later be organized using this SOCOCA hierarchy:

1. Province
2. Project
3. Project Year
4. Monitoring dataset/table

The Province and Project are assigned during file upload. Overview, Schedule, Cost, Quality, Risk, and Reports remain in an empty state until all four required SOCOCA tables are available for that project.

The dashboard header uses Province and Project selections based on the signed-in account's permitted data. New project names are entered from Data Upload.

## Province-based Project Control access

- Admin and Super Admin accounts can view every province and project.
- An Operator must first be assigned to the `Project Control` dashboard in the shared Account Settings.
- In Project Monitoring Settings, the Admin assigns that Operator to one province.
- The Operator then sees only projects belonging to the assigned province.
- Existing projects are selected from the Project list. For a new project, choose `Create New Project` and enter its name.
- Admin and Super Admin can delete a complete Province + Project dashboard from Project Monitoring Settings after confirmation.

Run the latest `supabase_schema.sql` once to create the separate `project_province_access` mapping table. The shared `accounts` table is not modified.

## Supabase setup

1. Create a Supabase project.
2. Run `supabase_schema.sql` in the Supabase SQL Editor.
3. Add these values to `.streamlit/secrets.toml` locally or Streamlit Cloud Secrets:

```toml
[supabase]
url = "https://YOUR_PROJECT.supabase.co"
service_role_key = "YOUR_SERVICE_ROLE_KEY"
```

The service-role key is used only by the Streamlit server. Never commit it or expose it in browser-side code. Once configured, provinces, projects, parsed dataset rows, raw CSV/Excel files, and upload history are stored persistently in Supabase.
