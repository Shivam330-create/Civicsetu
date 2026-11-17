# views/track.py
# page to see the complaint status using the complaint ID

import streamlit as st

import database as db
from views.common import show_complaint_details


def show_track():
    st.header("Track Your Complaint")
    st.write("Enter your complaint ID (for example CS-20261116-0001).")

    cid = st.text_input("Complaint ID")

    if cid.strip():
        c = db.get_complaint(cid)
        if c is None:
            st.error("No complaint found with this ID. Please check the ID again.")
        else:
            show_complaint_details(c)
