import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from .common import page_header,stat_card

def render(project,report_date,project_year="All Years"):
    page_header("PROJECT REPORTS","Generate, review, and export consolidated project reports.")
    metrics=[("Reports Generated","48","description"),("Due This Month","6","calendar_month"),("Awaiting Approval","4","schedule"),("Approved Reports","38","check"),("Latest Update","15 Sep 2026","update")]
    for col,(label,value,icon),i in zip(st.columns(5,gap="small"),metrics,range(5)):
        with col.container(border=True,key=f"whitecard_reports_kpi_{i}"): stat_card(label,value,icon)

    reports=pd.DataFrame({"Report Name":["Monthly Progress Report","Cost Report","Schedule Report","Quality Report","Risk Register","Safety Report"],"Type":["Progress","Cost","Schedule","Quality","Risk","Safety"],"Period":["Aug 2026"]*6,"Prepared By":["Project Controls","Commercial","Planning","QA/QC","Risk Management","HSE"],"Status":["Approved","For Review","Approved","Draft","For Review","Approved"],"Updated":["10 Sep","12 Sep","08 Sep","14 Sep","11 Sep","09 Sep"]})
    library_col,generate_col=st.columns([2.15,1],gap="small")
    with library_col.container(border=True,key="whitecard_reports_library"):
        st.markdown('<div class="section-title">Report Library</div>',unsafe_allow_html=True)
        st.dataframe(reports,hide_index=True,use_container_width=True,height=218)
        st.download_button("Export Report Register",reports.to_csv(index=False).encode(),"project_report_register.csv","text/csv",use_container_width=True)
    with generate_col.container(border=True,key="whitecard_reports_generate"):
            st.markdown('<div class="section-title">Generate Report</div>',unsafe_allow_html=True)
            report_type=st.selectbox("Report Type",["Monthly Progress Report","Cost Report","Schedule Report","Quality Report","Risk Register","Safety Report"],key="report_type")
            st.date_input("Date Range",value=(pd.Timestamp("2026-08-01"),pd.Timestamp("2026-08-31")),key="report_range")
            c1,c2=st.columns(2);c1.checkbox("Cost",True);c1.checkbox("Schedule",True);c2.checkbox("Quality",True);c2.checkbox("Risk",False)
            if st.button("Generate Report",type="primary",use_container_width=True): st.success(f"{report_type} prepared.")

    compliance,exports,approval=st.columns([1.15,1,1],gap="small")
    with compliance.container(border=True,key="whitecard_reports_compliance"):
        st.markdown('<div class="section-title">Reporting Compliance</div>',unsafe_allow_html=True)
        months=pd.date_range("2026-01-01",periods=12,freq="MS");ontime=[4,5,8,10,11,12,14,15,13,8,8,6];late=[0,1,1,1,2,2,3,3,2,1,1,1]
        bar=go.Figure([go.Bar(x=months,y=ontime,name="On Time",marker_color="#2d7ce5"),go.Bar(x=months,y=late,name="Late",marker_color="#ef5261")]);bar.update_layout(barmode="stack",height=190,margin=dict(l=4,r=4,t=2,b=2),paper_bgcolor="white",plot_bgcolor="white",legend=dict(orientation="h",y=-.18));bar.update_yaxes(gridcolor="#e6edf3");bar.update_xaxes(tickformat="%b<br>%Y");st.plotly_chart(bar,use_container_width=True,config={"displayModeBar":False})
    with exports.container(border=True,key="whitecard_reports_exports"):
        st.markdown('<div class="section-title">Recent Exports</div>',unsafe_allow_html=True)
        st.dataframe(pd.DataFrame({"Report":["Cost Report","Schedule Report","Risk Register","Quality Report","Progress Report"],"Format":["PDF","Excel","PDF","Excel","CSV"],"Exported":["15 Sep","14 Sep","12 Sep","10 Sep","08 Sep"],"Size":["2.4 MB","1.1 MB","0.9 MB","1.8 MB","0.4 MB"]}),hide_index=True,use_container_width=True,height=190)
    with approval.container(border=True,key="whitecard_reports_approval"):
        st.markdown('<div class="section-title">Approval Status</div>',unsafe_allow_html=True)
        pie=go.Figure(go.Pie(labels=["Draft","For Review","Approved","Returned"],values=[5,4,38,1],hole=.58,marker=dict(colors=["#8fc4f4","#ffca67","#16a68b","#ef5261"]),textinfo="none"));pie.add_annotation(text="<b>48</b><br>Reports",showarrow=False);pie.update_layout(height=190,margin=dict(l=3,r=3,t=0,b=3),paper_bgcolor="white",showlegend=False);st.plotly_chart(pie,use_container_width=True,config={"displayModeBar":False})

    with st.container(border=True,key="whitecard_reports_scheduled"):
        st.markdown('<div class="section-title">Scheduled Reports</div>',unsafe_allow_html=True)
        st.dataframe(pd.DataFrame({"Report":["Progress","Cost","Schedule","Risk","Safety"],"Frequency":["Weekly","Monthly","Monthly","Quarterly","Monthly"],"Next Run":["21 Sep","01 Oct","01 Oct","01 Oct","01 Oct"],"Active":[True]*5}),hide_index=True,use_container_width=True,height=178)
    st.caption(f"Reports workspace for {project} | {project_year} | {report_date:%d %b %Y}")
