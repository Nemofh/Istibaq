#!/usr/bin/env python3
"""
ISTIBAQ - إدارة الأصول الجامعية الكاملة
SQLite3 DB-API 2.0 Backend
"""
import sqlite3
import json
from datetime import datetime
from typing import Optional
import random


DB_PATH = "istibaq.db" # db name/path



def analyze_temperature(temp):
    if temp >= 45:
        return "حرجة"
    elif temp >= 38:
        return "تحذير"
    return "طبيعي"

def simulate_sensor_readings():
    with get_connection() as conn:
        assets = conn.execute("SELECT serial_number, name FROM assets").fetchall()

    readings = []

    for i, a in enumerate(assets):
        # نخلي أول عناصر مرتفعة عشان العرض
        if i == 0:
            temp = 49
        elif i == 1:
            temp = 44
        elif i == 2:
            temp = 39
        else:
            temp = random.randint(26, 34)

        readings.append({
            "serial_number": a["serial_number"],
            "name": a["name"],
            "temperature": temp,
            "status": analyze_temperature(temp)
        })

    return readings


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # dict-like rows
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
# ─────────────────────────────────────────────

def init_db():
    """Create tables if they don't exist and seed demo data."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS assets (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT NOT NULL,
                serial_number   TEXT NOT NULL UNIQUE,
                location        TEXT NOT NULL,
                building        TEXT NOT NULL,
                floor           TEXT NOT NULL,
                status          TEXT NOT NULL CHECK(status IN ('يعمل','تحذير','حرجة','معطل')),
                next_maintenance TEXT,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS maintenance_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_id    INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
                performed_at TEXT NOT NULL,
                description TEXT,
                technician  TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS notifications (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_id    INTEGER REFERENCES assets(id) ON DELETE SET NULL,
                message     TEXT NOT NULL,
                severity    TEXT NOT NULL CHECK(severity IN ('info','warning','critical')),
                is_read     INTEGER DEFAULT 0,
                created_at  TEXT DEFAULT (datetime('now'))
            );
             CREATE TABLE IF NOT EXISTS sensor_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                serial_number TEXT NOT NULL,
                temperature REAL NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('طبيعي','تحذير','حرجة')),
                created_at TEXT DEFAULT (datetime('now'))
                
            );
             CREATE TABLE IF NOT EXISTS maintenance_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_no TEXT NOT NULL UNIQUE,
                asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
                problem TEXT NOT NULL,
                category TEXT NOT NULL,
                confidence TEXT,
                reasoning TEXT,
                team TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
                           

        """)
        

        # Will display demo data only if empty
        count = conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0] # Check if assets table is empty
        if count == 0:
            demo_assets = [
                ("وحدة تكييف المبنى 4-طابق 2",  "202330001", "مباني أ - طابق 3،",  "مباني أ", "طابق 3", "يعمل",  "2024/01/15"),
                ("مصعد المبنى 4-طابق 2",          "202330002", "مباني أ - طابق 3،",  "مباني أ", "طابق 3", "تحذير", "2024/01/20"),
                ("مولد المبنى 3",                  "202330003", "مباني أ - طابق 3،",  "مباني أ", "طابق 3", "تحذير", "2024/01/20"),
                ("وحدة تكييف HVAC-07",             "HVAC7",     "مباني أ - طابق 3،",  "مباني أ", "طابق 3", "حرجة",  "2024/01/20"),
            ]
            conn.executemany(
                "INSERT INTO assets (name, serial_number, location, building, floor, status, next_maintenance) VALUES (?,?,?,?,?,?,?)",
                demo_assets
            )

def get_all_assets() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM assets ORDER BY id").fetchall()
        return [dict(r) for r in rows]


