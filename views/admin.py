# views/admin.py
# admin panel: login, heatmap, charts and status update

import os

import folium
import pandas as pd
import streamlit as st
from folium.plugins import HeatMap
from streamlit_folium import st_folium

import database as db
from config import DEFAULT_LAT, DEFAULT_LON, STATUS_LIST, URGENCY_COLOR, URGENCY_LIST, URGENCY_WEIGHT
from views.common import show_complaint_details


def get_admin_password():
    try:
        if "ADMIN_PASSWORD" in st.secrets:
            return st.secrets["ADMIN_PASSWORD"]
    except Exception:
        pass
    return os.environ.get("ADMIN_PASSWORD", "admin123")


def show_admin():
    st.header("Admin Panel")

    if "admin_ok" not in st.session_state:
        st.session_state.admin_ok = False

    # ---------- login ----------
    if not st.session_state.admin_ok:
        pwd = st.text_input("Admin password", type="password")
        if st.button("Login"):
            if pwd == get_admin_password():
                st.session_state.admin_ok = True
                st.rerun()
            else:
                st.error("Wrong password.")
        return

    if st.button("Logout"):
        st.session_state.admin_ok = False
        st.rerun()

    data = db.get_all_complaints()
    if len(data) == 0:
        st.info("There are no complaints yet.")
        return

    df = pd.DataFrame(data)

    # ---------- filters ----------
    st.subheader("Filters")
    f1, f2, f3 = st.columns(3)
    with f1:
        dept_list = sorted(df["department"].unique())
        sel_dept = st.multiselect("Department", dept_list, default=dept_list)
    with f2:
        sel_status = st.multiselect("Status", STATUS_LIST, default=STATUS_LIST)
    with f3:
        sel_urgency = st.multiselect("Urgency", URGENCY_LIST, default=URGENCY_LIST)

    df = df[df["department"].isin(sel_dept) & df["status"].isin(sel_status) & df["urgency"].isin(sel_urgency)]

    if df.empty:
        st.warning("No complaint found with these filters.")
        return

    # ---------- numbers ----------
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total complaints", len(df))
    m2.metric("Pending", int((df["status"] == "Pending").sum()))
    m3.metric("Resolved", int((df["status"] == "Resolved").sum()))
    m4.metric("High urgency", int((df["urgency"] == "High").sum()))

    # ---------- heatmap ----------
    st.subheader("City Heatmap")
    st.caption("Hot (red) areas mean more and urgent complaints. The marker color shows the urgency.")

    city_map = folium.Map(location=[DEFAULT_LAT, DEFAULT_LON], zoom_start=14)

    points = []
    for _, r in df.iterrows():
        weight = URGENCY_WEIGHT.get(r["urgency"], 1) * int(r["report_count"])
        points.append([r["lat"], r["lon"], weight])
    HeatMap(points, radius=25).add_to(city_map)

    for _, r in df.iterrows():
        popup_text = (r["complaint_id"] + "<br>" + r["issue_type"] + "<br>Urgency: " + r["urgency"] +
                      "<br>Status: " + r["status"] + "<br>Reports: " + str(r["report_count"]))
        folium.Marker(
            [r["lat"], r["lon"]],
            popup=folium.Popup(popup_text, max_width=250),
            icon=folium.Icon(color=URGENCY_COLOR.get(r["urgency"], "blue")),
        ).add_to(city_map)

    st_folium(city_map, height=450, width=700, returned_objects=[], key="admin_map")

    # ---------- charts ----------
    st.subheader("Charts")
    ch1, ch2 = st.columns(2)
    with ch1:
        st.write("Complaints by department")
        st.bar_chart(df.groupby("department").size())
    with ch2:
        st.write("Complaints by issue type")
        st.bar_chart(df.groupby("issue_type").size())

    # ---------- table ----------
    st.subheader("All Complaints")
    show_cols = ["complaint_id", "created_at", "issue_type", "department", "urgency",
                 "status", "report_count", "address", "summary"]
    st.dataframe(df[show_cols])
    st.download_button("Download CSV", data=df[show_cols].to_csv(index=False),
                       file_name="complaints.csv", mime="text/csv")

    # ---------- status update ----------
    st.subheader("Update Complaint Status")
    chosen = st.selectbox("Select complaint", list(df["complaint_id"]))
    c = db.get_complaint(chosen)

    if c is not None:
        show_complaint_details(c)

        new_status = st.selectbox("New status", STATUS_LIST, index=STATUS_LIST.index(c["status"]))
        remark = st.text_input("Remark (visible to the citizen)", value=c["admin_remark"] or "")
        if st.button("Save update"):
            db.update_status(chosen, new_status, remark)
            st.success("Status updated.")
            st.rerun()
