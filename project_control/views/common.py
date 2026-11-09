import streamlit as st

def page_header(title,subtitle=None,show_motto=False):
    left,right=st.columns([2,1])
    with left:
        st.title(title)
        if subtitle:
            st.markdown(f'<div class="page-accent">{subtitle}</div>',unsafe_allow_html=True)
    if show_motto:
        with right:
            st.markdown('<div class="eyebrow">INFRASTRUCTURE FOR A STRONGER TOMORROW ───</div>',unsafe_allow_html=True)

def kpi_card(title,value,note,progress,color):
    st.markdown(f'<div class="kpi" style="--accent:{color}"><div><div class="kpi-label">{title}</div><div class="ring" style="--p:{progress};--c:{color}"><b>{value}</b></div></div><div class="kpi-note">{note}</div></div>',unsafe_allow_html=True)

def stat_card(label,value,icon="analytics"):
    st.markdown(f'<div class="stat-card"><div class="stat-icon"><span class="material-symbols-rounded">{icon}</span></div><div class="stat-copy"><div class="stat-label">{label}</div><div class="stat-value">{value}</div></div></div>',unsafe_allow_html=True)

def placeholder_page(title,description,report_date):
    page_header(title,description)
    with st.container(border=True):
        st.info("This page is ready for its detailed charts and data fields.")
    st.caption(f"Reporting date: {report_date:%d %b %Y}")
