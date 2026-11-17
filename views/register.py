# views/register.py
# page to register a new complaint using the form

import streamlit as st

import complaint_service
from views.common import init_location_state, location_picker, make_download_text, set_location


def show_result(r):
    # shows the result after the complaint is submitted
    if r["kind"] == "duplicate":
        st.warning(
            "This issue is already reported (" + str(int(r["distance"])) + " m away). "
            "Your report has been added to the existing complaint. "
            "Total reports now: " + str(r["report_count"]) + ", Urgency: " + r["urgency"]
        )
        st.info("Complaint ID to track: " + r["complaint_id"])
    else:
        st.success("Complaint registered successfully! Complaint ID: " + r["complaint_id"])

    st.write("**Issue type:**", r["issue_type"])
    st.write("**Department:**", r["department"])
    st.write("**Urgency:**", r["urgency"], "-", r["urgency_reason"])
    st.write("**Summary:**", r["summary"])

    tab1, tab2 = st.tabs(["English Letter", "Hindi Letter"])
    with tab1:
        st.write(r["letter_en"])
    with tab2:
        st.write(r["letter_hi"])

    st.download_button(
        "Download letters (.txt)",
        data=make_download_text(r),
        file_name=r["complaint_id"] + ".txt",
        mime="text/plain",
    )


def show_register(api_key, demo_mode):
    st.header("Register a Complaint")
    st.write("Upload a photo, describe the problem (Hindi / English / local dialect) and select the place on the map.")
    st.caption("You can also register a complaint by chatting with the Virtual Assistant.")

    init_location_state()
    if "last_result" not in st.session_state:
        st.session_state.last_result = None

    # ---------- Step 1: photo and details ----------
    st.subheader("Step 1: Photo and Details")
    photo = st.file_uploader("Upload issue photo", type=["jpg", "jpeg", "png"])
    user_text = st.text_area("Describe the problem (Hindi, Hinglish, local dialect or English)",
                             placeholder="e.g. There is a big pothole on the road, it is dangerous at night")

    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input("Your name (optional)")
    with c2:
        phone = st.text_input("Phone number (optional)")
    address = st.text_input("Landmark / Area (optional)", placeholder="e.g. Near Railway Station, Kota")

    img = None
    photo_info = None
    if photo is not None:
        try:
            img, photo_info = complaint_service.load_photo(photo.getvalue())
            st.image(img, width=250)
        except Exception:
            st.error("This image file could not be opened. Please try another photo.")
            img = None
            photo_info = None

        if photo_info is not None and photo_info["lat"] is not None:
            st.caption("Photo GPS: " + str(round(photo_info["lat"], 5)) + ", " + str(round(photo_info["lon"], 5)))
            if st.button("Use photo location"):
                set_location(photo_info["lat"], photo_info["lon"])
                st.rerun()

    # ---------- Step 2: location from the map ----------
    st.subheader("Step 2: Select Location on Map")
    st.caption("Click on the place where the problem is (the red marker is your selected location, blue dots are older complaints).")

    location_picker("pick_map")

    with st.expander("Or type the coordinates manually"):
        m1, m2 = st.columns(2)
        with m1:
            man_lat = st.number_input("Latitude", value=float(st.session_state.sel_lat), format="%.5f")
        with m2:
            man_lon = st.number_input("Longitude", value=float(st.session_state.sel_lon), format="%.5f")
        if st.button("Use these coordinates"):
            set_location(man_lat, man_lon)
            st.rerun()

    # ---------- Step 3: submit ----------
    st.subheader("Step 3: Submit")
    if st.button("Submit Complaint", type="primary"):
        st.session_state.last_result = None
        if not api_key:
            st.error("Please enter the Gemini API key in the sidebar (or set it in secrets.toml).")
        elif img is None and not user_text.strip():
            st.warning("Please upload a photo or write a description.")
        elif not st.session_state.loc_picked:
            st.warning("Please select the location on the map first.")
        else:
            with st.spinner("AI is analysing the complaint..."):
                result, error, warnings = complaint_service.process_complaint(
                    api_key, demo_mode, img, photo_info, user_text, name, phone, address,
                    st.session_state.sel_lat, st.session_state.sel_lon)
            for w in warnings:
                st.warning(w)
            if error:
                st.error(error)
            else:
                st.session_state.last_result = result

    if st.session_state.last_result is not None:
        st.divider()
        show_result(st.session_state.last_result)
        if st.button("Clear result"):
            st.session_state.last_result = None
            st.rerun()
