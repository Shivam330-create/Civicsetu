# views/home.py

import streamlit as st

import database as db


def show_home():
    st.title("CivicSetu")
    st.subheader("Smart Grievance Virtual Assistant")
    st.write("AI Lab Mini Project | IIIT Kota | Topic: Citizen Grievance Redressal Assistant")

    data = db.get_all_complaints()
    total = len(data)
    pending = len([c for c in data if c["status"] == "Pending"])
    working = len([c for c in data if c["status"] == "In Progress"])
    resolved = len([c for c in data if c["status"] == "Resolved"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", total)
    c2.metric("Pending", pending)
    c3.metric("In Progress", working)
    c4.metric("Resolved", resolved)

    st.markdown("""
### How it works
1. **Register** - upload a photo, describe the problem (Hindi / English / local dialect) and select the location on the map.
2. **Verify** - EXIF metadata, photo GPS and AI are used to check whether the photo is genuine.
3. **Classify** - Gemini AI finds the issue type, the department and the urgency.
4. **Duplicate check** - if the same issue is already reported within 100 m, no new complaint is created and the priority is increased.
5. **Letter** - a formal application is written automatically in English and Hindi.
6. **Track** - check the status with the complaint ID. The admin can see problem areas on the heatmap.
7. **Virtual Assistant** - you can also register a complaint just by chatting (typing or speaking), and ask for the status of any complaint.
""")
    st.info("Select a page from the left sidebar.")
