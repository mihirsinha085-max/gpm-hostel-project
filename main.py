import os
import json
import time
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd

app = Flask(__name__, static_folder="../frontend")
CORS(app)

DB_FILE = "database.json"

DEFAULT_WORKERS = [
    {"id": "worker_shailee", "password": generate_password_hash("worker123"), "plain_password": "worker123", "name": "Shailee Kumar", "trade": "Electricity & Maintenance"},
    {"id": "worker_ranjeet", "password": generate_password_hash("worker123"), "plain_password": "worker123", "name": "Ranjeet Kumar", "trade": "Electricity"},
    {"id": "worker_amit", "password": generate_password_hash("worker123"), "plain_password": "worker123", "name": "Amit Kumar", "trade": "Electricity & Sanitation"}
]

DEFAULT_ACADEMIC_STAFF = [
    {"id": "suman_kumar", "password": generate_password_hash("suman123"), "plain_password": "suman123", "name": "Prof. Suman Kumar", "role": "Academic Building Incharge"},
    {"id": "aswini_kumar", "password": generate_password_hash("aswini123"), "plain_password": "aswini123", "name": "Prof. Aswini Kumar", "role": "Campus & Estate Incharge"}
]

DEFAULT_DATA = {
    "principal": {
        "id": "principal_office",
        "password": generate_password_hash("principal123"),
        "plain_password": "principal123",
        "name": "Dr. Principal / Patron-in-Chief"
    },
    "admins": [
        {"id": "admin", "password": generate_password_hash("superadmin"), "plain_password": "superadmin", "name": "Admin Office / Cashier Desk"}
    ],
    "workers": DEFAULT_WORKERS,
    "academic_staff": DEFAULT_ACADEMIC_STAFF,
    "wardens": [
        {"id": "warden_aswini", "password": generate_password_hash("admin123"), "plain_password": "admin123", "name": "Prof. Aswini Kumar", "wing": "boys"},
        {"id": "warden_gurudeo", "password": generate_password_hash("admin123"), "plain_password": "admin123", "name": "Prof. Gurudeo Nirala", "wing": "boys"},
        {"id": "warden_manadjee", "password": generate_password_hash("admin123"), "plain_password": "admin123", "name": "Prof. Manadjee Kumar", "wing": "boys"},
        {"id": "warden_ekta", "password": generate_password_hash("admin123"), "plain_password": "admin123", "name": "Prof. Ekta Kumari", "wing": "girls"}
    ],
    "delegated_wardens": [],
    "students": [],
    "leaves": [],
    "grievances": [],
    "campus_grievances": [],
    "official_applications": [],
    "profile_updates": []
}

def load_db():
    if not os.path.exists(DB_FILE):
        save_db(DEFAULT_DATA)
        return DEFAULT_DATA
    try:
        with open(DB_FILE, "r") as f:
            data = json.load(f)

        if "principal" not in data:
            data["principal"] = DEFAULT_DATA["principal"]

        existing_w_ids = {w["id"] for w in data.get("wardens", [])}
        for def_w in DEFAULT_DATA["wardens"]:
            if def_w["id"] not in existing_w_ids:
                data.setdefault("wardens", []).append(def_w)

        existing_a_ids = {a["id"] for a in data.get("admins", [])}
        for def_a in DEFAULT_DATA["admins"]:
            if def_a["id"] not in existing_a_ids:
                data.setdefault("admins", []).append(def_a)

        data["workers"] = DEFAULT_WORKERS
        data["academic_staff"] = DEFAULT_ACADEMIC_STAFF

        data.setdefault("students", [])
        data.setdefault("leaves", [])
        data.setdefault("grievances", [])
        data.setdefault("campus_grievances", [])
        data.setdefault("official_applications", [])
        data.setdefault("profile_updates", [])
        data.setdefault("delegated_wardens", [])
        save_db(data)
        return data
    except Exception as e:
        print("DB Load Error:", e)
        save_db(DEFAULT_DATA)
        return DEFAULT_DATA

def save_db(data):
    try:
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print("DB Save Error:", e)

@app.route("/")
def serve_root():
    return send_from_directory("../frontend", "index.html")

@app.route("/<path:filename>")
def serve_pages(filename):
    return send_from_directory("../frontend", filename)

@app.route("/download-rules")
def download_rules():
    target = "hostel_rules.pdf" if os.path.exists("../frontend/hostel_rules.pdf") else "hostel_rules.pdf.pdf"
    return send_from_directory("../frontend", target, as_attachment=True, download_name="GP_Munger_Hostel_Rules.pdf")

