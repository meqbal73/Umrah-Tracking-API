from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import math

# تهيئة الـ API
app = FastAPI(
    title="Umrah Tracking API",
    description="API لتتبع أشواط الطواف والسعي وحساب الوقت بناءً على الموقع الجغرافي",
    version="1.0"
)

# قاعدة بيانات وهمية (في الذاكرة) لحفظ بيانات المعتمرين
sessions_db = {}

# ==========================================
# 1. النماذج (Models) التي يستقبلها الـ API
# ==========================================
class LocationData(BaseModel):
    session_id: str
    lat: float
    lon: float

# ==========================================
# 2. دوال مساعدة (Helper Functions)
# ==========================================
def calculate_distance(lat1, lon1, lat2, lon2):
    """حساب المسافة الجغرافية بين نقطتين بالأمتار"""
    R = 6371e3 # نصف قطر الأرض
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))

# ==========================================
# 3. مسارات الطواف (Tawaf Endpoints)
# ==========================================
@app.post("/api/tawaf/start")
async def start_tawaf(data: LocationData):
    """نقطة بداية الطواف وتحديد موقع الصفر وتشغيل المؤقت"""
    now = datetime.now()
    sessions_db[data.session_id] = {
        "umrah_start_time": now,
        "tawaf_start_time": now,
        "saee_start_time": None,
        "tawaf_start_lat": data.lat,
        "tawaf_start_lon": data.lon,
        "tawaf_rounds": 0,
        "tawaf_completed": False,
        "is_away": False, # للتحقق من الابتعاد عن نقطة البداية
        "saee_rounds": 0,
        "saee_completed": False
    }
    return {"status": "success", "message": "تم بدء الطواف", "rounds": 0}

@app.post("/api/tawaf/track")
async def track_tawaf(data: LocationData):
    """تتبع حركة المعتمر وزيادة العداد عند العودة لنقطة البداية"""
    session = sessions_db.get(data.session_id)
    if not session or session["tawaf_completed"]:
        return {"status": "error", "message": "الطواف غير نشط أو مكتمل"}

    distance = calculate_distance(session["tawaf_start_lat"], session["tawaf_start_lon"], data.lat, data.lon)

    # شروط حساب الشوط (الابتعاد أكثر من 30 متر ثم العودة لأقل من 15 متر)
    if distance > 30:
        session["is_away"] = True
    elif distance < 15 and session["is_away"]:
        session["tawaf_rounds"] += 1
        session["is_away"] = False # تصفير الحالة للشوط القادم

        if session["tawaf_rounds"] == 7:
            session["tawaf_completed"] = True
            return {"status": "completed", "alert": "أتممت 7 أشواط! الطواف انتهى.", "rounds": 7}
        elif session["tawaf_rounds"] == 6:
            return {"status": "tracking", "alert": "تنبيه: أنت في الشوط الأخير!", "rounds": 6}

    elapsed_time = int((datetime.now() - session["tawaf_start_time"]).total_seconds())
    return {
        "status": "tracking",
        "rounds": session["tawaf_rounds"],
        "distance_to_start_meters": round(distance, 2),
        "timer_seconds": elapsed_time
    }

# ==========================================
# 4. مسارات السعي (Saee Endpoints)
# ==========================================
@app.post("/api/saee/start")
async def start_saee(data: LocationData):
    """بدء السعي (لا يفتح إلا إذا اكتمل الطواف)"""
    session = sessions_db.get(data.session_id)
    if not session or not session["tawaf_completed"]:
        return {"status": "error", "message": "يجب إتمام الطواف أولاً"}

    session["saee_start_time"] = datetime.now()
    session["saee_start_lat"] = data.lat
    session["saee_start_lon"] = data.lon
    session["is_away"] = False # إعادة استخدام المتغير للسعي

    return {"status": "success", "message": "تم بدء السعي", "rounds": 0}

@app.post("/api/saee/track")
async def track_saee(data: LocationData):
    """تتبع حركة السعي"""
    session = sessions_db.get(data.session_id)
    if not session or session["saee_completed"] or not session["saee_start_time"]:
        return {"status": "error", "message": "السعي غير نشط"}

    distance = calculate_distance(session["saee_start_lat"], session["saee_start_lon"], data.lat, data.lon)

    # السعي مسافته أطول، نعتبره ابتعد إذا تجاوز 100 متر وعاد لدائرة 20 متر
    if distance > 100:
        session["is_away"] = True
    elif distance < 20 and session["is_away"]:
        session["saee_rounds"] += 1
        session["is_away"] = False

        if session["saee_rounds"] == 7:
            session["saee_completed"] = True
            return {"status": "completed", "alert": "أتممت 7 أشواط! انتهى السعي.", "rounds": 7}
        elif session["saee_rounds"] == 6:
            return {"status": "tracking", "alert": "تنبيه: أنت في الشوط الأخير!", "rounds": 6}

    elapsed_time = int((datetime.now() - session["saee_start_time"]).total_seconds())
    return {
        "status": "tracking",
        "rounds": session["saee_rounds"],
        "distance_to_start_meters": round(distance, 2),
        "timer_seconds": elapsed_time
    }