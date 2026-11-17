# tests/test_basic.py
# to run:  pytest

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database as db
from utils import get_distance, dms_to_decimal
from ai_helper import parse_json


def test_distance_same_point():
    assert get_distance(25.18, 75.83, 25.18, 75.83) < 0.01


def test_distance_about_111m():
    # 0.001 degree of latitude is about 111 meters
    d = get_distance(25.0, 75.0, 25.001, 75.0)
    assert 105 < d < 117


def test_dms_to_decimal():
    assert abs(dms_to_decimal((25, 30, 0), "N") - 25.5) < 0.0001
    assert dms_to_decimal((25, 30, 0), "S") < 0


def test_parse_json_with_fence():
    data = parse_json('```json\n{"a": 1}\n```')
    assert data["a"] == 1


def test_database_flow(tmp_path):
    db.DB_PATH = str(tmp_path / "test.db")
    db.init_db()

    cid = db.add_complaint({"lat": 25.18, "lon": 75.83, "issue_type": "Garbage / Waste", "urgency": "Low"})
    assert cid.startswith("CS-")

    # within 50 m and same type = duplicate
    old, dist = db.find_duplicate(25.1803, 75.83, "Garbage / Waste")
    assert old is not None and dist < 100

    # different type = not a duplicate
    old2, _ = db.find_duplicate(25.1803, 75.83, "Street Light")
    assert old2 is None

    # urgency should increase when the report count increases
    db.increase_count(cid)
    updated = db.increase_count(cid)
    assert updated["report_count"] == 3
    assert updated["urgency"] == "Medium"

    db.update_status(cid, "Resolved", "done")
    assert db.get_complaint(cid)["status"] == "Resolved"
    old3, _ = db.find_duplicate(25.1803, 75.83, "Garbage / Waste")
    assert old3 is None


def test_process_complaint_and_duplicate(tmp_path, monkeypatch):
    import ai_helper
    import complaint_service

    db.DB_PATH = str(tmp_path / "test2.db")
    db.init_db()

    def fake_analyze(client, text, img, name, address, lat, lon):
        return {"issue_type": "Pothole / Road Damage", "department": "PWD (Public Works Department)",
                "urgency": "Medium", "urgency_reason": "test", "summary": "test",
                "photo_shows_civic_issue": True, "photo_matches_description": True,
                "letter_en": "EN", "letter_hi": "HI"}

    monkeypatch.setattr(ai_helper, "analyze_complaint", fake_analyze)
    monkeypatch.setattr(ai_helper, "get_client", lambda key: None)

    # first complaint is new
    r1, err1, _ = complaint_service.process_complaint("k", True, None, None, "pothole", "", "", "", 25.2, 75.8)
    assert err1 == "" and r1["kind"] == "new"

    # same place and type again = duplicate
    r2, err2, _ = complaint_service.process_complaint("k", True, None, None, "pothole", "", "", "", 25.2, 75.8)
    assert r2["kind"] == "duplicate" and r2["report_count"] == 2
    assert r2["complaint_id"] == r1["complaint_id"]


def test_fake_photo_blocked_without_exif(tmp_path):
    from PIL import Image
    import complaint_service

    db.DB_PATH = str(tmp_path / "test3.db")
    db.init_db()
    img = Image.new("RGB", (20, 20), "red")
    info = {"has_camera_info": False, "lat": None, "lon": None, "taken_at": None}
    result, error, _ = complaint_service.process_complaint("k", False, img, info, "x", "", "", "", 25.2, 75.8)
    assert result is None and "Fake complaint blocked" in error