# 1. Student Login
@app.route("/api/auth/student-login", methods=["POST"])
def student_login():
    data = request.json or {}
    login_id = str(data.get("email_or_roll", "")).strip().lower()
    password = str(data.get("password", "")).strip()
    db = load_db()

    student = next((
        s for s in db.get("students", [])
        if str(s.get("email", "")).strip().lower() == login_id or str(s.get("roll", "")).strip().lower() == login_id
    ), None)

    if not student:
        return jsonify({"status": "error", "message": "Invalid Roll Number or Password."}), 401

    stored = student.get("password", "")
    valid = check_password_hash(stored, password) if stored.startswith(("pbkdf2:sha256:", "scrypt:")) else (stored == password or student.get("plain_password") == password)

    if not valid:
        return jsonify({"status": "error", "message": "Invalid Roll Number or Password."}), 401

    safe = dict(student)
    safe.pop("password", None)
    return jsonify({"status": "success", "user": safe})

# 2. Student Admission Registration (BH-01, BH-02, GH-01, GH-02 & G/F/S/T-01 to 28)
@app.route("/api/student/register", methods=["POST"])
def register_new_student():
    data = request.json or {}
    roll = str(data.get("roll", "")).strip()

    if not roll:
        return jsonify({"status": "error", "message": "Roll number is required."}), 400

    db = load_db()
    if any(s.get("roll", "").strip().lower() == roll.lower() for s in db.get("students", [])):
        return jsonify({"status": "error", "message": f"Roll number {roll} is already registered!"}), 400

    name = str(data.get("name", "Student")).strip()
    hostel_code = str(data.get("hostel_code", "BH-01")).strip()
    wing = "girls" if hostel_code.startswith("GH") else "boys"
    email = str(data.get("email", "")).strip().lower()
    if not email:
        email = f"{roll.replace('/', '_').lower()}@gpmunger.ac.in"

    new_student = {
        "roll": roll,
        "name": name,
        "guardian": str(data.get("guardian", "--")).strip(),
        "dob": str(data.get("dob", "--")).strip(),
        "email": email,
        "contact": str(data.get("contact", "--")).strip(),
        "guardian_contact": str(data.get("guardian_contact", "--")).strip(),
        "branch": str(data.get("branch", "CSE")).strip(),
        "hostel_wing": wing,
        "hostel_code": hostel_code,
        "room": str(data.get("room", "G-01")).strip(),
        "bed": str(data.get("bed", "--")).strip(),
        "table_no": str(data.get("table_no", "--")).strip(),
        "district": str(data.get("district", "--")).strip(),
        "address": str(data.get("address", "--")).strip(),
        "password": generate_password_hash("1234"),
        "plain_password": "1234",
        "session": "Odd 2026 Session",
        "submitted_date": time.strftime("%d/%m/%Y"),
        "fee_due": 0,
        "fine_due": 0,
        "status": "Pending",
        "photo_url": data.get("photo_url") or "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=160&q=80",
        "signature_url": f"https://dummyimage.com/200x80/ffffff/000000.png&text={name.replace(' ', '+')}",
        "payment_history": []
    }

    db.setdefault("students", []).append(new_student)
    save_db(db)
    return jsonify({
        "status": "success",
        "message": f"Registration submitted for {name} ({roll}) in {hostel_code} Room {new_student['room']}!"
    })

# 3. Forgot Password via 4 Details
@app.route("/api/auth/verify-and-set-password", methods=["POST"])
def verify_and_set_password():
    data = request.json or {}
    email = str(data.get("email", "")).strip().lower()
    roll = str(data.get("roll", "")).strip().lower()
    parent_contact = str(data.get("parent_contact", "")).strip()
    new_password = str(data.get("new_password", "")).strip()

    if not new_password:
        return jsonify({"status": "error", "message": "New password is required."}), 400

    db = load_db()
    student = next((
        s for s in db.get("students", [])
        if str(s.get("email", "")).strip().lower() == email and str(s.get("roll", "")).strip().lower() == roll
    ), None)

    if not student:
        return jsonify({"status": "error", "message": "Email ID or Roll Number does not match our records."}), 404

    s_p_contact = str(student.get("guardian_contact", "")).strip()
    if parent_contact not in s_p_contact and s_p_contact not in parent_contact:
        return jsonify({"status": "error", "message": "Parent's contact number does not match our records."}), 400

    student["password"] = generate_password_hash(new_password)
    student["plain_password"] = new_password
    save_db(db)
    return jsonify({"status": "success", "message": "Identity verified! Password updated successfully."})

