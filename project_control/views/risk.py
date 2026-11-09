import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from .common import page_header,stat_card

def render(project,report_date,project_year="All Years"):
    page_header("PROJECT RISK MANAGEMENT","Identify, assess, mitigate, and monitor project risks.")
    st.info("The uploaded Project Monitoring Template does not contain a risk register. The panels below remain a layout preview until a risk dataset is uploaded.")
    metrics=[("Total Risks","36","warning"),("Critical Risks","4","error"),("High Risks","9","priority_high"),("Mitigated Risks","18","verified_user"),("Total Exposure","₱186M","monitoring")]
    for col,(label,value,icon),i in zip(st.columns(5,gap="small"),metrics,range(5)):
        with col.container(border=True,key=f"whitecard_risk_kpi_{i}"): stat_card(label,value,icon)
    matrix,status,trend=st.columns([1.35,.8,1.65],gap="small")
    with matrix.container(border=True,key="whitecard_risk_matrix"):
        st.markdown('<div class="section-title">Risk Matrix</div>',unsafe_allow_html=True)
        z=[[1,1,2,2,3],[1,2,2,3,3],[2,2,3,3,4],[2,3,3,4,4],[3,3,4,4,5]]
        heat=go.Figure(go.Heatmap(z=z,x=[1,2,3,4,5],y=[1,2,3,4,5],colorscale=[[0,"#56c58a"],[.5,"#ffe174"],[1,"#f15b5b"]],showscale=False))
        heat.add_trace(go.Scatter(x=[5,4,2,4,3,1],y=[5,4,3,3,2,1],mode="markers+text",text=["R-014","R-007","R-005","R-021","R-019","R-028"],textposition="middle right",marker=dict(size=12,color=["#e53935","#e53935","#ffb300","#ffb300","#ffb300","#16a65f"],line=dict(color="white",width=2))))
        heat.update_layout(height=305,margin=dict(l=5,r=25,t=3,b=5),paper_bgcolor="white",plot_bgcolor="white",showlegend=False);heat.update_xaxes(title="Impact",dtick=1);heat.update_yaxes(title="Likelihood",dtick=1)
        st.plotly_chart(heat,use_container_width=True,config={"displayModeBar":False})
    with status.container(border=True,key="whitecard_risk_status"):
        st.markdown('<div class="section-title">Risk Status</div>',unsafe_allow_html=True)
        pie=go.Figure(go.Pie(labels=["Open","Monitoring","Mitigated","Closed"],values=[14,10,8,4],hole=.58,marker=dict(colors=["#2569bd","#16a6a1","#61c28b","#8ca0b5"])));pie.update_layout(height=305,margin=dict(l=5,r=5,t=3,b=5),paper_bgcolor="white",legend=dict(orientation="h",y=-.12));st.plotly_chart(pie,use_container_width=True,config={"displayModeBar":False})
    with trend.container(border=True,key="whitecard_risk_trend"):
        st.markdown('<div class="section-title">Risk Exposure Trend</div>',unsafe_allow_html=True)
        months=pd.date_range("2026-01-01",periods=15,freq="MS");values=[80,95,110,130,155,180,198,215,230,218,205,193,180,168,160]
        line=go.Figure(go.Scatter(x=months,y=values,mode="lines+markers",line=dict(color="#2d7ce5",width=3)));line.update_layout(height=305,margin=dict(l=5,r=5,t=3,b=5),paper_bgcolor="white",plot_bgcolor="white");line.update_yaxes(title="Exposure (₱ Millions)",gridcolor="#e6edf3");line.update_xaxes(tickformat="%b<br>%Y")
        st.plotly_chart(line,use_container_width=True,config={"displayModeBar":False})
    register,categories,drivers=st.columns([1.8,.75,.75],gap="small")
    with register.container(border=True,key="whitecard_risk_register"):
        st.markdown('<div class="section-title">Priority Risk Register</div>',unsafe_allow_html=True)
        st.dataframe(pd.DataFrame({"Risk":["R-007 Right-of-way acquisition","R-014 Material price escalation","R-005 Utility relocation conflicts","R-021 Extreme weather events","R-019 Contractor shortage","R-028 Community opposition"],"Category":["Schedule","Cost","Technical","Environmental","Schedule","Stakeholder"],"Probability":["High","High","Medium","Medium","Low","Low"],"Impact":["High","Very High","High","High","Medium","Low"],"Owner":["C. Santos","M. Reyes","L. Tan","R. Cruz","P. Dela Cruz","A. Lim"],"Status":["Open","Open","Monitoring","Monitoring","Mitigated","Closed"]}),hide_index=True,use_container_width=True,height=295)
    with categories.container(border=True,key="whitecard_risk_categories"):
        st.markdown('<div class="section-title">Risks by Category</div>',unsafe_allow_html=True)
        bar=go.Figure(go.Bar(y=["Stakeholder","Environmental","Safety","Technical","Cost","Schedule"],x=[3,3,5,7,8,10],orientation="h",marker_color="#4d96dd"));bar.update_layout(height=295,margin=dict(l=5,r=5,t=3,b=5),paper_bgcolor="white",plot_bgcolor="white");bar.update_xaxes(gridcolor="#e6edf3");st.plotly_chart(bar,use_container_width=True,config={"displayModeBar":False})
    with drivers.container(border=True,key="whitecard_risk_drivers"):
        st.markdown('<div class="section-title">Top Risk Drivers</div>',unsafe_allow_html=True)
        st.dataframe(pd.DataFrame({"Driver":["Permitting","Price Volatility","Design Changes","Weather","Utility Conflicts"],"Risks":[9,8,6,5,5]}),hide_index=True,use_container_width=True,height=295)
    st.caption(f"Risk status for {project} | {project_year} | {report_date:%d %b %Y}")
