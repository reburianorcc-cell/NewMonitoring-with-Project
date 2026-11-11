import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from .common import page_header,stat_card

def render(project,report_date,project_year="All Years"):
    page_header("PROJECT QUALITY MANAGEMENT","Monitor inspections, nonconformities, defects, testing, and corrective actions.")
    st.info("The uploaded Project Monitoring Template does not contain quality inspection or NCR records. The panels below remain a layout preview until a quality dataset is uploaded.")
    metrics=[("Total Inspections","248","assignment"),("Passed Inspections","221","check"),("Open NCRs","9","fact_check"),("Defects Pending","14","warning"),("First-Time Pass Rate","89%","bar_chart")]
    for col,(label,value,icon),i in zip(st.columns(5,gap="small"),metrics,range(5)):
        with col.container(border=True,key=f"whitecard_quality_kpi_{i}"): stat_card(label,value,icon)
    months=pd.date_range("2026-01-01",periods=15,freq="MS")
    performance,ncr,trend=st.columns([1.4,.9,1.3],gap="small")
    with performance.container(border=True,key="whitecard_quality_inspections"):
        st.markdown('<div class="section-title">Inspection Performance</div>',unsafe_allow_html=True)
        passed=[12,17,20,23,27,30,36,40,45,38,34,29,27,24,21];failed=[3,4,5,7,6,8,9,9,8,8,8,8,7,6,7]
        fig=go.Figure([go.Bar(x=months,y=passed,name="Passed",marker_color="#16a6a1"),go.Bar(x=months,y=failed,name="Failed",marker_color="#2d7ce5")]);fig.update_layout(barmode="stack",height=290,margin=dict(l=5,r=5,t=3,b=5),paper_bgcolor="white",plot_bgcolor="white",legend=dict(orientation="h",y=-.23));fig.update_yaxes(title="Inspections",gridcolor="#e6edf3");fig.update_xaxes(tickformat="%b<br>%Y")
        st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
    with ncr.container(border=True,key="whitecard_quality_ncr"):
        st.markdown('<div class="section-title">NCR Status</div>',unsafe_allow_html=True)
        pie=go.Figure(go.Pie(labels=["Open","Under Review","Closed"],values=[9,5,34],hole=.58,marker=dict(colors=["#2d7ce5","#8fc4f4","#16a6a1"])));pie.update_layout(height=290,margin=dict(l=5,r=5,t=3,b=5),paper_bgcolor="white",legend=dict(orientation="h",y=-.15));st.plotly_chart(pie,use_container_width=True,config={"displayModeBar":False})
    with trend.container(border=True,key="whitecard_quality_control"):
        st.markdown('<div class="section-title">Quality Trend Control Chart</div>',unsafe_allow_html=True)
        rates=[.18,.15,.12,.09,.08,.08,.075,.075,.09,.11,.11,.125,.14,.13,.14];f=go.Figure(go.Scatter(x=months,y=rates,mode="lines+markers",line=dict(color="#2d7ce5",width=3)))
        for y,name,color in [(.21,"UCL","#ef3e3e"),(.125,"Mean","#8596a6"),(.04,"LCL","#16a65f")]: f.add_hline(y=y,line_dash="dash",line_color=color,annotation_text=name)
        f.update_layout(height=290,margin=dict(l=5,r=28,t=3,b=5),paper_bgcolor="white",plot_bgcolor="white");f.update_yaxes(title="Defects per Inspection",gridcolor="#e6edf3");f.update_xaxes(tickformat="%b<br>%Y")
        st.plotly_chart(f,use_container_width=True,config={"displayModeBar":False})
    defects,actions,side=st.columns([1,1.45,.9],gap="small")
    with defects.container(border=True,key="whitecard_quality_defects"):
        st.markdown('<div class="section-title">Defects by Work Package</div>',unsafe_allow_html=True)
        bar=go.Figure(go.Bar(y=["Finishes","MEP","Structural","Civil Works","Design"],x=[8,10,14,18,22],orientation="h",marker_color="#398bea",hoverinfo="skip"));bar.update_layout(height=285,margin=dict(l=5,r=5,t=3,b=5),paper_bgcolor="white",plot_bgcolor="white");bar.update_xaxes(title="Number of Defects",gridcolor="#e6edf3");st.plotly_chart(bar,use_container_width=True,config={"displayModeBar":False,"staticPlot":True})
    with actions.container(border=True,key="whitecard_quality_actions"):
        st.markdown('<div class="section-title">Corrective Action Tracker</div>',unsafe_allow_html=True)
        action_data=pd.DataFrame({"Issue":["Concrete strength below spec","Rebar cover noncompliance","Welding defect - Beam B2","Formwork alignment issue","MEP support installation"],"Owner":["Site Team","QA/QC","Contractor","Site Team","MEP Lead"],"Due Date":["20 Sep","25 Sep","02 Oct","05 Oct","10 Oct"],"Priority":["High","High","Medium","Medium","Low"],"Status":["Open","Open","Under Review","Open","Closed"]})
        action_rows=[]
        for _,row in action_data.iterrows():
            status=str(row["Status"]);priority=str(row["Priority"])
            status_bg,status_text=("#e8f7ee","#177245") if status=="Closed" else (("#fff4d6","#8a5700") if status=="Under Review" else ("#fdecec","#b42318"))
            priority_color={"High":"#b42318","Medium":"#b54708","Low":"#177245"}.get(priority,"#405c73")
            action_rows.append(
                '<div class="quality-action-row">'
                f'<div class="quality-issue">{html.escape(str(row["Issue"]))}</div>'
                f'<div>{html.escape(str(row["Owner"]))}</div><div>{html.escape(str(row["Due Date"]))}</div>'
                f'<div style="font-weight:800;color:{priority_color}">{html.escape(priority)}</div>'
                f'<div><span class="quality-status" style="background:{status_bg};color:{status_text}">{html.escape(status)}</span></div>'
                '</div>'
            )
        st.markdown(
            """
            <style>
            .quality-action-table{height:285px;overflow-y:auto;overflow-x:hidden;border:1px solid #e1eaf1;border-radius:9px;background:#fff}
            .quality-action-row{display:grid;grid-template-columns:minmax(155px,2fr) 82px 68px 66px 92px;align-items:center;border-bottom:1px solid #e5edf3;min-width:0}
            .quality-action-row>div{min-width:0;padding:10px 7px;font-size:10px;line-height:1.3;color:#233f58;white-space:normal;overflow-wrap:anywhere}
            .quality-action-head{position:sticky;top:0;z-index:2;background:#f6f8fb;font-weight:700}
            .quality-action-head>div{color:#667b8d;white-space:nowrap}
            .quality-issue{font-weight:700;color:#174f8a!important}
            .quality-status{display:inline-block;max-width:100%;padding:3px 6px;border-radius:999px;font-size:8px;font-weight:800;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
            .inspection-table{height:176px;overflow-y:auto;overflow-x:hidden;border:1px solid #e1eaf1;border-radius:9px;background:#fff}
            .inspection-row{display:grid;grid-template-columns:64px minmax(70px,1fr) minmax(85px,1.15fr);align-items:center;border-bottom:1px solid #e5edf3}
            .inspection-row>div{min-width:0;padding:9px 7px;font-size:10px;line-height:1.25;color:#233f58;white-space:normal;overflow-wrap:anywhere}
            .inspection-head{position:sticky;top:0;z-index:2;background:#f6f8fb;font-weight:700}
            .inspection-head>div{color:#667b8d;white-space:nowrap}
            @media(max-width:950px){.quality-action-row{grid-template-columns:minmax(125px,1.7fr) 68px 58px 56px 78px}.quality-action-row>div{padding:8px 4px;font-size:9px}.quality-status{font-size:7px;padding:3px 4px}}
            </style>
            <div class="quality-action-table"><div class="quality-action-row quality-action-head">
            <div>Issue</div><div>Owner</div><div>Due Date</div><div>Priority</div><div>Status</div></div>
            """+"".join(action_rows)+"</div>",unsafe_allow_html=True)
    with side:
        with st.container(border=True,key="whitecard_quality_health"):
            st.markdown('<div class="section-title">Quality Health</div>',unsafe_allow_html=True)
            for label,value,color in [("NCR Closure Rate","79%","#16a6a1"),("Open NCRs","9","#ef5261"),("Defects Pending","14","#ef5261")]:
                st.markdown(f'<div class="compact-health"><span>{label}</span><strong style="color:{color}">{value}</strong></div>',unsafe_allow_html=True)
        with st.container(border=True,key="whitecard_quality_upcoming"):
            st.markdown('<div class="section-title">Upcoming Inspections</div>',unsafe_allow_html=True)
            inspections=pd.DataFrame({"Date":["16 Sep","18 Sep","22 Sep","25 Sep"],"Area":["Structural","MEP","Civil Works","Finishes"],"Type":["Rebar","Installation","Concreting","Surface Finish"]})
            inspection_rows="".join(
                '<div class="inspection-row">'
                f'<div>{html.escape(str(row["Date"]))}</div><div>{html.escape(str(row["Area"]))}</div><div>{html.escape(str(row["Type"]))}</div></div>'
                for _,row in inspections.iterrows()
            )
            st.markdown('<div class="inspection-table"><div class="inspection-row inspection-head"><div>Date</div><div>Area</div><div>Type</div></div>'+inspection_rows+'</div>',unsafe_allow_html=True)
    st.caption(f"Quality status for {project} | {project_year} | {report_date:%d %b %Y}")
