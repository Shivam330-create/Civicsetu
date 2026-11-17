# app.py
# CivicSetu - Smart Grievance Virtual Assistant
# AI Lab Mini Project, IIIT Kota
# To run:  streamlit run app.py

import streamlit as st

import ai_helper
import database as db
from config import SEED_DEMO_DATA
from views.admin import show_admin
from views.assistant import show_assistant
from views.home import show_home
from views.register import show_register
from views.track import show_track

st.set_page_config(page_title="CivicSetu", page_icon="🏛️", layout="wide")

# get the database ready
db.init_db()
if SEED_DEMO_DATA:
    db.seed_demo_data()

# ---------- sidebar ----------
st.sidebar.title("CivicSetu")
page = st.sidebar.radio(
    "Menu",
    ["Home", "Register Complaint", "Track Complaint", "Virtual Assistant", "Admin Panel"],
)

st.sidebar.divider()
typed_key = st.sidebar.text_input("Gemini API Key", type="password",
                                  help="If the key is already in secrets or environment variable, you can leave this empty")
api_key = ai_helper.get_api_key(typed_key)
if api_key:
    st.sidebar.caption("API key found.")
else:
    st.sidebar.caption("API key is not set yet.")

demo_mode = st.sidebar.checkbox("Demo mode (skip EXIF/GPS check)", value=False,
                                help="Tick this to test with downloaded photos or screenshots on a laptop. The AI check will still run.")

# ---------- show the selected page ----------
if page == "Home":
    show_home()
elif page == "Register Complaint":
    show_register(api_key, demo_mode)
elif page == "Track Complaint":
    show_track()
elif page == "Virtual Assistant":
    show_assistant(api_key, demo_mode)
else:
    show_admin()
