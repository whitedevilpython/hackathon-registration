
# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, jsonify
import mysql.connector
from flask_cors import CORS


app = Flask(__name__)
CORS(app)

# ------------------ Database Connection ------------------
def connect_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",             # change if needed
        password="Prateek@068",  # <-- replace with your MySQL password
        database="hackathon_db"
    )

# ------------------ Generate Unique ID ------------------
def generate_unique_id():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("SELECT unique_id FROM participants ORDER BY id DESC LIMIT 1")
    last_id = cursor.fetchone()

    if last_id and last_id[0]:
        num = int(last_id[0].replace("HACK", ""))
        new_num = num + 1
    else:
        new_num = 1

    cursor.close()
    conn.close()

    return "HACK{0:04d}".format(new_num)   # Example: HACK0001


# ------------------ Routes ------------------
@app.route("/")
def home():
    return render_template("index.html")

# ---------- Register Participant ----------
@app.route("/register", methods=["POST"])
def register():
    try:
        data = request.get_json()
        name = data.get("name")
        email = data.get("email")
        phone = data.get("phone")
        year = data.get("year")
        college = data.get("college")

        if not (name and email and phone and year and college):
            return jsonify({"status": "error", "message": "All fields required"}), 400

        conn = connect_db()
        cursor = conn.cursor()

        # ✅ Check if email already exists
        cursor.execute("SELECT id FROM participants WHERE email = %s", (email,))
        existing = cursor.fetchone()
        if existing:
            conn.close()
            return jsonify({"status": "error", "message": "Email already registered!"}), 400

        # Generate new unique ID
        unique_id = generate_unique_id()

        # Insert new participant
        cursor.execute(
            "INSERT INTO participants (unique_id, name, email, phone, year, college) VALUES (%s, %s, %s, %s, %s, %s)",
            (unique_id, name, email, phone, year, college)
        )
        conn.commit()
        conn.close()

        return jsonify({
            "status": "success",
            "message": "Registration successful!",
            "unique_id": unique_id
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ---------- Admin Page ----------
@app.route("/admin")
def admin():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, unique_id, name, email, phone, year, college FROM participants")
    participants = cursor.fetchall()
    conn.close()
    return render_template("admin.html", participants=participants)

# ---------- Delete Participant ----------
@app.route("/delete", methods=["POST"])
def delete():
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
        conn.close()

        if deleted > 0:
            return jsonify({"status": "success", "message": f"Participant {unique_id} deleted"})
        else:
            return jsonify({"status": "error", "message": "Participant not found"}), 404

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ------------------ Run ------------------
if __name__ == "__main__":
    app.run(debug=True)
