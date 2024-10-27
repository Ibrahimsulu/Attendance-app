import http.client
import urllib.request, urllib.parse, urllib.error
import base64, json, time, requests, cv2, mysql.connector, certifi, ssl

# Disable SSL verification for testing (not recommended for production)
ssl_context = ssl._create_unverified_context()

# Connect to MySQL Database
def connectSQLDatabase():
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="UniVision"
    )
    cursor = connection.cursor()
    return cursor, connection

cursor, connection = connectSQLDatabase()

class FaceID(object):
    """The FaceID Class"""
    base_url = "https://sulu-api-test.cognitiveservices.azure.com/face/v1.0/"
    conn = http.client.HTTPSConnection('sulu-api-test.cognitiveservices.azure.com', context=ssl_context)
    cam = cv2.VideoCapture(0)
    personScanned = ''

    headers = {
        'Content-Type': 'application/json',
        'Ocp-Apim-Subscription-Key': '53FRqBl2eWGRnXs2aJRU3oEC18LbSCTabnB8ga0HL1NaNH7NrRYjJQQJ99AJACmepeSXJ3w3AAAKACOGgn0k',  # Update with your key
    }

    def createGroup(self, groupId, groupName):
        time.sleep(1)  # Delay to avoid rate limits
        params = urllib.parse.urlencode({})
        body = {"name": groupName}
        try:
            self.conn.request("PUT", f"{self.base_url}/persongroups/{groupId}?{params}", json.dumps(body), self.headers)
            response = self.conn.getresponse()
            data = response.read()
            print("GROUP CREATED")
        except Exception as e:
            print(f"Error: {str(e)}")

    def addPerson(self, name, targetGroup):
        time.sleep(1)  # Delay to avoid rate limits
        params = urllib.parse.urlencode({})
        body = {"name": name}
        try:
            self.conn.request("POST", f"{self.base_url}/persongroups/{targetGroup}/persons?{params}", json.dumps(body), self.headers)
            response = self.conn.getresponse()
            data = response.read()
            print(f"PERSON ADDED: {name}")
        except Exception as e:
            print(f"Error: {str(e)}")


    def addFace(self, targetName, targetGroup, URL):
        listOfPersons = self.listPersonsInGroup(targetGroup)
        if isinstance(listOfPersons, list):
            personId = ""
            for person in listOfPersons:
                if person.get("name") == targetName:
                    personId = person["personId"]
                    break
            if personId:
                time.sleep(1)  # Delay to avoid rate limits
                params = urllib.parse.urlencode({})
                body = {"url": URL}
                try:
                    self.conn.request("POST", f"{self.base_url}/persongroups/{targetGroup}/persons/{personId}/persistedFaces?{params}", json.dumps(body), self.headers)
                    response = self.conn.getresponse()
                    data = response.read()
                    print(f"FACE ADDED TO {targetName}")
                except Exception as e:
                    print(f"Error: {str(e)}")
            else:
                print(f"Error: Person '{targetName}' not found in group '{targetGroup}'")
        else:
            print("Error: Invalid response for persons list or empty list.")

    def detectFace(self, imgData):
        time.sleep(1)  # Delay to avoid rate limits
        detectHeaders = {'Content-Type': 'application/octet-stream', 'Ocp-Apim-Subscription-Key': '53FRqBl2eWGRnXs2aJRU3oEC18LbSCTabnB8ga0HL1NaNH7NrRYjJQQJ99AJACmepeSXJ3w3AAAKACOGgn0k'}
        url = f'{self.base_url}/detect'
        try:
            response = requests.post(url, headers=detectHeaders, data=imgData)
            response.raise_for_status()
            face_data = response.json()
            if face_data and "faceId" in face_data[0]:
                return face_data[0]["faceId"]
            else:
                print("NO FACE DETECTED")
                return -1
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e.response.status_code} - {e.response.reason}")
        except Exception as e:
            print(f"Error: {str(e)}")
        return -1

    def identifyFace(self, faceId, targetGroup):
        time.sleep(1)  # Delay to avoid rate limits
        params = urllib.parse.urlencode({})
        body = {'faceIds': [faceId], 'personGroupId': targetGroup}
        try:
            self.conn.request("POST", f"{self.base_url}/identify?{params}", json.dumps(body), self.headers)
            response = self.conn.getresponse()
            data = json.loads(response.read())
            if not data or not data[0]["candidates"]:
                raise IndexError()
            candidatePersonId = data[0]["candidates"][0]["personId"]
            listOfPersons = self.listPersonsInGroup(targetGroup)
            for person in listOfPersons:
                if person["personId"] == candidatePersonId:
                    print("PERSON IDENTIFIED: " + person["name"])
                    return person["name"]
        except IndexError:
            print("***** Idk something went wrong *****")
        except Exception as e:
            print(f"Error: {str(e)}")

    def addStudentToDatabase(self, id, name, programme):
        try:
            # Check if the student already exists
            query_check = "SELECT * FROM students WHERE studentID = %s"
            cursor.execute(query_check, (id,))
            if cursor.fetchone() is None:  # If student does not exist, insert
                query_insert = "INSERT INTO students (studentID, studentName, studentProgramme) VALUES (%s, %s, %s)"
                cursor.execute(query_insert, (id, name, programme))
                connection.commit()
                print(f"Added {name} to database successfully.")
            else:
                print(f"Student {name} with ID {id} already exists in the database.")
        except mysql.connector.Error as err:
            print(f"Error: {err}")
    def trainGroup(self, targetGroup):

        params = urllib.parse.urlencode({})

        try:
            self.conn.request("POST", "/face/v1.0/persongroups/" + targetGroup + "/train?%s" % params, "{body}", self.headers)
            response = self.conn.getresponse()
            data = response.read()
            print("GROUP TRAINED")
        except Exception as e:
            print("[Errno {0}] {1}".format(e.errno, e.strerror))

    def takeFrame(self):
        s, img = self.cam.read()
        return img, cv2.imencode(".jpg",img)[1].tobytes()


    def takeAttendance(self, timetableKey):
        try:
            while True:
                img, imgData = self.takeFrame()
                detectedFaceId = self.detectFace(imgData)
                if detectedFaceId != -1:
                    studentId = self.identifyFace(detectedFaceId, "testgroup")
                    if studentId:
                        checkPresentQuery = "SELECT * FROM attendance WHERE (studentID = %s AND timetableKey = %s)"
                        cursor.execute(checkPresentQuery, (studentId, timetableKey))
                        data = cursor.fetchone()
                        if not data:
                            print('Not in database, add:')
                            addQuery = "INSERT INTO attendance (studentID, timetableKey) VALUES (%s, %s)"
                            cursor.execute(addQuery, (studentId, timetableKey))
                            connection.commit()
                            self.personScanned = studentId
                        else:
                            print('Attendance already taken')
                time.sleep(2)
        except KeyboardInterrupt:
            self.conn.close()

    def getLastPersonScanned(self):
        return self.personScanned

    def getStudentDetails(self, studentId):
        try:
            retrieveDetailsQuery = "SELECT * FROM students WHERE (studentID = '" + studentId + "');"
            cursor.execute(retrieveDetailsQuery)
            return cursor.fetchone()
        except Exception as e:
            print(e)

    def getCourseDetails(self, courseId):
        try:
            retrieveCourseQuery = "SELECT * FROM courses WHERE (courseID = '" + courseId + "');"
            cursor.execute(retrieveCourseQuery)
            return cursor.fetchone()
        except Exception as e:
            print(e)

    def getCourseAttendanceScore(self, studentId, courseId):
        try:
            retrieveTotalNoLecturesQuery = "SELECT timetableKey FROM timetable WHERE (courseID = '" + courseId + "');"
            cursor.execute(retrieveTotalNoLecturesQuery)
            totalNoLectures = len(cursor.fetchall())

            retrieveAllAttendancesQuery = "SELECT * FROM attendance WHERE (studentID = '" + studentId + "');"
            cursor.execute(retrieveAllAttendancesQuery)
            allAttendances = cursor.fetchall()

            totalNoAttendances = 0
            for attendance in allAttendances:
                attendanceQuery = "SELECT courseID FROM timetable WHERE timetableKey = '" + str(attendance[1]) + "';"
                cursor.execute(attendanceQuery)
                if cursor.fetchone() and cursor.fetchone()[0] == courseId:
                    totalNoAttendances += 1

            if totalNoLectures > 0:
                attendanceScore = (totalNoAttendances / totalNoLectures) * 100
                return round(attendanceScore, 2)
            else:
                return 0
        except Exception as e:
            print(e)

    def getTimetableKeysFromCourseId(self, courseId):
        try:
            getTimetableQuery = "SELECT timetableKey FROM timetable WHERE courseID = '" + courseId + "';"
            cursor.execute(getTimetableQuery)
            timetable = cursor.fetchall()

            timetableKeys = []
            for event in timetable:
                timetableKeys.append(event[0])

            return timetableKeys

        except Exception as e:
            print(e)  

    def listPersonsInGroup(self, targetGroup):
        params = urllib.parse.urlencode({})
        try:
            self.conn.request("GET", f"/face/v1.0/persongroups/{targetGroup}/persons?{params}", "{body}", self.headers)
            response = self.conn.getresponse()
            data = response.read()
            print(f"Response status: {response.status}")
            print(f"Response data: {data}")
            if data:  # Check if response data is not empty
                person_list = json.loads(data)
                return person_list if person_list else []
            else:
                print("Error: Received empty response for persons list.")
                return []
        except Exception as e:
            print(f"Error retrieving persons list: {e}")
            return []





    def hackCambridgeTrainInit(self):
        self.createGroup("testgroup", "hello group")
        self.addPerson("0000000", "testgroup")
        self.addPerson("1111111", "testgroup")
        self.addPerson("2222222", "testgroup")
        self.addPerson("3333333", "testgroup")

        # Train the group after adding persons
        self.trainGroup("testgroup")  # Ensure the group is trained before adding faces
        time.sleep(5)

        # Add faces only after the group is trained
        self.addFace("0000000", "testgroup", "faces/matt/matt_image1.jpg")
        self.addFace("0000000", "testgroup", "faces/matt/matt_image2.jpg")
        self.addFace("1111111", "testgroup", "faces/neil/neil_image1.jpg")
        self.addFace("2222222", "testgroup", "faces/raf/raf_image1.jpg")
        self.addFace("3333333", "testgroup", "faces/Sulu/sulu1.PNG")
        self.addFace("3333333", "testgroup", "faces/Sulu/sulu2.PNG")
        self.addFace("3333333", "testgroup", "faces/Sulu/sulu3.PNG")
        self.addFace("3333333", "testgroup", "faces/Sulu/sulu4.PNG")
        self.addFace("3333333", "testgroup", "faces/Sulu/sulu5.PNG")

        # Optionally re-train the group if needed
        self.trainGroup("testgroup")



    def hackCambridgeDatabaseInit(self):
        self.addStudentToDatabase("0000000", "Matt Timmons-Brown", "BEng Computer Science & Electronics")
        self.addStudentToDatabase("1111111", "Neil Weidinger", "BSc Computer Science & Artificial Intelligence")
        self.addStudentToDatabase("2222222", "Rafael Anderka", "BSc Computer Science")
        self.addStudentToDatabase("3333333", "Ibrahim Sulu", "BSc Computer Science")

    def getStudentJson(self, studentId):
        studentDetails = self.getStudentDetails(studentId)

        studentDetailsDict = {
            "name" : studentDetails[2],
            "id" : "s" + studentDetails[1],
            "degree" : studentDetails[3]
        }

        return json.dumps(studentDetailsDict)

    def getCoursesJson(self):
        try:
            getCoursesQuery = "SELECT * FROM courses"
            cursor.execute(getCoursesQuery)
            courses = cursor.fetchall()

            jsonObjects = []
            for course in courses:
                
                attendance = self.getCourseAttendance(course[1])

                courseDict = {
                "courseID" : course[1],
                "courseName" : course[2],
                "school" : course[3],
                "courseAbbreviation" : course[4],
                "attendance" : attendance
                }
            
                jsonObjects.append(json.dumps(courseDict))
            
            return jsonObjects

        except Exception as e:
            print(e)

    def getEventsJson(self,courseId): 
        try: 
            courseDetails = self.getCourseDetails(courseId) 

            getTimetable = "SELECT * FROM timetable WHERE courseID = '" + courseId + "';" 
            cursor.execute(getTimetable) 
            timetable = cursor.fetchall() 

            jsonObjects = [] 
            for event in timetable: 
                attendance = self.getLectureAttendance(str(event[0])) 

                eventDict = { 
                "eventName" : event[4] + " - " + courseDetails[2], 
                "start" : event[2], 
                "end" : event[3], 
                "attendance" : attendance 
                } 

                jsonObjects.append(json.dumps(eventDict)) 

            return jsonObjects 

        except Exception as e: 
            print(e) 
    def wipeAttendanceLog(self, timetableKey):
        try:
            query = "DELETE FROM attendance WHERE timetableKey = %s"
            cursor.execute(query, (timetableKey,))
            connection.commit()
            print("Attendance log wiped for timetable key:", timetableKey)
        except mysql.connector.Error as err:
            print(f"Error: {err}")


    def main(self): 
        self.hackCambridgeTrainInit() # Init only once 
        self.hackCambridgeDatabaseInit() # Also init only once 
        #self.listPersonsInGroup("testgroup") 
        #print(self.getStudentDetails("0000000")) 
        #print(self.getCourseDetails("MATH08057")) 
        #print(self.getCourseAttendanceScore("0000000" ,"MATH08057")) 
        #print(self.getOverallAttendanceScore("0000000")) 
        #self.getStudentJson("0000000") 
        #print(self.getLectureAttendance("8")) 
        #print(self.getCourseAttendance("MATH08057")) 
        #print(self.getTimetableKeysFromCourseId("MATH08057")) 
        #self.getCoursesJson() 
        #self.getEventsJson("MATH08057") 
        self.wipeAttendanceLog("1") 
        print('--------------------------') 
        self.takeAttendance("1") 

if __name__ == "__main__":
    app = FaceID()
    app.main()