# 4. Direct Reset Password
@app.route("/api/auth/direct-reset-password", methods=["POST"])
def direct_reset_password():
    data = request.json or {}
    email = str(data.get("email", "")).strip().lower()
    current_pwd = str(data.get("current_password", "")).strip()
    new_pwd = str(data.get("new_password", "")).strip()

    if not current_pwd or not new_pwd:
        return jsonify({"status": "error", "message": "All fields are required."}), 400

    db = load_db()
    student = next((s for s in db.get("students", []) if str(s.get("email", "")).strip().lower() == email), None)

    if not student:
        return jsonify({"status": "error", "message": "Registered email not found."}), 404

    stored = student.get("password", "")
    valid = check_password_hash(stored, current_pwd) if stored.startswith(("pbkdf2:sha256:", "scrypt:")) else (stored == current_pwd or student.get("plain_password") == current_pwd)

    if not valid:
        return jsonify({"status": "error", "message": "Incorrect current password."}), 400

    student["password"] = generate_password_hash(new_pwd)
    student["plain_password"] = new_pwd
    save_db(db)
    return jsonify({"status": "success", "message": "Password updated successfully!"})

# 5. Student Self Change Password
@app.route("/api/student/change-password", methods=["POST"])
def student_self_change_pwd():
    data = request.json or {}
    roll = str(data.get("roll", "")).strip().lower()
    old_pwd = str(data.get("old_password", "")).strip()
    new_pwd = str(data.get("new_password", "")).strip()

    db = load_db()
    student = next((s for s in db.get("students", []) if str(s.get("roll", "")).strip().lower() == roll), None)
    if not student:
        return jsonify({"status": "error", "message": "Student record not found."}), 404

    stored = student.get("password", "")
    valid = check_password_hash(stored, old_pwd) if stored.startswith(("pbkdf2:sha256:", "scrypt:")) else (stored == old_pwd or student.get("plain_password") == old_pwd)

    if not valid:
        return jsonify({"status": "error", "message": "Incorrect current password."}), 400

    student["password"] = generate_password_hash(new_pwd)
    student["plain_password"] = new_pwd
    save_db(db)
    return jsonify({"status": "success", "message": "Password changed successfully!"})

# 6. Student Profile Update
@app.route("/api/student/update-profile", methods=["POST"])
def update_student_profile():
    data = request.json or {}
    roll = str(data.get("roll", "")).strip().lower()
    db = load_db()
    student = next((s for s in db.get("students", []) if str(s.get("roll", "")).strip().lower() == roll), None)
    if not student:
        return jsonify({"status": "error", "message": "Student not found"}), 404

    student["contact"] = data.get("contact", student.get("contact"))
    student["guardian_contact"] = data.get("guardian_contact", student.get("guardian_contact"))
    student["status"] = "Pending"
    save_db(db)
    return jsonify({"status": "success", "message": "Profile updated! Status is now Pending Warden approval."})

# 7. Warden Login
@app.route("/api/auth/warden-login", methods=["POST"])
def warden_login():
    data = request.json or {}
    w_id = str(data.get("id", "")).strip()
    pwd = str(data.get("password", "")).strip()
    db = load_db()

    warden = next((w for w in db.get("wardens", []) if w["id"] == w_id), None)
    if warden:
        stored = warden.get("password", "")
        valid = check_password_hash(stored, pwd) if stored.startswith(("pbkdf2:sha256:", "scrypt:")) else (stored == pwd or warden.get("plain_password") == pwd)
        if valid:
            return jsonify({"status": "success", "user": {"id": warden["id"], "name": warden["name"], "wing": warden.get("wing", "boys"), "role": "Hostel Incharge"}})

    return jsonify({"status": "error", "message": "Invalid Warden ID or Password."}), 401

# 8. Admin Office Login
@app.route("/api/auth/admin-login", methods=["POST"])
def admin_login():
    data = request.json or {}
    a_id = str(data.get("id", "")).strip()
    pwd = str(data.get("password", "")).strip()
    db = load_db()
    admin = next((a for a in db.get("admins", []) if a["id"] == a_id), None)
    if admin:
        stored = admin.get("password", "")
        valid = check_password_hash(stored, pwd) if stored.startswith(("pbkdf2:sha256:", "scrypt:")) else (stored == pwd or admin.get("plain_password") == pwd)
        if valid:
            return jsonify({"status": "success", "user": {"id": admin["id"], "name": admin["name"], "role": "Admin Office"}})
    return jsonify({"status": "error", "message": "Invalid Administrative Credentials."}), 401

# 9. Principal Dedicated Login
@app.route("/api/auth/principal-login", methods=["POST"])
def principal_login():
    data = request.json or {}
    p_id = str(data.get("id", "")).strip()
    pwd = str(data.get("password", "")).strip()
    db = load_db()

    principal = db.get("principal", DEFAULT_DATA["principal"])
    if principal.get("id") == p_id:
        stored = principal.get("password", "")
        valid = check_password_hash(stored, pwd) if stored.startswith(("pbkdf2:sha256:", "scrypt:")) else (stored == pwd or principal.get("plain_password") == pwd)
        if valid:
            return jsonify({
                "status": "success",
                "user": {
                    "id": principal["id"],
                    "name": principal.get("name", "Dr. Principal"),
                    "role": "Principal / Patron-in-Chief"
                }
            })
    return jsonify({"status": "error", "message": "Invalid Principal Security ID or Passkey."}), 401