def get_asset(asset_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM assets WHERE id=?", (asset_id,)).fetchone()
        return dict(row) if row else None


def add_asset(name: str, serial_number: str, location: str,
              building: str, floor: str, status: str,
              next_maintenance: Optional[str] = None) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO assets (name, serial_number, location, building, floor, status, next_maintenance)
               VALUES (?,?,?,?,?,?,?)""",
            (name, serial_number, location, building, floor, status, next_maintenance)
        )
        return cur.lastrowid


def update_asset(asset_id: int, **fields) -> bool:
    allowed = {"name","serial_number","location","building","floor","status","next_maintenance"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    updates["updated_at"] = datetime.now().isoformat(sep=" ", timespec="seconds")
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [asset_id]
    with get_connection() as conn:
        conn.execute(f"UPDATE assets SET {set_clause} WHERE id=?", values)
    return True


def delete_asset(asset_id: int) -> bool:
    with get_connection() as conn:
        conn.execute("DELETE FROM assets WHERE id=?", (asset_id,))
    return True


# ─────────────────────────────────────────────
# MAINTENANCE LOG
# ─────────────────────────────────────────────

def log_maintenance(asset_id: int, description: str,
                    technician: str = "", performed_at: Optional[str] = None) -> int:
    performed_at = performed_at or datetime.now().strftime("%Y/%m/%d")
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO maintenance_log (asset_id, performed_at, description, technician) VALUES (?,?,?,?)",
            (asset_id, performed_at, description, technician)
        )
        return cur.lastrowid


def get_maintenance_log(asset_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM maintenance_log WHERE asset_id=? ORDER BY performed_at DESC",
            (asset_id,)
        ).fetchall()
        return [dict(r) for r in rows]


# ─────────────────────────────────────────────
# NOTIFICATIONS
# ─────────────────────────────────────────────

def add_notification(message: str, severity: str = "info",
                     asset_id: Optional[int] = None) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO notifications (asset_id, message, severity) VALUES (?,?,?)",
            (asset_id, message, severity)
        )
        return cur.lastrowid


def get_unread_notifications():
    with get_connection() as conn:
        # هنا نجلب التنبيهات، ويمكنك مستقبلاً جعلها ديناميكية بناءً على حالة الأصول
        rows = conn.execute("SELECT * FROM notifications ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def mark_notifications_read():
    with get_connection() as conn:
        conn.execute("UPDATE notifications SET is_read=1 WHERE is_read=0")


def get_dashboard_stats() -> dict:
    with get_connection() as conn:
        total       = conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
        working     = conn.execute("SELECT COUNT(*) FROM assets WHERE status='يعمل'").fetchone()[0]
        warning     = conn.execute("SELECT COUNT(*) FROM assets WHERE status='تحذير'").fetchone()[0]
        critical    = conn.execute("SELECT COUNT(*) FROM assets WHERE status='حرجة'").fetchone()[0]
        unread_notif = conn.execute("SELECT COUNT(*) FROM notifications WHERE is_read=0").fetchone()[0]
    return {
        "total": total,
        "working": working,
        "warning": warning,
        "critical": critical,
        "unread_notifications": unread_notif,
    }


# ─────────────────────────────────────────────
# SEARCH
# ─────────────────────────────────────────────

def search_assets(query: str) -> list[dict]:
    q = f"%{query}%"
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT * FROM assets
               WHERE name LIKE ? OR serial_number LIKE ?
                  OR location LIKE ? OR status LIKE ?
               ORDER BY id""",
            (q, q, q, q)
        ).fetchall()
        return [dict(r) for r in rows]
    
    import random

def get_home_assets() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT
                id,
                name,
                serial_number,
                location,
                status,
                next_maintenance
            FROM assets
            ORDER BY id
        """).fetchall()

        assets = []
        for r in rows:
            asset = dict(r)

            name_lower = (asset["name"] or "").lower()
            if "مكيف" in name_lower or "تكييف" in name_lower or "hvac" in name_lower:
                asset_type = "hvac"
            elif "مصعد" in name_lower or "مضخة" in name_lower:
                asset_type = "mechanical"
            elif "مولد" in name_lower or "كهرب" in name_lower or "لوحة" in name_lower:
                asset_type = "electrical"
            elif "شبكة" in name_lower or "حاسب" in name_lower or "نظام" in name_lower:
                asset_type = "it"
            else:
                asset_type = "periodic"

            assets.append({
                "id": asset["id"],
                "name": asset["name"],
                "serial": asset["serial_number"],
                "location": asset["location"],
                "status": asset["status"],
                "last_maintenance": "غير متوفر",
                "next_maintenance": asset["next_maintenance"] or "غير محدد",
                "type": asset_type
            })

        return assets


def search_home_assets(query: str) -> list[dict]:
    q = f"%{query}%"
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT
                id,
                name,
                serial_number,
                location,
                status,
                next_maintenance
            FROM assets
            WHERE name LIKE ?
               OR serial_number LIKE ?
               OR location LIKE ?
            ORDER BY id
            LIMIT 4
        """, (q, q, q)).fetchall()

        results = []
        for r in rows:
            asset = dict(r)
            name_lower = (asset["name"] or "").lower()

            if "مكيف" in name_lower or "تكييف" in name_lower or "hvac" in name_lower:
                asset_type = "hvac"
            elif "مصعد" in name_lower or "مضخة" in name_lower:
                asset_type = "mechanical"
            elif "مولد" in name_lower or "كهرب" in name_lower or "لوحة" in name_lower:
                asset_type = "electrical"
            elif "شبكة" in name_lower or "حاسب" in name_lower or "نظام" in name_lower:
                asset_type = "it"
            else:
                asset_type = "periodic"

            results.append({
                "id": asset["id"],
                "name": asset["name"],
                "serial": asset["serial_number"],
                "location": asset["location"],
                "status": asset["status"],
                "last_maintenance": "غير متوفر",
                "next_maintenance": asset["next_maintenance"] or "غير محدد",
                "type": asset_type
            })

        return results


