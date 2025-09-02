import os
print("MAIL_USERNAME:", os.getenv("MAIL_USERNAME"))
print("MAIL_PASSWORD:", os.getenv("MAIL_PASSWORD"))

from flask import Flask, render_template, request, jsonify, url_for
import psycopg
from flask_cors import CORS
from flask_mail import Mail, Message
import secrets
import re

app = Flask(__name__)
CORS(app)

# ------------------ Flask-Mail Configuration ------------------
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")  # your email
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")  # app password
# use App Password if Gmail
mail = Mail(app)

# ------------------ Database Connection ------------------
def connect_db():
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        dbname=os.getenv("DB_NAME"),
        sslmode="require"
    )

# ------------------ Generate Unique ID ------------------
def generate_unique_id(cursor):
    cursor.execute("SELECT unique_id FROM participants ORDER BY id DESC LIMIT 1")
    last_id = cursor.fetchone()
    if last_id and last_id[0]:
        num = int(last_id[0].replace("HACK", ""))
        new_num = num + 1
    else:
        new_num = 1
    return "HACK{0:04d}".format(new_num)

# ------------------ Routes ------------------
@app.route("/")
def home():
    return render_template("index.html")

# ---------- Register Participant ----------
@app.route("/register", methods=["POST"])
def register():
    conn = None
    cursor = None
    try:
        data = request.get_json()
        name = data.get("name")
        email = data.get("email")
        phone = data.get("phone")
        year = data.get("year")
        college = data.get("college")

        if not (name and email and phone and year and college):
            return jsonify({"status": "error", "message": "All fields required"}), 400

        # Generate verification token first
        token = secrets.token_urlsafe(16)

        # Try sending verification email BEFORE saving to DB
        verify_link = url_for('verify_email', token=token, _external=True)
        msg = Message(
            subject="Verify Your Email",
            sender=app.config['MAIL_USERNAME'],
            recipients=[email]
        )
        msg.body = f"Hi {name},\nPlease verify your email by clicking this link:\n{verify_link}"

        try:
            mail.send(msg)
        except Exception as mail_error:
            return jsonify({
                "status": "error",
                "message": f"Invalid email or failed to send mail: {mail_error}"
            }), 400

        # If email sent successfully → Save in DB
        conn = connect_db()
        cursor = conn.cursor()

        # Check if email already exists
        cursor.execute("SELECT id FROM participants WHERE email = %s", (email,))
        existing = cursor.fetchone()
        if existing:
            return jsonify({"status": "error", "message": "Email already registered!"}), 400

        # Generate new unique ID
        unique_id = generate_unique_id(cursor)

        # Insert new participant
        cursor.execute(
            """
            INSERT INTO participants (unique_id, name, email, phone, year, college, is_verified, verification_token)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (unique_id, name, email, phone, year, college, False, token)
        )
        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Registration successful! Please check your email to verify.",
            "unique_id": unique_id
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ---------- Email Verification Route ----------
@app.route('/verify/<token>')
def verify_email(token):
    conn = None
    cursor = None
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM participants WHERE verification_token = %s", (token,))
        user = cursor.fetchone()
        if user:
            cursor.execute(
                "UPDATE participants SET is_verified = TRUE, verification_token = NULL WHERE id = %s",
                (user[0],)
            )
            conn.commit()
            return "✅ Email verified! You can now access your registration."
        else:
            return "❌ Invalid or expired verification link."
    except Exception as e:
        return f"Error: {e}", 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ---------- Admin Page ----------
@app.route("/admin")
def admin():
    conn = None
    cursor = None
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, unique_id, name, email, phone, year, college, is_verified FROM participants")
        participants = cursor.fetchall()
        return render_template("admin.html", participants=participants)
    except Exception as e:
        return f"Error: {e}", 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ---------- Delete Participant ----------
@app.route("/delete", methods=["POST"])
def delete():
    conn = None
    cursor = None
    try:
        data = request.get_json()
        unique_id = data.get("unique_id")
        if not unique_id:
            return jsonify({"status": "error", "message": "Unique ID required"}), 400

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM participants WHERE unique_id = %s", (unique_id,))
        conn.commit()
        deleted = cursor.rowcount

        if deleted > 0:
            return jsonify({"status": "success", "message": f"Participant {unique_id} deleted"})
        else:
            return jsonify({"status": "error", "message": "Participant not found"}), 404

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ---------- Test DB Connection ----------
@app.route("/test-db")
def test_db():
    conn = None
    cursor = None
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        return {"status": "ok", "message": f"DB works, result={result}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ------------------ Run ------------------
if __name__ == "__main__":
    app.run(debug=True)
