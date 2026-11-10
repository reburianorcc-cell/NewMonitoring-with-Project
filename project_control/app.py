from datetime import date
import streamlit as st
from project_control.views.cost import render as render_cost
from project_control.views.data_upload import render as render_data_upload
from project_control.views.overview import render as render_overview
from project_control.views.reports import render as render_reports
from project_control.views.risk import render as render_risk
from project_control.views.schedule import render as render_schedule
from project_control.views.settings import render as render_settings
from project_control.views.project_data import build_project_data, get_project_data
from project_control.views.supabase_store import (
    fetch_accessible_provinces,
    fetch_latest_datasets,
    fetch_latest_identity,
    fetch_registry,
    is_configured,
)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,500,0,0&display=swap');
*{box-sizing:border-box}html,body,[class*="css"]{font-family:Inter,sans-serif}.stApp,section[data-testid="stMain"],[data-testid="stAppViewContainer"]{background:#f3f7fb!important;color:#15324b}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#163f60 0%,#10314b 58%,#0c263c 100%)!important;border-right:1px solid rgba(255,255,255,.08);box-shadow:7px 0 24px rgba(10,35,56,.08)}[data-testid="stSidebar"] *{color:#fff}
[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"],[data-testid="collapsedControl"]{background:transparent!important;background-color:transparent!important;box-shadow:none!important}
[data-testid="stSidebar"] [data-testid="stSidebarContent"]{padding-left:.45rem!important;padding-right:.45rem!important}[data-testid="stSidebar"] .stButton{margin:.12rem 0;width:100%}[data-testid="stSidebar"] .stButton>button{width:100%;height:44px;min-height:44px;display:flex!important;align-items:center!important;justify-content:flex-start!important;gap:.68rem;border:1px solid transparent;border-radius:9px;background:transparent;color:#d9e8f4;padding:0 .9rem!important;font-weight:600;line-height:1;box-shadow:none;transition:all .18s ease;text-align:left!important}[data-testid="stSidebar"] .stButton>button>div,[data-testid="stSidebar"] .stButton>button>span{display:flex!important;align-items:center!important;justify-content:flex-start!important;width:100%;text-align:left!important}[data-testid="stSidebar"] .stButton>button span[data-testid="stIconMaterial"]{width:21px!important;min-width:21px!important;max-width:21px!important;justify-content:center!important;flex:0 0 21px}[data-testid="stSidebar"] .stButton>button p{margin:0!important;line-height:1!important;white-space:nowrap;text-align:left!important;flex:1}[data-testid="stSidebar"] .stButton>button:hover{background:rgba(58,145,210,.19);color:#fff;border-color:rgba(126,205,255,.18);transform:translateX(1px)}[data-testid="stSidebar"] .stButton>button[kind="primary"]{background:linear-gradient(135deg,#2e82c6,#2467ac);color:#fff;border:1px solid rgba(133,211,255,.25);box-shadow:0 5px 14px rgba(0,73,137,.22)}
[data-testid="stSidebar"] [class*="st-key-project_control_nav_"]{width:calc(100% - 18px)!important;margin:.08rem 0 .08rem 18px!important;position:relative}[data-testid="stSidebar"] [class*="st-key-project_control_nav_"]::before{content:"";position:absolute;left:-10px;top:5px;bottom:5px;width:2px;border-radius:2px;background:#39a7ef44}[data-testid="stSidebar"] [class*="st-key-project_control_nav_"] .stButton{margin:0!important}[data-testid="stSidebar"] [class*="st-key-project_control_nav_"] button{height:40px!important;min-height:40px!important;padding:7px 12px!important;border-radius:9px!important;font-size:.9rem!important}[data-testid="stSidebar"] [class*="st-key-project_control_nav_"] button[kind="secondary"]{background:transparent!important;border-color:transparent!important;box-shadow:none!important}[data-testid="stSidebar"] [class*="st-key-project_control_nav_"] button[kind="primary"]{background:linear-gradient(90deg,#1689e7,#1877c9)!important;border-left:3px solid #27e0e4!important;padding-left:9px!important}
.block-container{max-width:none;padding:.5rem 1.15rem 1.1rem}.block-container div[data-testid="stVerticalBlock"]{gap:.45rem}.block-container div[data-testid="stHorizontalBlock"]{gap:.55rem}h1{color:#102f50!important;font-size:1.85rem!important;font-weight:800!important;letter-spacing:-1.1px;margin:0!important;line-height:1.08!important}h2,h3{color:#15324b!important}
div[data-testid="stVerticalBlockBorderWrapper"],.stColumn div[data-testid="stVerticalBlockBorderWrapper"]{background-color:#fff!important;background-image:none!important;border:1px solid #d9e5ef!important;border-radius:11px;box-shadow:0 4px 14px rgba(18,52,77,.05);transition:transform .2s ease,box-shadow .2s ease}div[data-testid="stVerticalBlockBorderWrapper"]>div,div[data-testid="stVerticalBlockBorderWrapper"]>div>div,div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stVerticalBlock"]{background-color:#fff!important;background-image:none!important}div[data-testid="stVerticalBlockBorderWrapper"]>div{padding-top:.6rem!important;padding-bottom:.6rem!important}div[data-testid="stVerticalBlockBorderWrapper"]:hover{transform:translateY(-1px);box-shadow:0 8px 20px rgba(18,52,77,.08)}
[class*="st-key-whitecard_"]{background:#fff!important;background-color:#fff!important;border-radius:12px!important}[class*="st-key-whitecard_"]>div,[class*="st-key-whitecard_"]>div>div{background-color:#fff!important}
[data-testid="stSelectbox"],[data-testid="stDateInput"]{background:#fff;border:1px solid #dce7f0;border-radius:12px;padding:.55rem .8rem .72rem;box-shadow:0 4px 16px rgba(18,52,77,.04);margin-bottom:.25rem}[data-testid="stSelectbox"] label,[data-testid="stDateInput"] label{margin-bottom:.32rem!important}[data-testid="stSelectbox"] [data-baseweb="select"]>div,[data-testid="stDateInput"] [data-baseweb="input"],[data-testid="stDateInput"] input{border-color:#cad9e5!important;border-radius:8px!important;background-color:#eef2f6!important;background-image:none!important;min-height:46px}[data-testid="stSelectbox"] [data-baseweb="select"]>div:focus-within,[data-testid="stDateInput"] [data-baseweb="input"]:focus-within{background-color:#eef2f6!important}
.eyebrow{color:#2d6cdf;letter-spacing:3.5px;font-size:10px;font-weight:800;text-align:right;padding-top:12px}.page-accent{display:flex;align-items:center;gap:9px;margin:2px 0 10px;color:#587187;font-size:12px}.page-accent:before{content:"";width:34px;height:3px;border-radius:5px;background:linear-gradient(90deg,#16a6a1,#2d7ce5)}
.kpi{display:flex;align-items:center;justify-content:space-between;gap:10px;min-height:108px;padding:0 2px 12px;position:relative}.kpi:after{content:"";position:absolute;left:2px;right:2px;bottom:1px;height:3px;border-radius:3px;background:linear-gradient(90deg,var(--accent,#16a6a1),transparent);opacity:.72}.ring{--p:50;--c:#16a6a1;width:70px;height:70px;border-radius:50%;display:grid;place-items:center;background:conic-gradient(var(--c) calc(var(--p)*1%),#e4edf4 0);position:relative;flex:none;filter:drop-shadow(0 4px 7px rgba(26,67,97,.1))}.ring:before{content:"";position:absolute;inset:8px;border-radius:50%;background:#fff;box-shadow:inset 0 0 0 1px #eef3f6}.ring b{z-index:1;font-size:20px;letter-spacing:-1px;color:#123250}.kpi-label{font-size:13px;font-weight:800;margin-bottom:5px;color:#15324b}.kpi-note{font-size:10px;line-height:1.35;color:#687e91}.section-title{font-size:15px;font-weight:800;color:#15324b;margin-bottom:5px;padding-bottom:7px;border-bottom:1px solid #edf2f6;display:flex;align-items:center;gap:7px}.section-title:before{content:"";width:4px;height:17px;border-radius:4px;background:linear-gradient(180deg,#2d7ce5,#16a6a1);box-shadow:0 0 10px rgba(45,124,229,.24)}
.overview{font-size:13px;line-height:1.75;padding:1px 0 11px}.overview .row{display:grid;grid-template-columns:112px minmax(0,1fr);gap:8px;align-items:start}.overview .row:last-child{align-items:center;padding-top:3px;padding-bottom:7px}.overview span{color:#587087}.overview b{color:#15324b;overflow-wrap:anywhere}.pill{display:inline-block;background:#ffbd45;color:#17324b;padding:5px 18px;border-radius:20px;font-weight:700;line-height:1.25;white-space:nowrap}.health-row{display:flex;align-items:center;border-top:1px solid #edf1f5;padding:12px 2px;font-size:13px}.health-row b{width:95px}.dot{width:15px;height:15px;border-radius:50%;margin-right:12px}.ok{background:#2bb45a}.warn{background:#ffab00}
.phase-wrap{display:flex;width:100%;margin:5px 0 10px}.phase{position:relative;text-align:center;padding:9px 6px;font-size:12px;font-weight:700;background:#e5edf4;flex:1}.phase.done{background:#16a6a1;color:#fff}.phase.active{background:#2d7ce5;color:#fff}.milestones{display:grid;grid-template-columns:repeat(7,1fr);position:relative;margin:20px 3px 4px}.milestones:before{content:"";height:2px;background:#9eafbe;position:absolute;left:1%;right:1%;top:8px}.mile{text-align:center;position:relative;font-size:10px;color:#435b73;padding-top:24px}.diamond{position:absolute;top:1px;left:calc(50% - 7px);width:14px;height:14px;transform:rotate(45deg);background:#98a7b5}.diamond.done{background:#2bb45a}.diamond.active{background:#2d7ce5}
[data-testid="stDataFrame"]{border:1px solid #e1eaf1;border-radius:10px;overflow:hidden}[data-testid="stMetric"]{background:#f7fafc;border:1px solid #e5edf3;border-radius:10px;padding:12px}.stAlert{border-radius:10px!important}hr{border-color:rgba(255,255,255,.1)!important}
.stat-card{height:66px;display:flex;align-items:center;gap:11px}.stat-icon{width:42px;height:42px;border-radius:50%;display:grid;place-items:center;background:#eaf4ff;color:#2177e8;flex:none}.stat-icon .material-symbols-rounded{font-size:24px}.stat-copy{min-width:0}.stat-label{font-size:10px;font-weight:700;color:#314c66;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.stat-value{font-size:22px;line-height:1.05;margin-top:4px;font-weight:800;color:#102f50;white-space:nowrap}.compact-health{display:flex;align-items:center;justify-content:space-between;padding:8px 2px;border-bottom:1px solid #edf2f6}.compact-health:last-child{border-bottom:0}.compact-health span{font-size:11px;color:#4f687e}.compact-health strong{font-size:15px;color:#15324b}[data-testid="stPlotlyChart"]{margin-top:-.15rem!important;margin-bottom:-.25rem!important}
[class*="st-key-whitecard_reports_generate"] [data-testid="stSelectbox"],[class*="st-key-whitecard_reports_generate"] [data-testid="stDateInput"]{padding:.15rem 0 .3rem!important;margin:0!important;border:0!important;border-radius:0!important;box-shadow:none!important}[class*="st-key-whitecard_reports_generate"] [data-testid="stSelectbox"] label,[class*="st-key-whitecard_reports_generate"] [data-testid="stDateInput"] label{margin-bottom:.15rem!important;font-size:11px!important}[class*="st-key-whitecard_reports_generate"] [data-baseweb="select"]>div,[class*="st-key-whitecard_reports_generate"] [data-baseweb="input"],[class*="st-key-whitecard_reports_generate"] [data-testid="stDateInput"] input{min-height:38px!important;height:38px!important;background:#f4f7fa!important}[class*="st-key-whitecard_reports_generate"] [data-testid="stCheckbox"]{min-height:26px!important}[class*="st-key-whitecard_reports_generate"] [data-testid="stCheckbox"] label{padding-top:0!important;padding-bottom:0!important}[class*="st-key-whitecard_reports_generate"] .stButton{margin-top:.1rem!important}[class*="st-key-whitecard_reports_generate"] .stButton>button{min-height:38px!important;height:38px!important}
</style>""", unsafe_allow_html=True)

NAVIGATION=[("Overview",":material/dashboard:"),("Schedule",":material/calendar_month:"),("Cost",":material/bar_chart:"),("Risk",":material/warning:"),("Reports",":material/description:"),("Data Upload",":material/upload_file:")]
if st.session_state.get("admin_role") in {"admin", "super_admin"}:
    NAVIGATION.append(("Settings", ":material/settings:"))

def select_page(page_name):
    st.session_state.project_control_page=page_name

with st.sidebar:
    st.session_state.setdefault("project_control_page","Overview")
    for label,icon in NAVIGATION:
        st.button(
            label,icon=icon,key=f"project_control_nav_{label}",use_container_width=True,
            type="primary" if st.session_state.project_control_page==label else "secondary",
            on_click=select_page,args=(label,),
        )

page=st.session_state.project_control_page
account_role = st.session_state.get("admin_role", "operator")
account_id = st.session_state.get("admin_user_id")
try:
    allowed_provinces = fetch_accessible_provinces(account_id, account_role) if is_configured() else []
    registry = fetch_registry() if is_configured() else []
except Exception as exc:
    allowed_provinces, registry = [], []
    st.session_state.supabase_registry_error = str(exc)

if account_role == "operator" and not allowed_provinces:
    st.error("Your Project Monitoring account has not been assigned to a province. Please contact an Admin.")
    st.stop()

pending_identity = st.session_state.pop("pending_project_identity", None) or {}
province_options = allowed_provinces or sorted({item["province"] for item in registry if item["province"]})
if not province_options:
    province_options = ["No province configured"]
pending_province = pending_identity.get("province")
province_index = province_options.index(pending_province) if pending_province in province_options else 0
top_province,top1,top_year,top2=st.columns([.8,1.5,.65,.9])
with top_province:
    province=st.selectbox("Province", province_options, index=province_index, key="dashboard_province_select")
st.session_state.active_province=province
project_options = [
    item["project_name"] for item in registry
    if item["province"].casefold() == province.casefold()
]
if not project_options:
    project_options = ["No project uploaded"]
pending_project = pending_identity.get("project")
project_index = project_options.index(pending_project) if pending_project in project_options else 0
with top1:
    project=st.selectbox("Project", project_options, index=project_index, key="dashboard_project_select")
if project == "No project uploaded":
    project = ""

identity_key = (province, project)
if st.session_state.get("loaded_project_identity") != identity_key:
    tables = fetch_latest_datasets(province, project) if project and is_configured() else {}
    loaded_data = build_project_data(tables)
    st.session_state.project_monitoring_tables = tables
    if loaded_data:
        loaded_data["province"] = province
        loaded_data["project_name"] = project
        st.session_state.project_monitoring_data = loaded_data
    else:
        st.session_state.pop("project_monitoring_data", None)
    st.session_state.loaded_project_identity = identity_key

active_data = get_project_data()
duration_years = active_data.get("duration_years", 0) if active_data else 0
year_options = ["All Years"] + [f"Year {year}" for year in range(1, duration_years + 1)]
with top_year:
    project_year=st.selectbox("Project Year", year_options, key="project_year")
with top2:
    report_date=st.date_input("Reporting Date",date(2026,9,15))
st.session_state.allowed_project_provinces = allowed_provinces
st.session_state.project_registry = registry

PAGES={"Overview":render_overview,"Schedule":render_schedule,"Cost":render_cost,"Risk":render_risk,"Reports":render_reports,"Data Upload":render_data_upload,"Settings":render_settings}
page_content=st.empty()
page_content.empty()
with page_content.container():
    notice = st.session_state.pop("project_upload_notice", None)
    if notice:
        st.success(notice)
    if page in {"Data Upload", "Settings"}:
        PAGES[page](project,report_date,project_year)
    elif not get_project_data():
        st.info("Upload the four SOCOCA Project Monitoring CSV files to populate this dashboard.")
    else:
        PAGES[page](project,report_date,project_year)
