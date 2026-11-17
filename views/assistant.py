# views/assistant.py
# virtual assistant: answers questions, registers complaints through chat, checks status
# the user can type or speak (voice input)

import re

import streamlit as st

import ai_helper
import complaint_service
import database as db
from views.common import init_location_state, location_picker, make_download_text

GREETING = ("Hello! I am the CivicSetu Assistant. I can answer your questions, check the status of a complaint "
            "(just write the complaint ID) and register a new complaint through chat. "
            "To report a problem, just tell me what the problem is. You can type or use the voice recorder below.")


def reset_draft():
    st.session_state.draft = {"problem": None, "landmark": None, "name": None}
    st.session_state.photo_key += 1          # new key = photo uploader becomes empty
    st.session_state.loc_picked = False


def draft_to_text(img):
    # short text about the draft, this is sent to the AI with every message
    d = st.session_state.draft
    text = "problem: " + (d["problem"] or "not given")
    text += " | landmark: " + (d["landmark"] or "not given")
    text += " | name: " + (d["name"] or "not given")
    text += " | location selected on map: " + ("yes" if st.session_state.loc_picked else "no")
    text += " | photo uploaded: " + ("yes" if img is not None else "no")
    return text


def register_from_chat(api_key, demo_mode, img, photo_info):
    # registers the complaint using the draft, returns (reply_text, success)
    d = st.session_state.draft

    if not d["problem"] and img is None:
        return "I do not know the problem yet. Please describe the problem or upload a photo first.", False

    if not st.session_state.loc_picked:
        return ("Please select the location on the map first. Open the section "
                "'Photo, location and voice tools' above the chat and click on the map. Then say confirm again."), False

    with st.spinner("Registering your complaint..."):
        result, error, warnings = complaint_service.process_complaint(
            api_key, demo_mode, img, photo_info, d["problem"] or "", d["name"] or "", "",
            d["landmark"] or "", st.session_state.sel_lat, st.session_state.sel_lon)

    if error:
        return "I could not register the complaint. " + error, False

    st.session_state.chat_result = result

    if result["kind"] == "duplicate":
        text = ("This issue was already reported " + str(int(result["distance"])) + " m away, so I added your "
                "report to the existing complaint.")
        text += "\n\n**Complaint ID:** " + result["complaint_id"]
        text += "\n\n**Total reports:** " + str(result["report_count"]) + " | **Urgency:** " + result["urgency"]
    else:
        text = "Your complaint is registered."
        text += "\n\n**Complaint ID:** " + result["complaint_id"]
        text += "\n\n**Issue:** " + result["issue_type"]
        text += "\n\n**Department:** " + result["department"]
        text += "\n\n**Urgency:** " + result["urgency"] + " (" + result["urgency_reason"] + ")"

    text += "\n\nYou can download the formal letters below and track the complaint on the Track Complaint page."
    for w in warnings:
        text += "\n\nNote: " + w
    return text, True


def show_assistant(api_key, demo_mode):
    st.header("Virtual Assistant")
    st.caption("Ask questions, check a complaint status or register a new complaint by chatting.")

    if not api_key:
        st.warning("Please enter the Gemini API key in the sidebar.")
        return

    # ---------- session state ----------
    init_location_state()
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "draft" not in st.session_state:
        st.session_state.draft = {"problem": None, "landmark": None, "name": None}
    if "photo_key" not in st.session_state:
        st.session_state.photo_key = 0
    if "last_audio" not in st.session_state:
        st.session_state.last_audio = None
    if "chat_result" not in st.session_state:
        st.session_state.chat_result = None

    client = ai_helper.get_client(api_key)

    # ---------- tools: photo, location, voice ----------
    img = None
    photo_info = None
    audio = None
    with st.expander("Photo, location and voice tools", expanded=True):
        photo = st.file_uploader("Upload issue photo (optional)", type=["jpg", "jpeg", "png"],
                                 key="chat_photo_" + str(st.session_state.photo_key))
        if photo is not None:
            try:
                img, photo_info = complaint_service.load_photo(photo.getvalue())
                st.image(img, width=200)
            except Exception:
                st.error("This image file could not be opened. Please try another photo.")
                img = None
                photo_info = None

        st.write("**Select the location of the problem on the map:**")
        location_picker("chat_map")

        st.write("**Voice input:** record your message and it will be sent to the assistant.")
        audio = st.audio_input("Record your message", key="chat_audio")

    # ---------- get the new message (typed or voice) ----------
    typed = st.chat_input("Type your message...")
    question = typed
    from_voice = False

    if typed is None and audio is not None:
        audio_bytes = audio.getvalue()
        if hash(audio_bytes) != st.session_state.last_audio:
            st.session_state.last_audio = hash(audio_bytes)
            try:
                with st.spinner("Converting your voice to text..."):
                    text = ai_helper.transcribe_audio(client, audio_bytes)
                if text:
                    question = text
                    from_voice = True
                else:
                    st.warning("Could not hear anything in the recording. Please try again.")
            except Exception as e:
                st.error("Voice could not be converted to text. Error: " + str(e))

    # ---------- process the message ----------
    need_rerun = False
    if question:
        shown_question = question
        if from_voice:
            shown_question = "(voice) " + question

        # if the message has a complaint ID, get its details from the database
        message_for_ai = question
        ids = re.findall(r"CS-\d{8}-\d{4,}", question.upper())
        for cid in ids:
            c = db.get_complaint(cid)
            if c is None:
                message_for_ai += "\n\n[Database note: complaint " + cid + " not found]"
            else:
                message_for_ai += ("\n\n[Database note: complaint " + cid + " | issue: " + c["issue_type"] +
                                   " | department: " + c["department"] + " | urgency: " + c["urgency"] +
                                   " | status: " + c["status"] + " | reports: " + str(c["report_count"]) +
                                   " | remark: " + (c["admin_remark"] or "none") + "]")

        try:
            with st.spinner("Thinking..."):
                data = ai_helper.chat_turn(client, st.session_state.chat_history, message_for_ai, draft_to_text(img))
            reply = data["reply"]
            intent = data["intent"]

            # update the draft with the new details
            if intent == "cancel":
                reset_draft()
                need_rerun = True
            else:
                d = st.session_state.draft
                if data["problem"]:
                    d["problem"] = data["problem"]
                if data["landmark"]:
                    d["landmark"] = data["landmark"]
                if data["name"]:
                    d["name"] = data["name"]

            if intent == "confirm_submit":
                reply, success = register_from_chat(api_key, demo_mode, img, photo_info)
                if success:
                    reset_draft()
                    need_rerun = True
        except Exception as e:
            reply = "Sorry, I could not connect to the AI right now. Error: " + str(e)

        st.session_state.chat_history.append({"role": "user", "content": shown_question})
        st.session_state.chat_history.append({"role": "assistant", "content": reply})

        if need_rerun:
            st.rerun()    # refresh the photo uploader and the draft status

    # ---------- show draft status and chat ----------
    st.info("Complaint draft -> " + draft_to_text(img))

    with st.chat_message("assistant"):
        st.write(GREETING)

    for m in st.session_state.chat_history:
        with st.chat_message(m["role"]):
            st.write(m["content"])

    if st.session_state.chat_result is not None:
        r = st.session_state.chat_result
        st.download_button("Download letters of " + r["complaint_id"] + " (.txt)",
                           data=make_download_text(r),
                           file_name=r["complaint_id"] + ".txt",
                           mime="text/plain")

    if st.session_state.chat_history:
        if st.button("Clear chat"):
            st.session_state.chat_history = []
            st.session_state.chat_result = None
            st.rerun()