# 10. Worker Login (Shailee, Ranjeet, Amit)
@app.route("/api/auth/worker-login", methods=["POST"])
def worker_login():
    data = request.json or {}
    w_id = str(data.get("id", "")).strip()
    pwd = str(data.get("password", "")).strip()
    db = load_db()

    worker = next((w for w in db.get("workers", []) if w["id"] == w_id), None)
    if worker:
        stored = worker.get("password", "")
        valid = check_password_hash(stored, pwd) if stored.startswith(("pbkdf2:sha256:", "scrypt:")) else (stored == pwd or worker.get("plain_password") == pwd)
        if valid:
            return jsonify({
                "status": "success",
                "user": {
                    "id": worker["id"],
                    "name": worker["name"],
                    "trade": worker.get("trade", "Maintenance")
                }
            })
    return jsonify({"status": "error", "message": "Invalid Worker ID or Password."}), 401

# 10b. Academic & Campus Incharge Login (Suman & Aswini Sir)
@app.route("/api/auth/academic-login", methods=["POST"])
def academic_login():
    data = request.json or {}
    u_id = str(data.get("id", "")).strip()
    pwd = str(data.get("password", "")).strip()
    db = load_db()
    staff = next((s for s in db.get("academic_staff", []) if s["id"] == u_id), None)
    if not staff:
        staff = next((s for s in DEFAULT_ACADEMIC_STAFF if s["id"] == u_id), None)
    if staff:
        stored = staff.get("password", "")
        valid = check_password_hash(stored, pwd) if stored.startswith(("pbkdf2:sha256:", "scrypt:")) else (stored == pwd or staff.get("plain_password") == pwd)
        if valid:
            return jsonify({"status": "success", "user": {"id": staff["id"], "name": staff["name"], "role": staff.get("role", "Incharge")}} )
    return jsonify({"status": "error", "message": "Invalid Academic/Campus Incharge Credentials."}), 401

# 11. Super-Admin (Principal) Complete Data Overview
@app.route("/api/super/dashboard-data", methods=["GET"])
def super_dashboard_data():
    db = load_db()
    students = db.get("students", [])
    leaves = db.get("leaves", [])
    grievances = db.get("grievances", [])
    campus_gr = db.get("campus_grievances", [])
    apps = db.get("official_applications", [])

    return jsonify({
        "status": "success",
        "stats": {
            "total_students": len(students),
            "boys_count": len([s for s in students if s.get("hostel_wing") == "boys"]),
            "girls_count": len([s for s in students if s.get("hostel_wing") == "girls"]),
            "pending_leaves": len([l for l in leaves if l.get("status") == "Pending"]),
            "pending_apps": len([a for a in apps if not a.get("principal_remarks")]),
            "active_grievances": len(grievances) + len(campus_gr)
        },
        "applications": apps,
        "recent_leaves": leaves,
        "recent_grievances": grievances,
        "campus_grievances": campus_gr,
        "students": students,
        "workers": db.get("workers", DEFAULT_WORKERS),
        "academic_staff": db.get("academic_staff", DEFAULT_ACADEMIC_STAFF),
        "wardens": db.get("wardens", DEFAULT_DATA["wardens"])
    })

# 12. Principal Reads/Marks Application as Seen
@app.route("/api/super/mark-app-read", methods=["POST"])
def mark_app_read():
    app_id = (request.json or {}).get("app_id")
    db = load_db()
    for a in db.get("official_applications", []):
        if a.get("app_id") == app_id:
            a["is_read"] = True
            a["read_at"] = time.strftime("%d/%m/%Y %I:%M %p")
            save_db(db)
            return jsonify({"status": "success", "message": "Marked as read by Principal Ma'am!"})
    return jsonify({"status": "error", "message": "Application not found"}), 404

# 13. Principal Action on Digital Applications
@app.route("/api/super/action-application", methods=["POST"])
def action_application():
    data = request.json or {}
    app_id = data.get("app_id")
    action = data.get("action")
    remarks = data.get("remarks", "Order passed by Principal Ma'am.")

    db = load_db()
    for item in db.get("official_applications", []):
        if item.get("app_id") == app_id:
            item["status"] = action
            item["is_read"] = True
            item["read_at"] = item.get("read_at") or time.strftime("%d/%m/%Y %I:%M %p")
            item["principal_remarks"] = remarks
            item["action_taken_by"] = "Dr. Principal / Patron-in-Chief"
            item["action_date"] = time.strftime("%d/%m/%Y %I:%M %p")
            save_db(db)
            return jsonify({"status": "success", "message": f"Application {action} with feedback!"})

    return jsonify({"status": "error", "message": "Application not found"}), 404

