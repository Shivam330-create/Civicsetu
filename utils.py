# utils.py
# small helper functions (distance, photo EXIF data etc.)

import math
from datetime import datetime


def get_distance(lat1, lon1, lat2, lon2):
    # haversine formula, the answer is in meters
    R = 6371000  # radius of the earth (meters)
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def dms_to_decimal(value, ref):
    # convert GPS degree-minute-second into decimal degrees
    d = float(value[0])
    m = float(value[1])
    s = float(value[2])
    result = d + m / 60 + s / 3600

    if isinstance(ref, bytes):
        ref = ref.decode(errors="ignore")
    if str(ref).strip().upper() in ("S", "W"):
        result = -result
    return result


def get_photo_info(img):
    # reads camera info, GPS and time from the photo EXIF data
    # NOTE: call this function BEFORE transposing/converting the image
    info = {"has_camera_info": False, "lat": None, "lon": None, "taken_at": None}

    try:
        exif = img.getexif()
    except Exception:
        return info

    if not exif:
        return info

    # when the photo was taken
    try:
        exif_ifd = exif.get_ifd(0x8769)
        info["taken_at"] = exif_ifd.get(36867)   # DateTimeOriginal
    except Exception:
        pass

    # 271 = Make, 272 = Model (name of the phone/camera)
    if exif.get(271) or exif.get(272) or info["taken_at"]:
        info["has_camera_info"] = True

    # GPS location
    try:
        gps = exif.get_ifd(0x8825)
        if gps and 2 in gps and 4 in gps:
            info["lat"] = dms_to_decimal(gps[2], gps.get(1, "N"))
            info["lon"] = dms_to_decimal(gps[4], gps.get(3, "E"))
    except Exception:
        pass

    return info


def is_old_photo(taken_at, days):
    # taken_at format is "2026:11:16 10:30:00"
    if not taken_at:
        return False
    try:
        t = datetime.strptime(str(taken_at), "%Y:%m:%d %H:%M:%S")
        return (datetime.now() - t).days > days
    except Exception:
        return False


def make_maps_link(lat, lon):
    return "https://www.google.com/maps?q=" + str(lat) + "," + str(lon)
