# CivicSetu - Smart Grievance Virtual Assistant

**AI Lab Mini Project | IIIT Kota | B.Tech 3rd Semester**
Topic: Citizen Grievance Redressal Assistant

CivicSetu is a web app where a citizen can report a civic problem (pothole, garbage, drainage, street light,
water, electricity) using a photo and a description in Hindi, English or a local dialect. The AI sends the
complaint to the right department and writes the formal application automatically.

## Features

- Photo upload and description (Hindi, Hinglish, local dialect or English)
- Select the location by clicking on the map (or use the GPS stored in the photo)
- Fake complaint detection: EXIF metadata check, photo GPS vs selected location check, and a Gemini check to see if the photo really shows a civic problem
- Gemini AI finds the issue type, the department and the urgency (Low / Medium / High)
- Formal letter in English and Hindi, which can be downloaded
- Duplicate check: if the same type of issue is reported within 100 m, no new complaint is created. The report count increases and the urgency is raised automatically
- SQLite database (data is saved even after a page refresh)
- Complaint ID and a Track Complaint page (Pending / In Progress / Resolved)
- Virtual Assistant chatbot:
  - answers questions about the system and the departments
  - registers a complaint through chat (the user describes the problem, picks the location on the map, optionally uploads a photo and says "confirm")
  - shows the status of a complaint when the complaint ID is written in the message
  - voice input: the user can record a message in Hindi / English / Hinglish and it is converted to text by Gemini
- Admin panel (password protected): heatmap (weighted by urgency and number of reports), filters, charts, CSV download and status update

## Tech Stack

Python, Streamlit, Google Gemini API (`google-genai`), SQLite, Folium + streamlit-folium, Pillow, Pandas

## Folder Structure

```
CivicSetu/
├── app.py                # main file, sidebar menu
├── config.py             # settings (issue types, departments, radius etc.)
├── complaint_service.py  # main logic to register a complaint (used by the form and the chatbot)
├── database.py           # SQLite functions
├── ai_helper.py          # Gemini API (analysis, chatbot, voice to text)
├── utils.py              # distance (haversine), EXIF reading
├── views/
│   ├── home.py
│   ├── register.py
│   ├── track.py
│   ├── assistant.py
│   ├── admin.py
│   └── common.py
├── tests/test_basic.py
├── requirements.txt
├── uploads/              # complaint photos are saved here
└── .streamlit/secrets.toml.example
```

## Setup

1. Python 3.10 or newer should be installed.
2. Clone the repo and go inside the folder:
   ```
   git clone <your-repo-link>
   cd CivicSetu
   ```
3. Create a virtual environment (optional but good):
   ```
   python -m venv venv
   venv\Scripts\activate        (Windows)
   source venv/bin/activate     (Linux / Mac)
   ```
4. Install the libraries:
   ```
   pip install -r requirements.txt
   ```
5. Get a Gemini API key from https://aistudio.google.com/apikey
6. You can give the key in two ways:
   - Paste it in the sidebar of the app, or
   - Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and put the key inside
7. Run the app:
   ```
   streamlit run app.py
   ```

## How to Use

- **Register Complaint**: add a photo and description, click on the map and press Submit.
- **Demo mode** (sidebar): tick it when you want to test with a downloaded photo or a screenshot. The EXIF/GPS check will be skipped. Keep it off for real use.
- **Virtual Assistant**: type or record a message such as "there is a big pothole near the railway station". Then select the location on the map (inside the "Photo, location and voice tools" section), optionally upload a photo and write "confirm". To check a complaint, write its ID, for example "status of CS-20261116-0001". Voice recording works on localhost or on an HTTPS site, and the browser will ask for the microphone permission.
- **Admin Panel**: the default password is `admin123`. To change it, set `ADMIN_PASSWORD` in `secrets.toml`.
- On the first run, 6 demo complaints are added so that the heatmap is not empty. To turn this off, set `SEED_DEMO_DATA = False` in `config.py`. To reset all data, delete `data/civicsetu.db`.

## Tests

```
pip install pytest
pytest
```

## Limitations

- SQLite is a local file. If the app is deployed on Streamlit Cloud, the data can be lost after a restart (a real system should use PostgreSQL / Firebase).
- EXIF data can be edited, so an AI check is also used, but it is still not 100% fool-proof.
- Admin login uses a simple password.
- The free Gemini API has rate limits.
- The location is selected on the map by the user, the chatbot does not convert a landmark name into coordinates.

## Future Scope

- SMS / email notification when a complaint is resolved
- Before / after photo when a complaint is resolved
- Proper login for officers
- Voice input (Hindi speech to text)
- PostgreSQL database and online deployment

## Team

- [SHIVAM MEENA] - [2025KUAD3028]

Guide: [Pooja Sharma]
