"""
auth.py — EcoAdapt authentication system

Handles user registration, login, logout, session management,
and API key generation for pod pairing.
"""

import os
import secrets
import bcrypt
from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template_string
from functools import wraps
from lib.db import get_db

auth = Blueprint("auth", __name__)

# ─────────────────────────────────────────────────────────
# DB HELPERS
# ─────────────────────────────────────────────────────────

def init_users_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT UNIQUE NOT NULL,
            password    TEXT NOT NULL,
            api_key     TEXT UNIQUE NOT NULL,
            difficulty  TEXT DEFAULT 'NORMAL',
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def get_user_by_username(username):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM users WHERE username=?", (username,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_id(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM users WHERE id=?", (user_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_api_key(api_key):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM users WHERE api_key=?", (api_key,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def create_user(username, password):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    api_key = generate_api_key()
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username, password, api_key) VALUES (?,?,?)",
            (username, hashed, api_key)
        )
        conn.commit()

        # Create default plant config for this user
        user = get_user_by_username(username)
        conn.execute(
            "INSERT INTO plant_config (user_id) VALUES (?)",
            (user["id"],)
        )
        conn.commit()
        return user["id"], api_key
    except Exception as e:
        return None, str(e)
    finally:
        conn.close()

def verify_password(username, password):
    user = get_user_by_username(username)
    if not user:
        return None
    if bcrypt.checkpw(password.encode(), user["password"].encode()):
        return user
    return None

def generate_api_key():
    return "ea_" + secrets.token_urlsafe(24)

def regenerate_api_key(user_id):
    new_key = generate_api_key()
    conn = get_db()
    conn.execute(
        "UPDATE users SET api_key=? WHERE id=?", (new_key, user_id)
    )
    conn.commit()
    conn.close()
    return new_key

# ─────────────────────────────────────────────────────────
# SESSION HELPERS
# ─────────────────────────────────────────────────────────

def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_user_by_id(user_id)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            if request.is_json:
                return jsonify({"error": "unauthorized"}), 401
            return redirect(url_for("auth.login_page"))
        return f(*args, **kwargs)
    return decorated

def api_key_or_login_required(f):
    """For API endpoints — accepts either session login or X-API-Key header."""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Check API key header first
        api_key = request.headers.get("X-API-Key")
        if api_key:
            user = get_user_by_api_key(api_key)
            if user:
                request.api_user = user
                return f(*args, **kwargs)
            return jsonify({"error": "invalid api key"}), 401

        # Fall back to session
        if session.get("user_id"):
            request.api_user = get_user_by_id(session["user_id"])
            return f(*args, **kwargs)

        return jsonify({"error": "unauthorized"}), 401
    return decorated

# ─────────────────────────────────────────────────────────
# LOGIN / REGISTER PAGES
# ─────────────────────────────────────────────────────────

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EcoAdapt — Sign In</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;1,400&family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: #0c0f0a;
  color: #d8e4cc;
  font-family: 'DM Sans', sans-serif;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
