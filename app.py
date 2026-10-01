import json
import logging
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request

from services.priority_engine import analyze_complaint

BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "database"
DATABASE_PATH = DATABASE_DIR / "complaints.db"
VALID_STATUSES = {"NEW", "ACKNOWLEDGED", "IN_PROGRESS", "RESOLVED"}
VALID_LANGUAGES = {"en", "ta"}
PRIORITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "NORMAL": 3}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH, timeout=5)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    with closing(get_connection()) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                complaint_text TEXT NOT NULL,
                language TEXT NOT NULL CHECK (language IN ('en', 'ta')),
                priority TEXT NOT NULL CHECK (priority IN ('CRITICAL', 'HIGH', 'MEDIUM', 'NORMAL')),
                score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
                detected_factors TEXT NOT NULL,
                explanation TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'NEW'
                    CHECK (status IN ('NEW', 'ACKNOWLEDGED', 'IN_PROGRESS', 'RESOLVED')),
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
            )
            """
        )
        connection.commit()


def serialize_complaint(row: sqlite3.Row) -> dict[str, Any]:
    complaint = dict(row)
    try:
        complaint["detected_factors"] = json.loads(complaint["detected_factors"])
    except (TypeError, json.JSONDecodeError):
        complaint["detected_factors"] = []
    return complaint


def list_complaints() -> list[dict[str, Any]]:
    with closing(get_connection()) as connection:
        rows = connection.execute(
            """
            SELECT * FROM complaints
            ORDER BY CASE priority
                WHEN 'CRITICAL' THEN 0
                WHEN 'HIGH' THEN 1
                WHEN 'MEDIUM' THEN 2
                ELSE 3
            END, created_at DESC, id DESC
            """
        ).fetchall()
    return [serialize_complaint(row) for row in rows]


def complaint_stats(complaints: list[dict[str, Any]]) -> dict[str, int]:
    stats = {"total": len(complaints), "critical": 0, "high": 0, "medium": 0, "normal": 0}
    for complaint in complaints:
        key = complaint["priority"].lower()
        stats[key] += 1
    return stats


def insert_complaint(complaint_text: str, language: str) -> dict[str, Any]:
    analysis = analyze_complaint(complaint_text)
    with closing(get_connection()) as connection:
        cursor = connection.execute(
            """
            INSERT INTO complaints (
                complaint_text, language, priority, score,
                detected_factors, explanation, status
            ) VALUES (?, ?, ?, ?, ?, ?, 'NEW')
            """,
            (
                complaint_text,
                language,
                analysis["priority"],
                analysis["score"],
                json.dumps(analysis["detected_factors"], ensure_ascii=False),
                analysis["explanation"],
            ),
        )
        row = connection.execute(
            "SELECT * FROM complaints WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        connection.commit()
    result = serialize_complaint(row)
    result["recommended_action"] = analysis["recommended_action"]
    return result


def json_error(message: str, status_code: int):
    return jsonify({"error": message}), status_code


@app.get("/")
def citizen_page():
    return render_template("index.html")


@app.get("/dashboard")
def officer_dashboard():
    return render_template("dashboard.html")


@app.get("/api/complaints")
def get_complaints():
    try:
        complaints = list_complaints()
        return jsonify({"complaints": complaints, "stats": complaint_stats(complaints)})
    except sqlite3.Error:
        app.logger.exception("Could not read complaints")
        return json_error("Complaints are temporarily unavailable. Please try again.", 503)


@app.post("/api/complaints")
def create_complaint():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return json_error("Send a JSON object with complaint_text and language.", 400)

    complaint_text = payload.get("complaint_text")
    language = payload.get("language", "en")
    if not isinstance(complaint_text, str) or not complaint_text.strip():
        return json_error("Please enter or dictate a complaint before submitting.", 400)
    complaint_text = complaint_text.strip()
    if len(complaint_text) > 5000:
        return json_error("Complaint text must be 5,000 characters or fewer.", 400)
    if not isinstance(language, str) or language not in VALID_LANGUAGES:
        return json_error("Language must be 'en' or 'ta'.", 400)

    try:
        complaint = insert_complaint(complaint_text, language)
        return jsonify({
            "message": "Complaint received. An officer should review the information.",
            "complaint": complaint,
            "human_verification_required": complaint["priority"] == "CRITICAL",
        }), 201
    except sqlite3.Error:
        app.logger.exception("Could not save complaint")
        return json_error("We could not save your complaint. Please try again shortly.", 503)


@app.patch("/api/complaints/<int:complaint_id>/status")
def update_complaint_status(complaint_id: int):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return json_error("Send a JSON object containing a status.", 400)
    status = payload.get("status")
    if not isinstance(status, str) or status not in VALID_STATUSES:
        return json_error("Status must be NEW, ACKNOWLEDGED, IN_PROGRESS, or RESOLVED.", 400)

    try:
        with closing(get_connection()) as connection:
            cursor = connection.execute(
                "UPDATE complaints SET status = ? WHERE id = ?", (status, complaint_id)
            )
            if cursor.rowcount == 0:
                return json_error("That complaint could not be found.", 404)
            row = connection.execute(
                "SELECT * FROM complaints WHERE id = ?", (complaint_id,)
            ).fetchone()
            connection.commit()
        return jsonify({"complaint": serialize_complaint(row)})
    except sqlite3.Error:
        app.logger.exception("Could not update complaint status")
        return json_error("Status could not be updated. Please try again.", 503)


@app.post("/api/demo-data")
def add_demo_data():
    examples = [
        ("Enga area-la EB current poiduchu.", "ta"),
        ("Road-la accident nadandhirukku. Immediate help venum.", "ta"),
        (
            "Enga veetla medical equipment depend pannura patient irukanga. "
            "Current immediately venum.",
            "ta",
        ),
    ]
    try:
        inserted = [insert_complaint(text, language) for text, language in examples]
        return jsonify({"message": "Demo complaints added.", "complaints": inserted}), 201
    except sqlite3.Error:
        app.logger.exception("Could not add demo complaints")
        return json_error("Demo complaints could not be added. Please try again.", 503)


@app.errorhandler(413)
def request_too_large(_error):
    return json_error("Request is too large. Complaint text must be 5,000 characters or fewer.", 413)


@app.errorhandler(500)
def internal_server_error(_error):
    app.logger.exception("Unhandled server error")
    if request.path.startswith("/api/"):
        return json_error("Something went wrong. Please try again.", 500)
    return "Something went wrong. Please try again.", 500


initialize_database()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
