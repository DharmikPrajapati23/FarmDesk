import os
import time
from datetime import datetime, timedelta

from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from dotenv import load_dotenv

from pymongo import MongoClient
from bson.objectid import ObjectId

import bcrypt
import jwt  # PyJWT

from functools import wraps

load_dotenv()

app = Flask(__name__)

# CORS: allow Vite dev origin and credentials
CORS(
    app,
    resources={r"/*": {"origins": ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "http://127.0.0.1:3000"]}},
    supports_credentials=True,
)

# MongoDB
MONGO_URL = os.getenv("DATABASE_URL")
client = MongoClient(MONGO_URL)
db = client["FarmDesk"]
companies = db.companies       # company documents with embedded employees
crops = db.crops       # unchanged shape: one doc per company_id with crop_details array

# JWT secret
JWT_SECRET = os.getenv("JWT_SECRET", "dev_secret_change_me")
JWT_ALG = "HS256"

# Cookie config via env
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"  # True for HTTPS
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "Lax")                  # Lax/Strict/None
COOKIE_NAME = os.getenv("COOKIE_NAME", "auth_token")
COOKIE_PATH = "/"

# ---------- Utilities ----------
def hash_password(plain: str) -> bytes:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt())

def check_password(plain: str, hashed: bytes) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed)
    except Exception:
        return False

def normalize_role(r):
    if not r:
        return "Admin"
    v = str(r).lower()
    if v in ["company_admin", "admin", "superadmin"]:
        return "Admin"
    if v in ["officer", "company_officer"]:
        return "Officer"
    return "Officer"

def jwt_issue_for_employee(company_id: str, emp: dict, ttl_hours=8):
    now = int(time.time())
    payload = {
        "sub": str(emp.get("_id")),                  # employee id inside company doc
        "role": normalize_role(emp.get("role")),     # Admin or Officer
        "company_id": company_id,
        "username": emp.get("username"),
        "iat": now,
        "exp": now + 60 * 60 * ttl_hours,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def jwt_verify(token: str):
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])

def get_token_from_request():
    # Prefer HttpOnly cookie
    token = request.cookies.get(COOKIE_NAME)
    if token:
        return token
    # Fallback: Authorization Bearer
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth.split(" ", 1)[1].strip()
    return None

def current_user():
    token = get_token_from_request()
    if not token:
        return None, "Missing token"
    try:
        payload = jwt_verify(token)
        company_id = payload.get("company_id")
        emp_id = payload.get("sub")
        username = payload.get("username")
        if not company_id or not emp_id:
            return None, "Invalid token"

        comp = companies.find_one({"company_id": company_id}, {"employees.password_hash": 0})
        if not comp:
            return None, "User not found"

        emp = None
        for e in comp.get("employees", []):
            if str(e.get("_id")) == str(emp_id) or (username and e.get("username") == username):
                emp = e
                break

        if not emp:
            return None, "User not found"

        # Minimal user view for downstream handlers
        view = {
            "_id": str(emp.get("_id")),
            "username": emp.get("username"),
            "role": normalize_role(emp.get("role")),
            "company_id": comp.get("company_id"),
        }
        return view, None
    except Exception:
        return None, "Invalid or expired token"

def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user, err = current_user()
        if err:
            return jsonify({"error": "Unauthorized"}), 401
        request.user = user
        return fn(*args, **kwargs)
    return wrapper

def require_role(*roles):
    roles_norm = set(normalize_role(r) for r in roles)
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user, err = current_user()
            if err:
                return jsonify({"error": "Unauthorized"}), 401
            if normalize_role(user.get("role")) not in roles_norm:
                return jsonify({"error": "Forbidden"}), 403
            request.user = user
            return fn(*args, **kwargs)
        return wrapper
    return deco

