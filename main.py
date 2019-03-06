from scrape import get_school_courses
from flask import Flask, jsonify
import os

app = Flask(__name__)
app._static_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

courses = list()

def fetch():
    global courses
    courses = get_school_courses("I&C SCI") \
          + get_school_courses("COMPSCI") \
          + get_school_courses("IN4MATX") \
          + get_school_courses("CSE") \
          + get_school_courses("EECS")

fetch()

@app.route("/api/refetch")
def refetch():
    fetch()
    return "OK"

@app.route("/api/prerequisites")
def prerequisites():
    global courses
    return jsonify([course.as_json() for course in courses])

@app.route("/")
def index():
    return app.send_static_file("prerequisites.html")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80)
