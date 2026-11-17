# ai_helper.py
# all the code that talks to the Gemini API is here

import json
import os
import re
import time

import streamlit as st
from google import genai
from google.genai import types

from config import FALLBACK_MODELS, ISSUE_TYPES, MODEL_NAME, URGENCY_LIST


def get_api_key(typed_key):
    # first the key typed in the sidebar, then secrets.toml, then the environment variable
    if typed_key and typed_key.strip():
        return typed_key.strip()
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY", "")


def get_client(api_key):
    return genai.Client(api_key=api_key)


def get_model_name():
    # first secrets.toml, then environment variable, then the default from config.py
    try:
        if "GEMINI_MODEL" in st.secrets:
            return st.secrets["GEMINI_MODEL"]
    except Exception:
        pass
    return os.environ.get("GEMINI_MODEL", MODEL_NAME)


def call_gemini(client, contents, config):
    # tries the main model first, if it is not found (404) the fallback models are tried
    # if the server is busy (503) or the limit is hit (429), we try up to 3 times
    models_to_try = [get_model_name()]
    for m in FALLBACK_MODELS:
        if m not in models_to_try:
            models_to_try.append(m)

    last_error = None
    for model in models_to_try:
        for attempt in range(3):
            try:
                return client.models.generate_content(model=model, contents=contents, config=config)
            except Exception as e:
                last_error = e
                msg = str(e)
                if "404" in msg or "NOT_FOUND" in msg:
                    break              # go to the next model
                if "503" in msg or "429" in msg or "UNAVAILABLE" in msg:
                    time.sleep(2)
                else:
                    raise
    raise last_error


def parse_json(text):
    # sometimes the AI adds ```json ... ``` around the answer, so we remove it
    if text is None:
        raise ValueError("AI returned an empty response")
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError("AI response was not valid JSON")


def to_bool(value, default=True):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in ("true", "yes", "1")


def analyze_complaint(client, user_text, img, name, address, lat, lon):
    # classifies the complaint, decides the urgency and writes the letter in both languages
    issue_list = ", ".join(ISSUE_TYPES.keys())

    if not user_text or not user_text.strip():
        user_text = "(No description given, only photo)"
    if not name or not name.strip():
        name = "Citizen"
    if not address or not address.strip():
        address = "Not given"

    json_format = """{
  "issue_type": "one value from the issue list",
  "urgency": "Low or Medium or High",
  "urgency_reason": "one short sentence",
  "summary": "one line summary in English",
  "photo_shows_civic_issue": true or false,
  "photo_matches_description": true or false,
  "letter_en": "formal complaint letter in English",
  "letter_hi": "formal complaint letter in Hindi (Devanagari)"
}"""

    prompt = (
        "You are an assistant for a citizen grievance system in Kota, Rajasthan, India.\n"
        "Read the complaint below. The text can be in Hindi, Hinglish, English or a local dialect "
        "(like Hadoti or Marwari).\n\n"
        "Complaint text: " + user_text + "\n"
        "Citizen name: " + name + "\n"
        "Landmark / area: " + address + "\n"
        "GPS location: " + str(lat) + ", " + str(lon) + "\n\n"
        "Issue list: " + issue_list + "\n\n"
        "Rules:\n"
        "1. issue_type must be exactly one value from the issue list.\n"
        "2. urgency: High = danger to life or safety (live wire, big pothole on main road, "
        "sewage overflow, no water for days). Medium = daily inconvenience. Low = minor problem.\n"
        "3. If a photo is attached: photo_shows_civic_issue is true only if it really shows a civic "
        "problem (road, garbage, drain, light, water, wire etc). photo_matches_description is true "
        "if the photo agrees with the text. If there is NO photo, set both to true.\n"
        "4. Letters must be formal and polite, addressed to the concerned department officer in Kota, "
        "with Subject, Body and 'Yours faithfully' with the citizen name. Mention the location and the "
        "GPS coordinates. Do not invent any facts, names or dates that were not given.\n"
        "5. Return ONLY valid JSON in this format:\n" + json_format
    )

    contents = [prompt]
    if img is not None:
        contents.append(img)

    config = types.GenerateContentConfig(response_mime_type="application/json")
    res = call_gemini(client, contents, config)
    data = parse_json(res.text)

    # check the AI output and fix it if something is wrong
    issue_type = str(data.get("issue_type", "Other")).strip()
    fixed_type = "Other"
    for t in ISSUE_TYPES:
        if t.lower() == issue_type.lower():
            fixed_type = t
    issue_type = fixed_type

    urgency = str(data.get("urgency", "Medium")).strip().capitalize()
    if urgency not in URGENCY_LIST:
        urgency = "Medium"

    result = {
        "issue_type": issue_type,
        "department": ISSUE_TYPES[issue_type],
        "urgency": urgency,
        "urgency_reason": str(data.get("urgency_reason", "")),
        "summary": str(data.get("summary", "")),
        "photo_shows_civic_issue": to_bool(data.get("photo_shows_civic_issue"), True),
        "photo_matches_description": to_bool(data.get("photo_matches_description"), True),
        "letter_en": str(data.get("letter_en", "")),
        "letter_hi": str(data.get("letter_hi", "")),
    }
    return result