def classify_maintenance_request(asset_name: str, asset_type: str, problem: str) -> dict:
    p = (problem or "").lower()
    a = (asset_name or "").lower()
    t = (asset_type or "").lower()

    category = "periodic"
    confidence = "65%"
    reasoning = "تم التصنيف كصيانة دورية افتراضياً"

    if "كهرب" in p or "تيار" in p or "لوح" in p:
        category = "electrical"
        confidence = "82%"
        reasoning = "المشكلة تتعلق بالكهرباء أو اللوحات"
    elif "تبريد" in p or "تكييف" in p or "برود" in p or t == "hvac" or "مكيف" in a:
        category = "hvac"
        confidence = "88%"
        reasoning = "الأصل أو المشكلة مرتبطة بأنظمة التكييف والتبريد"
    elif "مصعد" in p or "مضخة" in p or t == "mechanical":
        category = "mechanical"
        confidence = "80%"
        reasoning = "المشكلة ضمن نطاق الأنظمة الميكانيكية"
    elif "شبكة" in p or "حاسب" in p or "سيرفر" in p or t == "it":
        category = "it"
        confidence = "79%"
        reasoning = "المشكلة ضمن نطاق تقنية المعلومات"
    elif "تسرب" in p or "تشققات" in p or "جدار" in p:
        category = "civil"
        confidence = "77%"
        reasoning = "المشكلة ضمن الأعمال المدنية"
    elif "فحص" in p or "دوري" in p or "فلتر" in p:
        category = "periodic"
        confidence = "75%"
        reasoning = "الوصف يشير إلى صيانة دورية"

    teams = {
        "hvac": "فريق أنظمة التكييف والتبريد",
        "electrical": "فريق الكهرباء والإلكترونيات",
        "periodic": "فريق الصيانة الدورية العامة",
        "mechanical": "فريق الميكانيكا والمعدات",
        "civil": "فريق الأعمال المدنية والبنية",
        "it": "فريق تقنية المعلومات والشبكات",
    }

    return {
        "category": category,
        "confidence": confidence,
        "reasoning": reasoning,
        "team": teams.get(category, "فريق الصيانة العامة")
    }


def create_maintenance_request(asset_id: int, problem: str, category: str,
                               confidence: str = "", reasoning: str = "", team: str = "") -> dict:
    ticket_no = f"TKT-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO maintenance_requests
            (ticket_no, asset_id, problem, category, confidence, reasoning, team)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (ticket_no, asset_id, problem, category, confidence, reasoning, team))

        conn.execute("""
            INSERT INTO notifications (asset_id, message, severity)
            VALUES (?, ?, ?)
        """, (
            asset_id,
            f"تم إنشاء طلب صيانة جديد رقم {ticket_no}",
            "warning" if category != "periodic" else "info"
        ))

        request_id = cur.lastrowid

    return {
        "id": request_id,
        "ticket_no": ticket_no
    }


def get_recent_maintenance_requests(limit: int = 6) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT
                mr.id,
                mr.ticket_no,
                mr.problem,
                mr.category,
                mr.confidence,
                mr.reasoning,
                mr.team,
                mr.created_at,
                a.name AS asset_name,
                a.serial_number
            FROM maintenance_requests mr
            JOIN assets a ON a.id = mr.asset_id
            ORDER BY mr.id DESC
            LIMIT ?
        """, (limit,)).fetchall()

        return [dict(r) for r in rows]








def analyze_temperature(temp: float) -> str:
    if temp >= 45:
        return "حرجة"
    elif temp >= 38:
        return "تحذير"
    return "طبيعي"


def insert_sensor_reading(serial_number: str, temperature: float) -> int:
    status = analyze_temperature(temperature)

    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO sensor_readings (serial_number, temperature, status)
            VALUES (?, ?, ?)
            """,
            (serial_number, temperature, status)
        )
        return cur.lastrowid