def set_auth_cookie(resp, token, hours=8):
    expires = datetime.utcnow() + timedelta(hours=hours)
    resp.set_cookie(
        COOKIE_NAME,
        token,
        httponly=False,  # Allow JavaScript access for debugging
        secure=COOKIE_SECURE,
        samesite="None" if COOKIE_SECURE else "Lax",  # None for cross-origin
        expires=expires,
        path=COOKIE_PATH,
    )
    return resp

def clear_auth_cookie(resp):
    resp.set_cookie(COOKIE_NAME, "", expires=0, path=COOKIE_PATH, samesite=COOKIE_SAMESITE, secure=COOKIE_SECURE)
    return resp

# ---------- Auth helpers ----------
def _find_employee_for_login(company_id, username, want_role=None):
    comp = companies.find_one({"company_id": company_id})
    if not comp:
        return None, None
    for e in comp.get("employees", []):
        if e.get("username") == username:
            if want_role and normalize_role(e.get("role")) != want_role:
                continue
            return comp, e
    return comp, None

# ---------- Super Admin: create company admin ----------
@app.route('/superadmin/create_admin', methods=['POST'])
def create_company_admin():
    data = request.json or {}
    username = (data.get('username') or "").strip()
    password = data.get('password')
    company_id = (data.get('company_id') or "").strip()

    if not username or not password or not company_id:
        return jsonify({"error": "Missing required fields"}), 400

    hashed_pw = hash_password(password)

    comp = companies.find_one({"company_id": company_id})
    if not comp:
        emp = {
            "_id": str(ObjectId()),
            "username": username,
            "password_hash": hashed_pw,
            "role": "Admin",
        }
        companies.insert_one({"company_id": company_id, "employees": [emp]})
        return jsonify({"message": "Company admin created successfully", "id": emp["_id"]}), 201

    # company exists -> check username uniqueness
    for e in comp.get("employees", []):
        if e.get("username") == username:
            return jsonify({"error": "Username already exists in this company"}), 409

    emp = {
        "_id": str(ObjectId()),
        "username": username,
        "password_hash": hashed_pw,
        "role": "Admin",
    }
    companies.update_one({"company_id": company_id}, {"$push": {"employees": emp}})
    return jsonify({"message": "Company admin created successfully", "id": emp["_id"]}), 201

# ---------- Auth: me, login, logout ----------
@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    user, err = current_user()
    if err:
        return jsonify({"error": err}), 401
    return jsonify(user), 200

@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    resp = make_response(jsonify({"message": "Logged out"}))
    return clear_auth_cookie(resp), 200

@app.route("/admin/login", methods=["POST"])
def admin_login():
    data = request.json or {}
    company_id = (data.get("company_id") or "").strip()
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not company_id or not username or not password:
        return jsonify({"error": "Missing required fields"}), 400 

    comp, emp = _find_employee_for_login(company_id, username, want_role="Admin")
    if comp is None:
        return jsonify({"error": "User Not Found"}), 401
    if emp is None:
        return jsonify({"error": "Unauthorized role"}), 403

    if not check_password(password, emp.get("password_hash", b"")):
        return jsonify({"error": "Please Enter Correct Password"}), 401

    token = jwt_issue_for_employee(company_id, emp, ttl_hours=8)
    resp = make_response(jsonify({"message": "Login successful"}))
    set_auth_cookie(resp, token, hours=8)
    return resp, 200

@app.route("/officer/login", methods=["POST"])
def officer_login():
    data = request.json or {}
    company_id = (data.get("company_id") or "").strip()
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not company_id or not username or not password:
        return jsonify({"error": "Missing required fields"}), 400

    comp, emp = _find_employee_for_login(company_id, username, want_role="Officer")
    if comp is None or emp is None:
        return jsonify({"error": "User Not Found"}), 401

    if not check_password(password, emp.get("password_hash", b"")):
        return jsonify({"error": "Please Enter Correct Password"}), 401

    token = jwt_issue_for_employee(company_id, emp, ttl_hours=8)
    resp = make_response(jsonify({"message": "Login successful"}))
    set_auth_cookie(resp, token, hours=8)
    return resp, 200

