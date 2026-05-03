"""
Student Result Tracker API
===========================
A RESTful API built with Python Flask for managing student results.
Author: Saranya S
Tech Stack: Python, Flask, REST API, JSON
"""

from flask import Flask, jsonify, request, render_template
import json
import os
from datetime import datetime

app = Flask(__name__)

# ── Data Store (JSON file as lightweight database) ──
DATA_FILE = "data/students.json"

def load_data():
    """Load student data from JSON file."""
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    """Save student data to JSON file."""
    os.makedirs("data", exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def calculate_grade(average):
    """Calculate letter grade based on average marks."""
    if average >= 90:
        return "O"
    elif average >= 80:
        return "A+"
    elif average >= 70:
        return "A"
    elif average >= 60:
        return "B+"
    elif average >= 50:
        return "B"
    elif average >= 40:
        return "C"
    else:
        return "F"

def calculate_result(subjects):
    """Calculate average, grade, and pass/fail from subject marks."""
    if not subjects:
        return 0, "N/A", "N/A"
    marks = list(subjects.values())
    average = round(sum(marks) / len(marks), 2)
    grade = calculate_grade(average)
    result = "Pass" if all(m >= 40 for m in marks) else "Fail"
    return average, grade, result

def find_student(students, roll_no):
    """Find a student by roll number."""
    for i, s in enumerate(students):
        if s["roll_no"].lower() == roll_no.lower():
            return i, s
    return -1, None


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/students", methods=["GET"])
def get_all_students():
    students = load_data()
    dept_filter = request.args.get("department", "").strip().lower()
    if dept_filter:
        students = [s for s in students if s.get("department", "").lower() == dept_filter]
    result_list = []
    for s in students:
        avg, grade, result = calculate_result(s.get("subjects", {}))
        result_list.append({**s, "average": avg, "grade": grade, "result": result})
    return jsonify({"success": True, "count": len(result_list), "students": result_list}), 200


@app.route("/api/students/<roll_no>", methods=["GET"])
def get_student(roll_no):
    students = load_data()
    _, student = find_student(students, roll_no)
    if not student:
        return jsonify({"success": False, "message": f"Student '{roll_no}' not found."}), 404
    avg, grade, result = calculate_result(student.get("subjects", {}))
    return jsonify({"success": True, "student": {**student, "average": avg, "grade": grade, "result": result}}), 200


@app.route("/api/students", methods=["POST"])
def add_student():
    data = request.get_json()
    required = ["roll_no", "name", "department", "semester", "subjects"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"success": False, "message": f"Missing fields: {', '.join(missing)}"}), 400
    if not isinstance(data["subjects"], dict) or not data["subjects"]:
        return jsonify({"success": False, "message": "Subjects must be a non-empty dictionary."}), 400
    for subj, marks in data["subjects"].items():
        if not isinstance(marks, (int, float)) or not (0 <= marks <= 100):
            return jsonify({"success": False, "message": f"Invalid marks for '{subj}'. Must be 0-100."}), 400
    students = load_data()
    idx, existing = find_student(students, data["roll_no"])
    if existing:
        return jsonify({"success": False, "message": f"Student '{data['roll_no']}' already exists."}), 409
    new_student = {
        "roll_no": data["roll_no"].upper(),
        "name": data["name"].strip(),
        "department": data["department"].strip().upper(),
        "semester": data["semester"],
        "subjects": data["subjects"],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    students.append(new_student)
    save_data(students)
    avg, grade, result = calculate_result(new_student["subjects"])
    return jsonify({"success": True, "message": "Student added successfully.", "student": {**new_student, "average": avg, "grade": grade, "result": result}}), 201


@app.route("/api/students/<roll_no>", methods=["PUT"])
def update_student(roll_no):
    students = load_data()
    idx, student = find_student(students, roll_no)
    if not student:
        return jsonify({"success": False, "message": f"Student '{roll_no}' not found."}), 404
    data = request.get_json()
    if "subjects" in data:
        for subj, marks in data["subjects"].items():
            if not isinstance(marks, (int, float)) or not (0 <= marks <= 100):
                return jsonify({"success": False, "message": f"Invalid marks for '{subj}'."}), 400
    for field in ["name", "department", "semester", "subjects"]:
        if field in data:
            students[idx][field] = data[field]
    students[idx]["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_data(students)
    avg, grade, result = calculate_result(students[idx]["subjects"])
    return jsonify({"success": True, "message": "Student updated successfully.", "student": {**students[idx], "average": avg, "grade": grade, "result": result}}), 200


@app.route("/api/students/<roll_no>", methods=["DELETE"])
def delete_student(roll_no):
    students = load_data()
    idx, student = find_student(students, roll_no)
    if not student:
        return jsonify({"success": False, "message": f"Student '{roll_no}' not found."}), 404
    removed = students.pop(idx)
    save_data(students)
    return jsonify({"success": True, "message": f"Student '{removed['name']}' deleted successfully."}), 200


@app.route("/api/summary", methods=["GET"])
def get_summary():
    students = load_data()
    summary = {}
    for s in students:
        dept = s.get("department", "Unknown")
        avg, grade, result = calculate_result(s.get("subjects", {}))
        if dept not in summary:
            summary[dept] = {"total": 0, "passed": 0, "failed": 0, "toppers": [], "average_scores": []}
        summary[dept]["total"] += 1
        summary[dept]["average_scores"].append(avg)
        if result == "Pass":
            summary[dept]["passed"] += 1
        else:
            summary[dept]["failed"] += 1
        if avg >= 80:
            summary[dept]["toppers"].append({"name": s["name"], "roll_no": s["roll_no"], "average": avg, "grade": grade})
    for dept in summary:
        scores = summary[dept].pop("average_scores")
        summary[dept]["dept_average"] = round(sum(scores) / len(scores), 2) if scores else 0
    return jsonify({"success": True, "summary": summary}), 200


@app.errorhandler(404)
def not_found(e):
    return jsonify({"success": False, "message": "Endpoint not found."}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"success": False, "message": "Method not allowed."}), 405


if __name__ == "__main__":
    app.run(debug=True, port=5000)