# 14. Student Submits Digital Application
@app.route("/api/applications/submit", methods=["POST"])
def submit_digital_application():
    data = request.json or {}
    db = load_db()

    app_id = f"GPM-APP-2026-{len(db.get('official_applications', [])) + 101}"
    record = {
        "app_id": app_id,
        "roll": data.get("roll"),
        "name": data.get("name"),
        "wing": data.get("wing", "boys"),
        "category": data.get("category", "General Request"),
        "subject": data.get("subject"),
        "body": data.get("body"),
        "submitted_at": time.strftime("%d/%m/%Y %I:%M %p"),
        "status": "Pending Principal Review",
        "is_read": False,
        "read_at": None,
        "principal_remarks": "",
        "action_taken_by": "",
        "action_date": ""
    }
    db.setdefault("official_applications", []).insert(0, record)
    save_db(db)
    return jsonify({"status": "success", "message": "Digital Application submitted successfully!", "app_id": app_id})

# 15. Student Fetches Their Own Applications
@app.route("/api/student/my-applications", methods=["GET"])
def get_student_applications():
    roll = request.args.get("roll", "").strip().lower()
    db = load_db()
    my_apps = [a for a in db.get("official_applications", []) if str(a.get("roll", "")).strip().lower() == roll]
    return jsonify({"status": "success", "applications": my_apps})

# 16. Warden Data
@app.route("/api/warden/data", methods=["GET"])
def get_warden_data():
    wing = request.args.get("wing", "boys").strip().lower()
    db = load_db()
    return jsonify({
        "status": "success",
        "wing": wing,
        "students": [s for s in db.get("students", []) if s.get("hostel_wing", "boys").strip().lower() == wing],
        "leaves": [l for l in db.get("leaves", []) if l.get("hostel_wing", "boys").strip().lower() == wing]
    })

# 17. Admin Centralized Data
@app.route("/api/admin/data", methods=["GET"])
def get_admin_data():
    db = load_db()
    students_view = []
    for s in db.get("students", []):
        c = dict(s)
        c.pop("password", None)
        c["current_password"] = s.get("plain_password", "1234")
        students_view.append(c)
    return jsonify({
        "students": students_view,
        "leaves": db.get("leaves", []),
        "grievances": db.get("grievances", []),
        "applications": db.get("official_applications", []),
        "workers": db.get("workers", DEFAULT_WORKERS)
    })

# 18. Admin Assigns Task
@app.route("/api/admin/assign-task", methods=["POST"])
def assign_task():
    data = request.json or {}
    t_id = data.get("ticket_id")
    worker_id = data.get("worker_id")
    custom_name = data.get("worker_name")
    db = load_db()

    worker = next((w for w in db.get("workers", []) if w["id"] == worker_id), None)
    assigned_name = custom_name or (worker["name"] if worker else "Field Staff (Offline)")

    for g in db.get("grievances", []):
        if g.get("ticket_id") == t_id:
            g["status"] = "In Progress"
            g["assigned_worker_id"] = worker_id
            g["assigned_worker_name"] = assigned_name
            g["assigned_at"] = time.strftime("%d/%m/%Y %I:%M %p")
            save_db(db)
            return jsonify({"status": "success", "message": f"Task updated to In Progress: Assigned to {assigned_name}!"})
    return jsonify({"status": "error", "message": "Ticket not found"}), 404

# 19. Admin Directly Resolves Grievance
@app.route("/api/admin/resolve-grievance-direct", methods=["POST"])
def admin_direct_resolve():
    data = request.json or {}
    t_id = data.get("ticket_id")
    remarks = data.get("remarks", "Resolved by Admin Office via Offline Staff.")
    db = load_db()

    for g in db.get("grievances", []):
        if g.get("ticket_id") == t_id:
            g["status"] = "Resolved"
            g["resolved_notes"] = remarks
            g["resolved_at"] = time.strftime("%d/%m/%Y %I:%M %p")
            g["assigned_worker_name"] = g.get("assigned_worker_name") or "Hostel Ground Staff (Called)"
            save_db(db)
            return jsonify({"status": "success", "message": "Grievance marked as Resolved by Admin Office!"})
    return jsonify({"status": "error", "message": "Ticket not found"}), 404