# ---------- Admin: Officers management (embedded) ----------
@app.route("/admin/officers", methods=["GET"])
@require_role("Admin")
def list_officers():
    company_id = request.user.get("company_id")
    comp = companies.find_one({"company_id": company_id}, {"employees.password_hash": 0})
    items = []
    if comp:
        for e in comp.get("employees", []):
            if normalize_role(e.get("role")) == "Officer":
                items.append({
                    "_id": str(e.get("_id")),
                    "username": e.get("username"),
                    "role": "Officer",
                    "company_id": company_id
                })
    return jsonify({"items": items}), 200

@app.route("/admin/officers", methods=["POST"])
@require_role("Admin")
def create_officer():
    company_id = request.user.get("company_id")
    data = request.json or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    comp = companies.find_one({"company_id": company_id})
    if not comp:
        return jsonify({"error": "Company not found"}), 404

    for e in comp.get("employees", []):
        if e.get("username") == username:
            return jsonify({"error": "Username already exists"}), 409

    emp = {
        "_id": str(ObjectId()),
        "username": username,
        "password_hash": hash_password(password),
        "role": "Officer",
    }
    companies.update_one({"company_id": company_id}, {"$push": {"employees": emp}})
    return jsonify({"message": "Officer created", "id": emp["_id"]}), 201

@app.route("/admin/officers/<officer_id>", methods=["DELETE"])
@require_role("Admin")
def delete_officer(officer_id):
    company_id = request.user.get("company_id")

    comp = companies.find_one({"company_id": company_id})
    if not comp:
        return jsonify({"error": "Company not found"}), 404

    exists = False
    for e in comp.get("employees", []):
        if str(e.get("_id")) == str(officer_id) and normalize_role(e.get("role")) == "Officer":
            exists = True
            break
    if not exists:
        return jsonify({"error": "Officer not found"}), 404

    companies.update_one(
        {"company_id": company_id},
        {"$pull": {"employees": {"_id": officer_id}}}
    )
    return jsonify({"message": "Officer deleted"}), 200

# ---------- Admin: Crops management (unchanged storage) ----------
@app.route("/admin/crops", methods=["GET"])
@require_role("Admin")
def list_crops():
    user = request.user
    company_id = user.get("company_id")

    # Find or create crops document for this company
    crop_doc = crops.find_one({"company_id": company_id})
    if not crop_doc:
        crop_doc = {
            "company_id": company_id,
            "crop_details": []
        }
        crops.insert_one(crop_doc)

    return jsonify({"crop_details": crop_doc.get("crop_details", [])}), 200

