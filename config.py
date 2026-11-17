# config.py
# all the settings are kept in one place so we don't have to change the code again and again

MODEL_NAME = "gemini-2.5-flash"

# center of Kota (the map starts from here)
DEFAULT_LAT = 25.1825
DEFAULT_LON = 75.8391

DUPLICATE_RADIUS_M = 100   # same issue within 100 meters = duplicate
GPS_MISMATCH_M = 500       # allowed difference between photo GPS and selected location
OLD_PHOTO_DAYS = 7         # warn if the photo is older than this

# if True, some demo complaints are added the first time the app runs
SEED_DEMO_DATA = True

# issue type -> department
ISSUE_TYPES = {
    "Pothole / Road Damage": "PWD (Public Works Department)",
    "Garbage / Waste": "Nagar Nigam (Municipal Corporation)",
    "Sewage / Drainage": "Nagar Nigam (Municipal Corporation)",
    "Street Light": "Nagar Nigam (Municipal Corporation)",
    "Water Supply / Leakage": "PHED (Water Supply Department)",
    "Electricity / Power Line": "Electricity Department (Discom)",
    "Stray Animals": "Nagar Nigam (Municipal Corporation)",
    "Other": "Nagar Nigam (Municipal Corporation)",
}

URGENCY_LIST = ["Low", "Medium", "High"]
URGENCY_WEIGHT = {"Low": 1, "Medium": 2, "High": 3}
URGENCY_COLOR = {"Low": "green", "Medium": "orange", "High": "red"}

STATUS_LIST = ["Pending", "In Progress", "Resolved"]