# 20. Admin Updates Disciplinary Fine
@app.route("/api/admin/update-fine", methods=["POST"])
def admin_update_fine():
    data = request.json or {}
    roll = str(data.get("roll", "")).strip()
    fine_amount = float(data.get("fine_amount", 0))
    reason = str(data.get("reason", "Disciplinary Fine")).strip()
    db = load_db()

    for s in db.get("students", []):
        if s.get("roll") == roll:
            s["fine_due"] = fine_amount
            s.setdefault("fine_history", []).append({
                "amount": fine_amount,
                "reason": reason,
                "date": time.strftime("%d/%m/%Y %I:%M %p")
            })
            save_db(db)
            return jsonify({"status": "success", "message": f"Fine updated to ₹{fine_amount} for {s['name']}!"})

    return jsonify({"status": "error", "message": "Student not found"}), 404

# 21. Worker Tasks Fetch
@app.route("/api/worker/my-tasks", methods=["GET"])
def get_worker_tasks():
    w_id = request.args.get("worker_id", "")
    db = load_db()
    all_gr = db.get("grievances", [])
    assigned = [g for g in all_gr if g.get("assigned_worker_id") == w_id]
    return jsonify({
        "status": "success",
        "pending": [g for g in assigned if g.get("status") in ["Assigned", "In Progress", "Reported"]],
        "completed": [g for g in assigned if g.get("status") == "Resolved"]
    })

# 22. Worker Completes Task with Live After-Proof
@app.route("/api/worker/complete-task", methods=["POST"])
def complete_task():
    data = request.json or {}
    t_id = data.get("ticket_id")
    after_proof = data.get("after_proof")
    notes = data.get("work_notes", "Task completed on site.")
    db = load_db()

    for g in db.get("grievances", []):
        if g.get("ticket_id") == t_id:
            g["status"] = "Resolved"
            g["after_proof"] = after_proof
            g["resolved_notes"] = notes
            g["resolved_at"] = time.strftime("%d/%m/%Y %I:%M %p")
            save_db(db)
            return jsonify({"status": "success", "message": "Work resolved with live proof!"})
    return jsonify({"status": "error", "message": "Ticket not found"}), 404

# 23. Student Submits Feedback
@app.route("/api/student/submit-feedback", methods=["POST"])
def submit_feedback():
    data = request.json or {}
    t_id = data.get("ticket_id")
    rating = int(data.get("rating", 5))
    review = str(data.get("review", "")).strip()
    db = load_db()

    for g in db.get("grievances", []):
        if g.get("ticket_id") == t_id:
            g["feedback"] = {
                "rating": rating,
                "review": review,
                "submitted_at": time.strftime("%d/%m/%Y %I:%M %p")
            }
            save_db(db)
            return jsonify({"status": "success", "message": "Feedback submitted successfully!"})
    return jsonify({"status": "error", "message": "Ticket not found"}), 404

