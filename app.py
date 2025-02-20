from flask import Flask, render_template, request, redirect
import main as UV
import json

app = Flask(__name__)
attendanceApp = UV.FaceID()

# Run once to initialize, if necessary
attendanceApp.hackCambridgeTrainInit()
attendanceApp.hackCambridgeDatabaseInit()


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/courses", methods=["GET", "POST"])
def courses():
    if request.method == "GET":
        return render_template("courses.html")

    # POST request
    else:
        attendanceApp.main()

@app.route("/list", methods=["GET", "POST"])
def list():
    if request.method == "GET":
        coursesList = attendanceApp.getCoursesJson()
        coursesListOfDicts = []
        for course in coursesList:
            coursesListOfDicts.append(json.loads(course))
        return render_template("list.html", coursesList=coursesListOfDicts)

    # POST request
    else:
        return redirect("/list")

@app.route("/poll")
def poll():
    lastPersonScannedId = attendanceApp.getLastPersonScanned()
    # personScannedData = '{"ID" : "' + lastPersonScannedId + '"}'
    personScannedData = attendanceApp.getStudentJson(lastPersonScannedId)
    return personScannedData