def get_sensor_readings() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT sr.id, sr.serial_number, sr.temperature, sr.status, sr.created_at,
                   a.name, a.location
            FROM sensor_readings sr
            LEFT JOIN assets a ON a.serial_number = sr.serial_number
            ORDER BY
                CASE sr.status
                    WHEN 'حرجة' THEN 1
                    WHEN 'تحذير' THEN 2
                    WHEN 'طبيعي' THEN 3
                    ELSE 4
                END,
                sr.created_at DESC,
                sr.id DESC
        """).fetchall()
        return [dict(r) for r in rows]

def clear_sensor_readings():
    with get_connection() as conn:
        conn.execute("DELETE FROM sensor_readings")


def simulate_sensor_readings() -> list[dict]:
    with get_connection() as conn:
        assets = conn.execute("""
            SELECT serial_number, name
            FROM assets
            ORDER BY id
        """).fetchall()

    clear_sensor_readings()

    simulated = []
    for i, asset in enumerate(assets):
        # نخلي أول الأصول أعلى حرارة للعرض
        if i == 0:
            temp = 49.0
        elif i == 1:
            temp = 44.0
        elif i == 2:
            temp = 39.0
        else:
            temp = round(random.uniform(26, 34), 1)

        insert_sensor_reading(asset["serial_number"], temp)
        simulated.append({
            "serial_number": asset["serial_number"],
            "name": asset["name"],
            "temperature": temp,
            "status": analyze_temperature(temp)
        })

    return get_sensor_readings()
#1111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111
from datetime import datetime

def predict_asset_status(name: str = "", next_maintenance: Optional[str] = None,
                         current_status: Optional[str] = None) -> dict:
    """
    AI-like simple prediction for asset status.
    يعتمد على تاريخ الصيانة + نوع الأصل + الحالة الحالية إن وجدت.
    """
    score = 0
    reasons = []

    # 1) تحليل تاريخ الصيانة
    if next_maintenance:
        try:
            maint_date = datetime.strptime(next_maintenance, "%Y-%m-%d")
            today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
            diff_days = (maint_date - today).days

            if diff_days < 0:
                score += 4
                reasons.append("تاريخ الصيانة متأخر")
            elif diff_days == 0:
                score += 3
                reasons.append("الصيانة اليوم")
            elif diff_days <= 7:
                score += 2
                reasons.append("الصيانة خلال أسبوع")
            else:
                reasons.append("موعد الصيانة غير قريب")
        except Exception:
            score += 1
            reasons.append("تعذر قراءة تاريخ الصيانة")
    else:
        score += 2
        reasons.append("لا يوجد تاريخ صيانة")

    # 2) تحليل اسم الأصل
    name_lower = (name or "").strip().lower()
    risky_keywords = ["مصعد", "مولد", "generator", "elevator", "hvac", "مكيف", "تكييف"]

    if any(k in name_lower for k in risky_keywords):
        score += 1
        reasons.append("نوع الأصل يحتاج متابعة أعلى")

    # 3) الاستفادة من الحالة الحالية إذا أدخلها المستخدم
    if current_status == "معطل":
        score += 4
        reasons.append("تم تحديد الأصل كمعطل")
    elif current_status == "حرجة":
        score += 3
        reasons.append("الحالة الحالية حرجة")
    elif current_status == "تحذير":
        score += 2
        reasons.append("الحالة الحالية تحذير")

    # القرار النهائي
    if score >= 5:
        predicted = "حرجة"
    elif score >= 2:
        predicted = "تحذير"
    else:
        predicted = "يعمل"

    return {
        "predicted_status": predicted,
        "score": score,
        "reason": "، ".join(reasons)
    }

def export_assets_json() -> str:
    return json.dumps(get_all_assets(), ensure_ascii=False, indent=2)


def export_stats_json() -> str:
    return json.dumps(get_dashboard_stats(), ensure_ascii=False, indent=2)



if __name__ == "__main__":
    init_db()
    print("=== ISTIBAQ DB initialised ===\n")

    print("Dashboard Stats: ")
    print(json.dumps(get_dashboard_stats(), ensure_ascii=False, indent=2))

    print("\n All Assets:")
    for a in get_all_assets():
        print(f"  [{a['id']}] {a['name']}  |  {a['serial_number']}  |  {a['status']}  |  صيانة: {a['next_maintenance']}")

    print("\nSearch 'تكييف':")
    for a in search_assets("تكييف"):
        print(f"  ✓ {a['name']}")

    # Add maintenance log entry
    log_maintenance(1, "تم فحص الفلاتر وتنظيفها", technician="أحمد العمري")
    print("\n Maintenance log for asset #1:")
    for m in get_maintenance_log(1):
        print(f"  {m['performed_at']} — {m['description']} ({m['technician']})")

    # Notification
    add_notification("وحدة HVAC-07 تحتاج صيانة عاجلة", severity="critical", asset_id=4)
    print("\n Unread Notifications:")
    for n in get_unread_notifications():
        print(f"  [{n['severity'].upper()}] {n['message']}")

    print("\n All DB-API 2.0 functions operational.")