.card {
  background: #131710;
  border: 1px solid #2a3324;
  border-radius: 16px;
  padding: 40px;
  width: 100%;
  max-width: 380px;
}
.logo {
  font-family: 'Playfair Display', serif;
  font-size: 28px;
  color: #7ec44f;
  text-align: center;
  margin-bottom: 6px;
}
.subtitle {
  text-align: center;
  font-size: 12px;
  color: #6b7d5e;
  margin-bottom: 32px;
  font-family: 'DM Mono', monospace;
}
.form-group { margin-bottom: 16px; }
.form-label {
  display: block;
  font-size: 10px;
  color: #6b7d5e;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-family: 'DM Mono', monospace;
  margin-bottom: 6px;
}
.form-input {
  width: 100%;
  background: #1a1f16;
  border: 1px solid #2a3324;
  border-radius: 6px;
  padding: 10px 12px;
  color: #d8e4cc;
  font-size: 14px;
  outline: none;
  transition: border-color 0.15s;
  font-family: 'DM Sans', sans-serif;
}
.form-input:focus { border-color: #7ec44f; }
.btn {
  width: 100%;
  padding: 12px;
  border-radius: 6px;
  border: none;
  background: #4a8c28;
  color: #d8f4b8;
  font-family: 'DM Mono', monospace;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.15s;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-top: 8px;
}
.btn:hover { background: #3a7020; }
.error {
  background: #2a1410;
  border: 1px solid #7a3428;
  border-radius: 6px;
  padding: 10px 12px;
  font-size: 12px;
  color: #c85a4a;
  margin-bottom: 16px;
  font-family: 'DM Mono', monospace;
}
.link {
  text-align: center;
  margin-top: 20px;
  font-size: 12px;
  color: #6b7d5e;
}
.link a { color: #7ec44f; text-decoration: none; }
.link a:hover { text-decoration: underline; }
</style>
</head>
<body>
<div class="card">
  <div class="logo">🌿 EcoAdapt</div>
  <div class="subtitle">{{ mode == 'register' and 'Create your account' or 'Welcome back' }}</div>

  {% if error %}
  <div class="error">{{ error }}</div>
  {% endif %}

  <form method="POST">
    <div class="form-group">
      <label class="form-label">Username</label>
      <input class="form-input" type="text" name="username" required autocomplete="username">
    </div>
    <div class="form-group">
      <label class="form-label">Password</label>
      <input class="form-input" type="password" name="password" required autocomplete="{{ mode == 'register' and 'new-password' or 'current-password' }}">
    </div>
    {% if mode == 'register' %}
    <div class="form-group">
      <label class="form-label">Confirm Password</label>
      <input class="form-input" type="password" name="confirm_password" required autocomplete="new-password">
    </div>
    {% endif %}
    <button class="btn" type="submit">{{ mode == 'register' and 'Create Account' or 'Sign In' }}</button>
  </form>

  <div class="link">
    {% if mode == 'register' %}
      Already have an account? <a href="/login">Sign in</a>
    {% else %}
      Don't have an account? <a href="/register">Create one</a>
    {% endif %}
  </div>
</div>
</body>
</html>
"""

# ─────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────

@auth.route("/login", methods=["GET", "POST"])
def login_page():
    if session.get("user_id"):
        return redirect("/")

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")

        user = verify_password(username, password)
        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect("/")
        else:
            error = "Invalid username or password."

    return render_template_string(LOGIN_HTML, mode="login", error=error)


@auth.route("/register", methods=["GET", "POST"])
def register_page():
    if session.get("user_id"):
        return redirect("/")

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        if len(username) < 3:
            error = "Username must be at least 3 characters."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif password != confirm:
            error = "Passwords do not match."
        elif get_user_by_username(username):
            error = "Username already taken."
        else:
            user_id, result = create_user(username, password)
            if user_id:
                session["user_id"] = user_id
                session["username"] = username
                return redirect("/")
            else:
                error = f"Registration failed: {result}"

    return render_template_string(LOGIN_HTML, mode="register", error=error)


@auth.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@auth.route("/api/me", methods=["GET"])
@login_required
def me():
    user = get_current_user()
    return jsonify({
        "id":         user["id"],
        "username":   user["username"],
        "difficulty": user["difficulty"],
        "api_key":    user["api_key"],
        "created_at": user["created_at"],
    }), 200


@auth.route("/api/regenerate-key", methods=["POST"])
@login_required
def regen_key():
    user = get_current_user()
    new_key = regenerate_api_key(user["id"])
    return jsonify({"api_key": new_key}), 200


@auth.route("/api/difficulty", methods=["POST"])
@login_required
def set_difficulty():
    data = request.get_json()
    difficulty = data.get("difficulty", "NORMAL")
    if difficulty not in ["ZEN", "NORMAL", "HARD", "HARDCORE"]:
        return jsonify({"error": "invalid difficulty"}), 400
    conn = get_db()
    conn.execute(
        "UPDATE users SET difficulty=? WHERE id=?",
        (difficulty, session["user_id"])
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True}), 200
