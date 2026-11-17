# complaint_service.py
# main logic to register a complaint
# it is used by the Register page and also by the chatbot, so the code is written only once

import io
import os
import uuid

from PIL import Image, ImageOps

import ai_helper
import database as db
from config import GPS_MISMATCH_M, OLD_PHOTO_DAYS
from utils import get_distance, get_photo_info, is_old_photo

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")


def load_photo(raw_bytes):
    # opens the uploaded photo, returns (image, exif_info)
    raw_img = Image.open(io.BytesIO(raw_bytes))
    info = get_photo_info(raw_img)                 # read the EXIF first
    img = ImageOps.exif_transpose(raw_img).convert("RGB")
    img.thumbnail((1280, 1280))                    # resize so that the API call is faster
    return img, info


def process_complaint(api_key, demo_mode, img, photo_info, user_text, name, phone, address, lat, lon):
    # returns (result, error, warnings)
    # result is None if the complaint was blocked or something failed
    warnings = []

    # step 1: check if the photo is real (EXIF + GPS check)
    if img is not None and not demo_mode:
        if not photo_info["has_camera_info"]:
            error = ("Fake complaint blocked: no camera metadata (EXIF) found in the photo. "
                     "Screenshots and edited photos are not allowed. "
                     "Please upload a photo taken directly with the camera.")
            return None, error, warnings
        if photo_info["lat"] is not None:
            d = get_distance(lat, lon, photo_info["lat"], photo_info["lon"])
            if d > GPS_MISMATCH_M:
                error = ("The photo GPS location is " + str(int(d)) +
                         " m away from the selected location. Please select the correct place.")
                return None, error, warnings
        else:
            warnings.append("No GPS location found in the photo (camera location may be off). "
                            "Only the selected location will be used.")
        if is_old_photo(photo_info["taken_at"], OLD_PHOTO_DAYS):
            warnings.append("This photo looks older than " + str(OLD_PHOTO_DAYS) + " days.")

    # step 2: analysis by AI
    client = ai_helper.get_client(api_key)
    try:
        ai = ai_helper.analyze_complaint(client, user_text, img, name, address, lat, lon)
    except Exception as e:
        error = "Could not get a response from AI. Please check the API key and internet. Error: " + str(e)
        return None, error, warnings

    # step 3: photo check by AI (to catch screenshots / random photos)
    if img is not None:
        if not ai["photo_shows_civic_issue"]:
            return None, "Fake complaint blocked: the photo does not show any civic problem.", warnings
        if not ai["photo_matches_description"]:
            warnings.append("The photo and the description do not match. The admin will check this.")

    # step 4: duplicate check (same issue within 100 m)
    old, dist = db.find_duplicate(lat, lon, ai["issue_type"])

    if old is not None:
        updated = db.increase_count(old["complaint_id"])
        result = {
            "kind": "duplicate",
            "complaint_id": updated["complaint_id"],
            "distance": dist,
            "report_count": updated["report_count"],
            "urgency": updated["urgency"],
        }
    else:
        # save the photo
        photo_path = ""
        if img is not None:
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            photo_path = os.path.join(UPLOAD_DIR, uuid.uuid4().hex[:12] + ".jpg")
            img.save(photo_path, "JPEG", quality=85)

        if img is None:
            photo_status = "No photo"
        elif demo_mode:
            photo_status = "AI checked (EXIF skipped in demo mode)"
        else:
            photo_status = "EXIF + AI verified"

        complaint_id = db.add_complaint({
            "name": name, "phone": phone, "address": address,
            "description": user_text,
            "issue_type": ai["issue_type"], "department": ai["department"],
            "urgency": ai["urgency"], "urgency_reason": ai["urgency_reason"],
            "summary": ai["summary"],
            "lat": lat, "lon": lon,
            "photo_path": photo_path, "photo_status": photo_status,
            "letter_en": ai["letter_en"], "letter_hi": ai["letter_hi"],
        })
        result = {"kind": "new", "complaint_id": complaint_id, "urgency": ai["urgency"]}

    # keep the letters etc. in the result so they can be shown later
    saved = db.get_complaint(result["complaint_id"])
    result["issue_type"] = ai["issue_type"]
    result["department"] = ai["department"]
    result["urgency_reason"] = ai["urgency_reason"]
    result["summary"] = ai["summary"]
    result["letter_en"] = ai["letter_en"]
    result["letter_hi"] = ai["letter_hi"]
    result["created_at"] = saved["created_at"]
    result["lat"] = saved["lat"]
    result["lon"] = saved["lon"]

    return result, "", warnings