@app.route("/admin/crops", methods=["POST"])
@require_role("Admin")
def add_crop():
    user = request.user
    company_id = user.get("company_id")
    data = request.json or {}

    crop_name = (data.get("crop_name") or "").strip()
    rate_per_unit = data.get("rate_per_unit")

    if not crop_name or rate_per_unit is None:
        return jsonify({"error": "Crop name and rate per unit are required"}), 400

    try:
        rate_per_unit = float(rate_per_unit)
        if rate_per_unit < 0:
            return jsonify({"error": "Rate per unit must be positive"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid rate per unit"}), 400

    crop_doc = crops.find_one({"company_id": company_id})
    if crop_doc:
        existing = crop_doc.get("crop_details", [])
        if any(c["crop_name"].lower() == crop_name.lower() for c in existing):
            return jsonify({"error": "Crop already exists"}), 409

    new_crop = {
        "crop_name": crop_name,
        "rate_per_unit": rate_per_unit,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "created_by": user.get("username"),
        "updated_by": user.get("username")
    }

    if crop_doc:
        crops.update_one(
            {"company_id": company_id},
            {"$push": {"crop_details": new_crop}}
        )
    else:
        crops.insert_one({
            "company_id": company_id,
            "crop_details": [new_crop]
        })

    return jsonify({"message": "Crop added successfully", "crop": new_crop}), 201

@app.route("/admin/crops/<crop_name>", methods=["PUT"])
@require_role("Admin")
def update_crop(crop_name):
    user = request.user
    company_id = user.get("company_id")
    data = request.json or {}

    new_crop_name = (data.get("crop_name") or "").strip()
    rate_per_unit = data.get("rate_per_unit")

    if not new_crop_name or rate_per_unit is None:
        return jsonify({"error": "Crop name and rate per unit are required"}), 400

    try:
        rate_per_unit = float(rate_per_unit)
        if rate_per_unit < 0:
            return jsonify({"error": "Rate per unit must be positive"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid rate per unit"}), 400

    crop_doc = crops.find_one({"company_id": company_id})
    if not crop_doc:
        return jsonify({"error": "No crops found for this company"}), 404

    crop_details = crop_doc.get("crop_details", [])
    crop_index = None

    for i, crop in enumerate(crop_details):
        if crop["crop_name"] == crop_name:
            crop_index = i
            break

    if crop_index is None:
        return jsonify({"error": "Crop not found"}), 404

    for i, crop in enumerate(crop_details):
        if i != crop_index and crop["crop_name"].lower() == new_crop_name.lower():
            return jsonify({"error": "Crop name already exists"}), 409

    crop_details[crop_index] = {
        "crop_name": new_crop_name,
        "rate_per_unit": rate_per_unit,
        "created_at": crop_details[crop_index]["created_at"],
        "updated_at": datetime.utcnow(),
        "created_by": crop_details[crop_index]["created_by"],
        "updated_by": user.get("username")
    }

    crops.update_one(
        {"company_id": company_id},
        {"$set": {"crop_details": crop_details}}
    )

    return jsonify({"message": "Crop updated successfully", "crop": crop_details[crop_index]}), 200

@app.route("/admin/crops/<crop_name>", methods=["DELETE"])
@require_role("Admin")
def delete_crop(crop_name):
    user = request.user
    company_id = user.get("company_id")

    crop_doc = crops.find_one({"company_id": company_id})
    if not crop_doc:
        return jsonify({"error": "No crops found for this company"}), 404

    crop_details = crop_doc.get("crop_details", [])
    updated_crops = [crop for crop in crop_details if crop["crop_name"] != crop_name]

    if len(updated_crops) == len(crop_details):
        return jsonify({"error": "Crop not found"}), 404

    crops.update_one(
        {"company_id": company_id},
        {"$set": {"crop_details": updated_crops}}
    )

    return jsonify({"message": "Crop deleted successfully"}), 200

if __name__ == '__main__':
    port = int(os.getenv("BACKEND_PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)











# import os
# import time
# from datetime import datetime, timedelta

# from flask import Flask, request, jsonify, make_response
# from flask_cors import CORS
# from dotenv import load_dotenv

# from pymongo import MongoClient
# from pymongo.errors import DuplicateKeyError
# from bson.objectid import ObjectId

# import bcrypt
# import jwt  # PyJWT

# from functools import wraps

# load_dotenv()  

# app = Flask(__name__)

# # CORS: allow Vite dev origin and credentials
# CORS(
#     app,
#     resources={r"/*": {"origins": ["http://localhost:5173"]}},
#     supports_credentials=True,
# )

# # MongoDB
# MONGO_URL = os.getenv("DATABASE_URL")
# client = MongoClient(MONGO_URL)
# db = client["FarmDesk"]
# users = db.users
# crops = db.crops
# users.create_index([("company_id", 1), ("username", 1)], unique=True)  # enforce per-company uniqueness

# # JWT secret
# JWT_SECRET = os.getenv("JWT_SECRET", "dev_secret_change_me")
# JWT_ALG = "HS256"

# # Cookie config via env
# COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"  # True for HTTPS
# COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "Lax")  # Lax/Strict/None
# COOKIE_NAME = os.getenv("COOKIE_NAME", "auth_token")
# COOKIE_PATH = "/"

# # -------- Utilities --------
# def hash_password(plain: str) -> bytes:
#     return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt())

# def check_password(plain: str, hashed: bytes) -> bool:
#     try:
#         return bcrypt.checkpw(plain.encode("utf-8"), hashed)
#     except Exception:
#         return False

# def jwt_issue(user_doc, ttl_hours=8):
#     now = int(time.time())
#     payload = {
#         "sub": str(user_doc["_id"]),
#         "role": user_doc.get("role", "company_admin"),
#         "company_id": user_doc.get("company_id"),
#         "username": user_doc.get("username"),
#         "iat": now,
#         "exp": now + 60 * 60 * ttl_hours,
#     }
#     return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

# def jwt_verify(token: str):
#     return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])

# def get_token_from_request():
#     # Prefer HttpOnly cookie
#     token = request.cookies.get(COOKIE_NAME)
#     if token:
#         return token
#     # Fallback: Authorization Bearer
#     auth = request.headers.get("Authorization", "")
#     if auth.startswith("Bearer "):
#         return auth.split(" ", 1)[1].strip()
#     return None

# def current_user():
#     token = get_token_from_request()
#     if not token:
#         return None, "Missing token"
#     try:
#         payload = jwt_verify(token)
#         uid = payload.get("sub")
#         if not uid:
#             return None, "Invalid token"
#         doc = users.find_one({"_id": ObjectId(uid)}, {"password_hash": 0})
#         if not doc:
#             return None, "User not found"
#         doc["_id"] = str(doc["_id"])
#         return doc, None
#     except Exception:
#         return None, "Invalid or expired token"

# def require_auth(fn):
#     @wraps(fn)
#     def wrapper(*args, **kwargs):
#         user, err = current_user()
#         if err:
#             return jsonify({"error": "Unauthorized"}), 401
#         request.user = user
#         return fn(*args, **kwargs)
#     return wrapper

# def require_role(*roles):
#     def deco(fn):
#         @wraps(fn)
#         def wrapper(*args, **kwargs):
#             user, err = current_user()
#             if err:
#                 return jsonify({"error": "Unauthorized"}), 401
#             if user.get("role") not in roles:
#                 return jsonify({"error": "Forbidden"}), 403
#             request.user = user
#             return fn(*args, **kwargs)
#         return wrapper
#     return deco

# def set_auth_cookie(resp, token, hours=8):
#     expires = datetime.utcnow() + timedelta(hours=hours)
#     resp.set_cookie(
#         COOKIE_NAME,
#         token,
#         httponly=True,
#         secure=COOKIE_SECURE,
#         samesite=COOKIE_SAMESITE,
#         expires=expires,
#         path=COOKIE_PATH,
#     )
#     return resp

# def clear_auth_cookie(resp):
#     resp.set_cookie(COOKIE_NAME, "", expires=0, path=COOKIE_PATH, samesite=COOKIE_SAMESITE, secure=COOKIE_SECURE)
#     return resp

# # -------- Super Admin: create company admin --------
# @app.route('/superadmin/create_admin', methods=['POST'])
# def create_company_admin():
#     data = request.json or {}
#     username = data.get('username')
#     password = data.get('password')
#     company_id = data.get('company_id')

#     if not username or not password or not company_id:
#         return jsonify({"error": "Missing required fields"}), 400

#     if users.find_one({"company_id": company_id, "username": username}):
#         return jsonify({"error": "Username already exists in this company"}), 409

#     hashed_pw = hash_password(password)
#     user_doc = {
#         "username": username,
#         "password_hash": hashed_pw,
#         "role": "company_admin",
#         "company_id": company_id
#     }

#     try:
#         res = users.insert_one(user_doc)
#         return jsonify({"message": "Company admin created successfully", "id": str(res.inserted_id)}), 201
#     except DuplicateKeyError:
#         return jsonify({"error": "Username already exists in this company"}), 409

# # -------- Auth: me, login, logout --------
# @app.route("/api/auth/me", methods=["GET"])
# def auth_me():
#     user, err = current_user()
#     if err:
#         return jsonify({"error": err}), 401
#     return jsonify(user), 200

# @app.route("/api/auth/logout", methods=["POST"])
# def auth_logout():
#     resp = make_response(jsonify({"message": "Logged out"}))
#     return clear_auth_cookie(resp), 200

# @app.route("/admin/login", methods=["POST"])
# def admin_login():
#     data = request.json or {}
#     company_id = data.get("company_id")
#     username = data.get("username")
#     password = data.get("password")

#     if not company_id or not username or not password:
#         return jsonify({"error": "Missing required fields"}), 400

#     user = users.find_one({"company_id": company_id, "username": username})
#     if not user:
#         return jsonify({"error": "User Not Found"}), 401

#     if user.get("role") != "company_admin":
#         return jsonify({"error": "Unauthorized role"}), 403

#     if not check_password(password, user.get("password_hash", b"")):
#         return jsonify({"error": "Please Enter Correct Password"}), 401

#     # Issue JWT and set HttpOnly cookie
#     token = jwt_issue(user, ttl_hours=8)
#     resp = make_response(jsonify({"message": "Login successful"}))
#     set_auth_cookie(resp, token, hours=8)
#     return resp, 200

# # -------- Officer Login --------
# @app.route("/officer/login", methods=["POST"])
# def officer_login():
#     data = request.json or {}
#     company_id = data.get("company_id")
#     username = data.get("username")
#     password = data.get("password")

#     if not company_id or not username or not password:
#         return jsonify({"error": "Missing required fields"}), 400

#     # Support both legacy and new role values
#     user = users.find_one({
#         "company_id": company_id,
#         "username": username,
#         "role": {"$in": ["Officer", "company_officer", "officer"]},
#     })
#     if not user:
#         return jsonify({"error": "User Not Found"}), 401

#     if not check_password(password, user.get("password_hash", b"")):
#         return jsonify({"error": "Please Enter Correct Password"}), 401

#     token = jwt_issue(user, ttl_hours=8)
#     resp = make_response(jsonify({"message": "Login successful"}))
#     set_auth_cookie(resp, token, hours=8)
#     return resp, 200

# # -------- Admin: Officers management --------
# @app.route("/admin/officers", methods=["GET"])
# @require_role("company_admin")
# def list_officers():
#     user = request.user  # set by decorator
#     company_id = user.get("company_id")
#     items = []
#     for doc in users.find({"company_id": company_id, "role": "Officer"}):
#         doc["_id"] = str(doc["_id"])
#         # Do not expose password hash
#         doc.pop("password_hash", None)
#         items.append(doc)
#     return jsonify({"items": items}), 200


# @app.route("/admin/officers", methods=["POST"])
# @require_role("company_admin")
# def create_officer():
#     user = request.user
#     company_id = user.get("company_id")
#     data = request.json or {}
#     username = (data.get("username") or "").strip()
#     password = (data.get("password") or "").strip()

#     if not username or not password:
#         return jsonify({"error": "Username and password are required"}), 400

#     if users.find_one({"company_id": company_id, "username": username}):
#         return jsonify({"error": "Username already exists"}), 409

#     user_doc = {
#         "username": username,
#         "password_hash": hash_password(password),
#         "role": "Officer",
#         "company_id": company_id,
#     }
#     res = users.insert_one(user_doc)
#     return jsonify({"message": "Officer created", "id": str(res.inserted_id)}), 201


# @app.route("/admin/officers/<officer_id>", methods=["DELETE"])
# @require_role("company_admin")
# def delete_officer(officer_id):
#     user = request.user
#     company_id = user.get("company_id")
#     try:
#         oid = ObjectId(officer_id)
#     except Exception:
#         return jsonify({"error": "Invalid officer id"}), 400

#     # Only allow deleting officers of same company and officer role
#     res = users.delete_one({"_id": oid, "company_id": company_id, "role": {"$in": ["Officer", "company_officer", "officer"]}})
#     if res.deleted_count == 0:
#         return jsonify({"error": "Officer not found"}), 404
#     return jsonify({"message": "Officer deleted"}), 200


# @app.route("/admin/officers", methods=["POST"])
# @require_role("company_admin")
# def admin_create_officer():
#     """
#     Body: { "username": "...", "password": "..." }
#     company_id is taken from the authenticated admin (request.user)
#     """
#     data = request.json or {}
#     username = data.get("username")
#     password = data.get("password")

#     if not username or not password:
#         return jsonify({"error": "Missing required fields"}), 400

#     # company_id from authenticated admin
#     admin_user = request.user  # set by @require_role
#     company_id = admin_user.get("company_id")
#     if not company_id:
#         return jsonify({"error": "Admin missing company_id"}), 400

#     # Optional friendly pre-check (DB unique index is the real guard)
#     if users.find_one({"company_id": company_id, "username": username}):
#         return jsonify({"error": "Username already exists in this company"}), 409  # conflict

#     hashed_pw = hash_password(password)
#     officer_doc = {
#         "username": username,
#         "password_hash": hashed_pw,
#         "role": "company_officer",
#         "company_id": company_id
#     }

#     try:
#         res = users.insert_one(officer_doc)
#         return jsonify({
#             "message": "Officer created successfully",
#             "id": str(res.inserted_id),
#             "username": username,
#             "company_id": company_id
#         }), 201
#     except DuplicateKeyError:
#         return jsonify({"error": "Username already exists in this company"}), 409


# @app.route("/admin/officers", methods=["GET"])
# @require_role("company_admin")
# def admin_list_officers():
#     company_id = request.user.get("company_id")
#     docs = users.find(
#         {"company_id": company_id, "role": "company_officer"},
#         {"password_hash": 0}
#     )
#     items = []
#     for d in docs:
#         d["_id"] = str(d["_id"])
#         items.append(d)
#     return jsonify({"items": items}), 200


# # -------- Admin: Crops management --------
# @app.route("/admin/crops", methods=["GET"])
# @require_role("company_admin")
# def list_crops():
#     user = request.user
#     company_id = user.get("company_id")
    
#     # Find or create crops document for this company
#     crop_doc = crops.find_one({"company_id": company_id})
#     if not crop_doc:
#         # Create initial crops document
#         crop_doc = {
#             "company_id": company_id,
#             "crop_details": []
#         }
#         crops.insert_one(crop_doc)
    
#     return jsonify({"crop_details": crop_doc.get("crop_details", [])}), 200


# @app.route("/admin/crops", methods=["POST"])
# @require_role("company_admin")
# def add_crop():
#     user = request.user
#     company_id = user.get("company_id")
#     data = request.json or {}
    
#     crop_name = (data.get("crop_name") or "").strip()
#     rate_per_unit = data.get("rate_per_unit")
    
#     if not crop_name or not rate_per_unit:
#         return jsonify({"error": "Crop name and rate per unit are required"}), 400
    
#     try:
#         rate_per_unit = float(rate_per_unit)
#         if rate_per_unit < 0:
#             return jsonify({"error": "Rate per unit must be positive"}), 400
#     except (ValueError, TypeError):
#         return jsonify({"error": "Invalid rate per unit"}), 400
    
#     # Check if crop already exists for this company
#     crop_doc = crops.find_one({"company_id": company_id})
#     if crop_doc:
#         existing_crops = crop_doc.get("crop_details", [])
#         if any(crop["crop_name"].lower() == crop_name.lower() for crop in existing_crops):
#             return jsonify({"error": "Crop already exists"}), 409
    
#     # Create new crop entry
#     new_crop = {
#         "crop_name": crop_name,
#         "rate_per_unit": rate_per_unit,
#         "created_at": datetime.utcnow(),
#         "updated_at": datetime.utcnow(),
#         "created_by": user.get("username"),
#         "updated_by": user.get("username")
#     }
    
#     # Add to crops document
#     if crop_doc:
#         crops.update_one(
#             {"company_id": company_id},
#             {"$push": {"crop_details": new_crop}}
#         )
#     else:
#         crops.insert_one({
#             "company_id": company_id,
#             "crop_details": [new_crop]
#         })
    
#     return jsonify({"message": "Crop added successfully", "crop": new_crop}), 201


# @app.route("/admin/crops/<crop_name>", methods=["PUT"])
# @require_role("company_admin")
# def update_crop(crop_name):
#     user = request.user
#     company_id = user.get("company_id")
#     data = request.json or {}
    
#     new_crop_name = (data.get("crop_name") or "").strip()
#     rate_per_unit = data.get("rate_per_unit")
    
#     if not new_crop_name or not rate_per_unit:
#         return jsonify({"error": "Crop name and rate per unit are required"}), 400
    
#     try:
#         rate_per_unit = float(rate_per_unit)
#         if rate_per_unit < 0:
#             return jsonify({"error": "Rate per unit must be positive"}), 400
#     except (ValueError, TypeError):
#         return jsonify({"error": "Invalid rate per unit"}), 400
    
#     # Find the crop document
#     crop_doc = crops.find_one({"company_id": company_id})
#     if not crop_doc:
#         return jsonify({"error": "No crops found for this company"}), 404
    
#     crop_details = crop_doc.get("crop_details", [])
#     crop_index = None
    
#     # Find the crop to update
#     for i, crop in enumerate(crop_details):
#         if crop["crop_name"] == crop_name:
#             crop_index = i
#             break
    
#     if crop_index is None:
#         return jsonify({"error": "Crop not found"}), 404
    
#     # Check if new name conflicts with existing crops (excluding current one)
#     for i, crop in enumerate(crop_details):
#         if i != crop_index and crop["crop_name"].lower() == new_crop_name.lower():
#             return jsonify({"error": "Crop name already exists"}), 409
    
#     # Update the crop
#     crop_details[crop_index] = {
#         "crop_name": new_crop_name,
#         "rate_per_unit": rate_per_unit,
#         "created_at": crop_details[crop_index]["created_at"],  # Keep original created_at
#         "updated_at": datetime.utcnow(),
#         "created_by": crop_details[crop_index]["created_by"],  # Keep original created_by
#         "updated_by": user.get("username")  # Update with current admin
#     }
    
#     crops.update_one(
#         {"company_id": company_id},
#         {"$set": {"crop_details": crop_details}}
#     )
    
#     return jsonify({"message": "Crop updated successfully", "crop": crop_details[crop_index]}), 200


# @app.route("/admin/crops/<crop_name>", methods=["DELETE"])
# @require_role("company_admin")
# def delete_crop(crop_name):
#     user = request.user
#     company_id = user.get("company_id")
    
#     # Find the crop document
#     crop_doc = crops.find_one({"company_id": company_id})
#     if not crop_doc:
#         return jsonify({"error": "No crops found for this company"}), 404
    
#     crop_details = crop_doc.get("crop_details", [])
    
#     # Find and remove the crop
#     updated_crops = [crop for crop in crop_details if crop["crop_name"] != crop_name]
    
#     if len(updated_crops) == len(crop_details):
#         return jsonify({"error": "Crop not found"}), 404
    
#     crops.update_one(
#         {"company_id": company_id},
#         {"$set": {"crop_details": updated_crops}}
#     )
    
#     return jsonify({"message": "Crop deleted successfully"}), 200


# if __name__ == '__main__':
#     port = int(os.getenv("BACKEND_PORT", 5000))
#     app.run(host='0.0.0.0', port=port, debug=True)