CHAT_SYSTEM_PROMPT = """You are CivicSetu Assistant, a friendly virtual assistant for citizens of Kota, Rajasthan, India.
You help people with civic complaints (potholes, garbage, drainage, street lights, water supply, electricity, stray animals).

You can do three things:
1. Answer questions (how the system works, which department handles which problem, tips for a clear complaint).
2. Register a complaint through chat. The user describes the problem in any language. Then the user selects the location on the map
   and can upload a photo in the "Photo, location and voice tools" section above the chat. When the draft has a problem
   and a location, ask the user to confirm. When the user confirms, the system registers the complaint.
3. Tell the status of a complaint. If complaint details from the database are given in the message, use them.

Every message from the system starts with "Current draft:" which shows what is already collected for the new complaint.
Then comes "User message:".

Return ONLY valid JSON in this format:
{
  "reply": "your reply to the user",
  "intent": "question or report_problem or confirm_submit or check_status or cancel",
  "problem": "full description of the problem or null",
  "landmark": "landmark / area or null",
  "name": "name of the citizen or null"
}

Rules for intent:
- report_problem: the user is describing a civic problem or adding details to it. Put the full problem (old draft problem + new details) in "problem".
  If a landmark or name is given, fill them. In the reply, tell what is still missing (location on the map, optional photo) and ask them to say "confirm" when ready.
- confirm_submit: the user clearly agrees to register the complaint now (for example "confirm", "submit", "yes register it", "haan kar do").
  Keep the reply very short because the system will write the final message.
- cancel: the user wants to cancel or start the draft again.
- check_status: the user asks about the status of a complaint.
- question: anything else.
- Use null for "problem", "landmark" and "name" when the user did not give them in this message.

Other rules:
- Reply in the same language the user uses (Hindi, English or Hinglish). Keep answers short and simple.
- Never say that a complaint is registered by yourself. Only the system registers it after confirm_submit.
- Do not make up phone numbers, officer names or time limits.
- For emergencies (fire, accident, fallen live wire) tell the user to call 112 immediately.
- If the question is not related to civic issues, politely say you can only help with civic complaints."""


def clean_value(value):
    # AI sometimes gives "null" or empty text instead of a real null
    if value is None:
        return None
    value = str(value).strip()
    if value == "" or value.lower() in ("null", "none"):
        return None
    return value


def chat_turn(client, history, user_message, draft_text):
    # history = [{"role": "user"/"assistant", "content": "..."}]
    # returns a dictionary with reply, intent, problem, landmark and name
    contents = []
    for m in history[-10:]:
        role = "user" if m["role"] == "user" else "model"
        if len(contents) == 0 and role == "model":
            continue   # the first message must be from the user
        contents.append(types.Content(role=role, parts=[types.Part(text=m["content"])]))

    full_message = "Current draft: " + draft_text + "\n\nUser message: " + user_message
    contents.append(types.Content(role="user", parts=[types.Part(text=full_message)]))

    config = types.GenerateContentConfig(
        system_instruction=CHAT_SYSTEM_PROMPT,
        response_mime_type="application/json",
    )
    res = call_gemini(client, contents, config)

    try:
        data = parse_json(res.text)
    except Exception:
        # if the JSON is broken, just show the text as a normal answer
        text = res.text or "Sorry, I could not understand that. Please try again."
        return {"reply": text, "intent": "question", "problem": None, "landmark": None, "name": None}

    intent = str(data.get("intent", "question")).strip().lower()
    if intent not in ("question", "report_problem", "confirm_submit", "check_status", "cancel"):
        intent = "question"

    reply = clean_value(data.get("reply")) or "Sorry, I could not understand that. Please try again."

    return {
        "reply": reply,
        "intent": intent,
        "problem": clean_value(data.get("problem")),
        "landmark": clean_value(data.get("landmark")),
        "name": clean_value(data.get("name")),
    }


def transcribe_audio(client, audio_bytes):
    # converts the recorded voice (wav) into text using Gemini
    prompt = ("Transcribe this audio exactly as spoken. The speaker may speak Hindi, English or Hinglish. "
              "Write Hindi words in Devanagari. Return only the transcript, nothing else. "
              "If there is no speech, return an empty text.")
    audio_part = types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav")
    config = types.GenerateContentConfig()
    res = call_gemini(client, [prompt, audio_part], config)
    if not res.text:
        return ""
    return res.text.strip()
