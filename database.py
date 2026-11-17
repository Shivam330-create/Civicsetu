# database.py
# SQLite is used so that the data is not lost when the page is refreshed

import os
import sqlite3
from datetime import datetime

from config import DUPLICATE_RADIUS_M, URGENCY_LIST
from utils import get_distance

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "civicsetu.db")


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_id TEXT UNIQUE,
            created_at TEXT,
            updated_at TEXT,
            name TEXT,
            phone TEXT,
            address TEXT,
            description TEXT,
            issue_type TEXT,
            department TEXT,
            urgency TEXT,
            urgency_reason TEXT,
            summary TEXT,
            lat REAL,
            lon REAL,
            photo_path TEXT,
            photo_status TEXT,
            letter_en TEXT,
            letter_hi TEXT,
            status TEXT,
            admin_remark TEXT,
            report_count INTEGER
        )
    """)
    conn.commit()
    conn.close()


def add_complaint(d):
    # d is a dictionary, returns the complaint ID
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_conn()

    cur = conn.execute(
        """INSERT INTO complaints
        (created_at, updated_at, name, phone, address, description, issue_type,
         department, urgency, urgency_reason, summary, lat, lon, photo_path,
         photo_status, letter_en, letter_hi, status, admin_remark, report_count)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            now, now,
            d.get("name", ""), d.get("phone", ""), d.get("address", ""),
            d.get("description", ""), d.get("issue_type", "Other"),
            d.get("department", ""), d.get("urgency", "Medium"),
            d.get("urgency_reason", ""), d.get("summary", ""),
            d["lat"], d["lon"], d.get("photo_path", ""),
            d.get("photo_status", ""), d.get("letter_en", ""),
            d.get("letter_hi", ""), "Pending", "", 1,
        ),
    )
    row_id = cur.lastrowid

    # ID format: CS-20261116-0001
    complaint_id = "CS-" + datetime.now().strftime("%Y%m%d") + "-" + str(row_id).zfill(4)
    conn.execute("UPDATE complaints SET complaint_id = ? WHERE id = ?", (complaint_id, row_id))

    conn.commit()
    conn.close()
    return complaint_id


def get_all_complaints():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM complaints ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_complaint(complaint_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM complaints WHERE complaint_id = ?", (complaint_id.strip().upper(),)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return dict(row)


def find_duplicate(lat, lon, issue_type):
    # finds an unresolved complaint of the same type within 100 m
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM complaints WHERE issue_type = ? AND status != 'Resolved'", (issue_type,)
    ).fetchall()
    conn.close()

    best = None
    best_dist = None
    for r in rows:
        dist = get_distance(lat, lon, r["lat"], r["lon"])
        if dist <= DUPLICATE_RADIUS_M:
            if best is None or dist < best_dist:
                best = dict(r)
                best_dist = dist
    return best, best_dist


def increase_count(complaint_id):
    # when a duplicate comes, increase the count (more reports = more urgency)
    old = get_complaint(complaint_id)
    if old is None:
        return None

    new_count = old["report_count"] + 1
    urgency = old["urgency"]

    if new_count >= 5:
        urgency = "High"
    elif new_count >= 3 and urgency == "Low":
        urgency = "Medium"

    if urgency not in URGENCY_LIST:
        urgency = "Medium"

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_conn()
    conn.execute(
        "UPDATE complaints SET report_count = ?, urgency = ?, updated_at = ? WHERE complaint_id = ?",
        (new_count, urgency, now, old["complaint_id"]),
    )
    conn.commit()
    conn.close()
    return get_complaint(old["complaint_id"])


def update_status(complaint_id, status, remark):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_conn()
    conn.execute(
        "UPDATE complaints SET status = ?, admin_remark = ?, updated_at = ? WHERE complaint_id = ?",
        (status, remark, now, complaint_id),
    )
    conn.commit()
    conn.close()


def seed_demo_data():
    # add demo data only when the database is empty
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
    conn.close()
    if count > 0:
        return

    demo = [
        ("Pothole / Road Damage", "PWD (Public Works Department)", "High", 25.1825, 75.8391, "Big pothole on main road"),
        ("Garbage / Waste", "Nagar Nigam (Municipal Corporation)", "Medium", 25.1840, 75.8410, "Garbage not collected for many days"),
        ("Street Light", "Nagar Nigam (Municipal Corporation)", "Low", 25.1790, 75.8350, "Street light not working"),
        ("Water Supply / Leakage", "PHED (Water Supply Department)", "High", 25.2138, 75.8648, "Pipeline leakage, water wasting"),
        ("Sewage / Drainage", "Nagar Nigam (Municipal Corporation)", "High", 25.2100, 75.8600, "Drain overflowing on road"),
        ("Electricity / Power Line", "Electricity Department (Discom)", "Medium", 25.1700, 75.8500, "Wire hanging low from pole"),
    ]
    for i in range(len(demo)):
        item = demo[i]
        cid = add_complaint({
            "name": "Demo User",
            "address": "Demo location, Kota",
            "description": item[5],
            "issue_type": item[0],
            "department": item[1],
            "urgency": item[2],
            "urgency_reason": "Demo data",
            "summary": item[5],
            "lat": item[3],
            "lon": item[4],
            "photo_status": "No photo",
        })
        if i == 2:
            update_status(cid, "In Progress", "Team has been assigned")
        if i == 5:
            update_status(cid, "Resolved", "Wire fixed")
