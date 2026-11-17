# views/common.py
# small functions used by more than one page

import os

import folium
import streamlit as st
from streamlit_folium import st_folium

import database as db
from config import DEFAULT_LAT, DEFAULT_LON, STATUS_LIST
from utils import make_maps_link


def init_location_state():
    # keeps the selected location in session state (shared by Register page and chatbot)
    if "sel_lat" not in st.session_state:
        st.session_state.sel_lat = DEFAULT_LAT
        st.session_state.sel_lon = DEFAULT_LON
        st.session_state.loc_picked = False
        st.session_state.last_click = None


def set_location(lat, lon):
    st.session_state.sel_lat = round(float(lat), 5)
    st.session_state.sel_lon = round(float(lon), 5)
    st.session_state.loc_picked = True


def location_picker(map_key):
    # shows a map, the user clicks on it to select the location
    if st.session_state.loc_picked:
        center = [st.session_state.sel_lat, st.session_state.sel_lon]
        zoom = 16
    else:
        center = [DEFAULT_LAT, DEFAULT_LON]
        zoom = 14

    m = folium.Map(location=center, zoom_start=zoom)
    if st.session_state.loc_picked:
        folium.Marker(center, tooltip="Selected location", icon=folium.Icon(color="red")).add_to(m)
    for c in db.get_all_complaints():
        if c["status"] != "Resolved":
            folium.CircleMarker([c["lat"], c["lon"]], radius=5, color="blue", fill=True,
                                tooltip=c["issue_type"]).add_to(m)

    map_data = st_folium(m, height=350, width=700, returned_objects=["last_clicked"], key=map_key)

    if map_data and map_data.get("last_clicked"):
        click = (round(map_data["last_clicked"]["lat"], 5), round(map_data["last_clicked"]["lng"], 5))
        if click != st.session_state.last_click:
            st.session_state.last_click = click
            set_location(click[0], click[1])
            st.rerun()

    if st.session_state.loc_picked:
        st.success("Selected location: " + str(st.session_state.sel_lat) + ", " + str(st.session_state.sel_lon))
    else:
        st.info("No location selected yet.")


def show_status_bar(status):
    if status in STATUS_LIST:
        pos = STATUS_LIST.index(status) + 1
    else:
        pos = 1
    st.progress(pos / len(STATUS_LIST), text="Status: " + status)


def make_download_text(c):
    # builds the text file that the user can download
    text = "Complaint ID: " + str(c["complaint_id"]) + "\n"
    text += "Date: " + str(c["created_at"]) + "\n"
    text += "Department: " + str(c["department"]) + "\n"
    text += "Location: " + make_maps_link(c["lat"], c["lon"]) + "\n"
    text += "\n==== ENGLISH ====\n\n" + str(c["letter_en"]) + "\n"
    text += "\n==== HINDI ====\n\n" + str(c["letter_hi"]) + "\n"
    return text


def show_complaint_details(c):
    st.markdown("### " + c["complaint_id"])
    show_status_bar(c["status"])

    col1, col2 = st.columns(2)
    with col1:
        st.write("**Issue type:**", c["issue_type"])
        st.write("**Department:**", c["department"])
        st.write("**Urgency:**", c["urgency"])
        st.write("**Total reports:**", c["report_count"])
    with col2:
        st.write("**Submitted on:**", c["created_at"])
        st.write("**Last updated:**", c["updated_at"])
        st.write("**Photo check:**", c["photo_status"])
        st.markdown("[Open location in Google Maps](" + make_maps_link(c["lat"], c["lon"]) + ")")

    if c["summary"]:
        st.write("**Summary:**", c["summary"])
    if c["admin_remark"]:
        st.info("Remark from department: " + c["admin_remark"])

    if c["photo_path"] and os.path.exists(c["photo_path"]):
        st.image(c["photo_path"], width=300)

    if c["letter_en"] or c["letter_hi"]:
        with st.expander("View formal letters"):
            st.markdown("**English**")
            st.write(c["letter_en"])
            st.markdown("**Hindi**")
            st.write(c["letter_hi"])