# 24. Smart Excel Upload
@app.route("/api/admin/upload-excel", methods=["POST"])
def upload_excel():
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded."}), 400

    file = request.files["file"]
    try:
        df = pd.read_csv(file) if file.filename.endswith(".csv") else pd.read_excel(file)
        df = df.fillna("")
        db = load_db()
        existing_rolls = {str(s.get("roll")).strip() for s in db.get("students", [])}
        added = 0
        col_map = {str(c).strip().lower().replace(" ", "_"): c for c in df.columns}

        def get_val(row, aliases, default=""):
            for a in aliases:
                norm_a = a.lower().replace(" ", "_")
                if norm_a in col_map:
                    val = str(row[col_map[norm_a]]).strip()
                    if val and val != "nan":
                        return val
            return default

        for _, row in df.iterrows():
            roll = get_val(row, ["roll", "roll_no", "rollno", "reg_no", "registration_no"])
            if not roll or roll in existing_rolls:
                continue

            name = get_val(row, ["name", "student_name", "candidate_name", "full_name"], "Student")
            email = get_val(row, ["email", "email_id", "mail"], f"{roll.replace('/', '_').lower()}@gpmunger.ac.in")
            contact = get_val(row, ["contact", "mobile", "phone", "student_mobile"], "--")
            g_contact = get_val(row, ["guardian_contact", "parent_mobile", "father_contact"], "--")
            guardian = get_val(row, ["guardian", "father_name", "parent_name"], "--")
            hostel_code = get_val(row, ["hostel", "hostel_code", "building"], "BH-01").upper()
            room = get_val(row, ["room", "room_no"], "G-01").upper()
            bed = get_val(row, ["bed", "bed_no"], "--")
            table_no = get_val(row, ["table", "table_no"], "--")
            branch = get_val(row, ["branch", "dept", "department"], "CSE")
            wing = "girls" if hostel_code.startswith("GH") else "boys"

            new_student = {
                "roll": roll, "name": name, "email": email,
                "password": generate_password_hash("1234"), "plain_password": "1234",
                "branch": branch, "hostel_wing": wing,
                "hostel_code": hostel_code,
                "room": room, "bed": bed, "table_no": table_no,
                "dob": get_val(row, ["dob", "date_of_birth"], "--"),
                "contact": contact, "guardian": guardian, "guardian_contact": g_contact,
                "district": get_val(row, ["district", "dist"], "--"),
                "address": get_val(row, ["address", "location"], "--"),
                "session": "Odd 2026 Session", "submitted_date": time.strftime("%d/%m/%Y"),
                "fee_due": 0, "fine_due": 0, "status": "Approved",
                "photo_url": "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=160&q=80",
                "signature_url": f"https://dummyimage.com/200x80/ffffff/000000.png&text={name.replace(' ', '+')}",
                "payment_history": []
            }
            db["students"].append(new_student)
            existing_rolls.add(roll)
            added += 1

        save_db(db)
        return jsonify({"status": "success", "message": f"{added} students imported successfully from Excel!"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Excel Error: {str(e)}"}), 500

# 25. Student Management Endpoints (Admin)
@app.route("/api/admin/add-student", methods=["POST"])
def admin_add_student():
    data = request.json or {}
    roll = str(data.get("roll", "")).strip()
    if not roll: return jsonify({"status": "error", "message": "Roll is required"}), 400
    db = load_db()
    if any(s.get("roll", "").lower() == roll.lower() for s in db.get("students", [])):
        return jsonify({"status": "error", "message": "Roll already registered"}), 400

    pwd = str(data.get("password", "1234")).strip()
    hostel_code = str(data.get("hostel_code", "BH-01")).strip()
    wing = "girls" if hostel_code.startswith("GH") else "boys"
    new_s = {
        "roll": roll, "name": data.get("name", "Student"),
        "email": f"{roll.replace('/', '_').lower()}@gpmunger.ac.in",
        "password": generate_password_hash(pwd), "plain_password": pwd,
        "hostel_wing": wing, "hostel_code": hostel_code,
        "room": data.get("room", "G-01"), "bed": data.get("bed", "--"),
        "table_no": data.get("table_no", "--"),
        "contact": data.get("contact", "--"), "status": "Approved",
        "fine_due": 0, "payment_history": []
    }
    db["students"].append(new_s)
    save_db(db)
    return jsonify({"status": "success", "message": "Student added successfully!"})

@app.route("/api/admin/edit-student", methods=["POST"])
def admin_edit_student():
    data = request.json or {}
    roll = str(data.get("roll", "")).strip()
    db = load_db()
    for s in db.get("students", []):
        if s.get("roll") == roll:
            s["name"] = data.get("name", s.get("name"))
            s["hostel_code"] = data.get("hostel_code", s.get("hostel_code"))
            s["room"] = data.get("room", s.get("room"))
            s["bed"] = data.get("bed", s.get("bed"))
            s["table_no"] = data.get("table_no", s.get("table_no"))
            s["contact"] = data.get("contact", s.get("contact"))
            s["status"] = data.get("status", s.get("status"))
            save_db(db)
            return jsonify({"status": "success", "message": "Record updated successfully!"})
    return jsonify({"status": "error", "message": "Student not found"}), 404

@app.route("/api/admin/change-student-password", methods=["POST"])
def admin_change_pwd():
    data = request.json or {}
    roll = str(data.get("roll", "")).strip()
    new_pwd = str(data.get("new_password", "")).strip()
    db = load_db()
    for s in db.get("students", []):
        if s.get("roll") == roll:
            s["password"] = generate_password_hash(new_pwd)
            s["plain_password"] = new_pwd
            save_db(db)
            return jsonify({"status": "success", "message": "Password updated successfully!"})
    return jsonify({"status": "error", "message": "Student not found"}), 404

@app.route("/api/admin/delete-student", methods=["POST"])
def admin_delete_student():
    roll = request.json.get("roll", "")
    db = load_db()
    initial_len = len(db.get("students", []))
    db["students"] = [s for s in db.get("students", []) if s.get("roll") != roll]
    if len(db["students"]) < initial_len:
        save_db(db)
        return jsonify({"status": "success", "message": f"Student {roll} deleted successfully!"})
    return jsonify({"status": "error", "message": "Student not found"}), 404

# 26. Leave Submit & Approve
@app.route("/api/leaves", methods=["POST"])
def add_leave():
    data = request.json or {}
    db = load_db()
    roll = data.get("roll")
    st = next((s for s in db.get("students", []) if s.get("roll") == roll), None)
    wing = st.get("hostel_wing", "boys") if st else "boys"

    l_id = f"GPM-HLA-2026-{len(db.get('leaves', [])) + 1201}"
    record = {
        "leave_id": l_id, "roll": roll, "name": data.get("name"),
        "hostel": data.get("hostel"), "hostel_wing": wing, "room": data.get("room"),
        "reason": data.get("reason"), "departure_date": data.get("departure_date"),
        "return_date": data.get("return_date"), "address": data.get("address"),
        "submitted_at": time.strftime("%d-%m-%Y"), "status": "Pending"
    }
    db.setdefault("leaves", []).insert(0, record)
    save_db(db)
    return jsonify({"status": "success", "leave_id": l_id})

@app.route("/api/warden/approve-leave", methods=["POST"])
def warden_approve():
    l_id = request.json.get("leave_id")
    db = load_db()
    for l in db.get("leaves", []):
        if l.get("leave_id") == l_id:
            l["status"] = "Approved"
            save_db(db)
            return jsonify({"status": "success", "message": "Leave Sanctioned Successfully!"})
    return jsonify({"status": "error"}), 404

@app.route("/api/student/leaves", methods=["GET"])
def fetch_leaves():
    roll = request.args.get("roll")
    db = load_db()
    return jsonify({"status": "success", "leaves": [l for l in db.get("leaves", []) if l.get("roll") == roll]})

# 27. Grievance Submit
@app.route("/api/grievances", methods=["POST"])
def add_grievance():
    data = request.json or {}
    db = load_db()
    roll = data.get("roll")
    st = next((s for s in db.get("students", []) if s.get("roll") == roll), None)
    hostel_code = data.get("hostel") or (st.get("hostel_code") if st else "BH-01")
    wing = "girls" if hostel_code.startswith("GH") else "boys"

    t_id = f"GPM-TKT-{len(db.get('grievances', [])) + 101}"
    rec = {
        "ticket_id": t_id, "roll": roll, "name": data.get("name"),
        "hostel": hostel_code, "room": data.get("room"), "hostel_wing": wing,
        "category": data.get("category"), "description": data.get("description"),
        "timestamp": time.strftime("%d/%m/%Y %H:%M"), "db_level": float(data.get("db_level", 0.0)),
        "photo_base64": data.get("photo_base64"), "audio_base64": data.get("audio_base64"),
        "status": "Reported", "assigned_worker_id": None, "assigned_worker_name": None,
        "after_proof": None, "feedback": None
    }
    db.setdefault("grievances", []).insert(0, rec)
    save_db(db)
    return jsonify({"status": "success", "ticket_id": t_id})

# ==========================================
# 28. ACADEMIC & CAMPUS INCHARGE ENDPOINTS (With Student Roll & Name)
# ==========================================
@app.route("/api/campus/grievances", methods=["POST"])
def add_campus_grievance():
    data = request.json or {}
    db = load_db()
    t_id = f"GPM-CAMPUS-{len(db.get('campus_grievances', [])) + 101}"
    rec = {
        "ticket_id": t_id,
        "category_type": data.get("category_type", "Academic"),
        "location": data.get("location"),
        "issue": data.get("issue"),
        "description": data.get("description"),
        "roll": data.get("roll", "Anonymous"),
        "name": data.get("name", "Student / Resident"),
        "timestamp": time.strftime("%d/%m/%Y %H:%M"),
        "db_level": float(data.get("db_level", 0.0)),
        "photo_base64": data.get("photo_base64"),
        "audio_base64": data.get("audio_base64"),
        "status": "Reported",
        "assigned_to": data.get("assigned_to", "Prof. Suman Kumar"),
        "after_proof": None,
        "resolved_notes": None
    }
    db.setdefault("campus_grievances", []).insert(0, rec)
    save_db(db)
    return jsonify({"status": "success", "ticket_id": t_id})

@app.route("/api/campus/grievances", methods=["GET"])
def get_campus_grievances():
    db = load_db()
    return jsonify({"status": "success", "grievances": db.get("campus_grievances", [])})

@app.route("/api/campus/resolve-grievance", methods=["POST"])
def resolve_campus_grievance():
    data = request.json or {}
    t_id = data.get("ticket_id")
    notes = data.get("resolved_notes", "Resolved by Incharge.")
    db = load_db()
    for g in db.get("campus_grievances", []):
        if g.get("ticket_id") == t_id:
            g["status"] = "Resolved"
            g["resolved_notes"] = notes
            g["resolved_at"] = time.strftime("%d/%m/%Y %I:%M %p")
            save_db(db)
            return jsonify({"status": "success", "message": "Grievance marked as Resolved!"})
    return jsonify({"status": "error", "message": "Ticket not found"}), 404

if __name__ == "__main__":
    app.run(debug=True, port=5000)