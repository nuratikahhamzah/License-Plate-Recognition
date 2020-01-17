from flask import Flask, request, jsonify, render_template, redirect
import os
import pytesseract
from PIL import Image
import numpy as np
import cv2
from pyimagesearch.motion_detection import SingleMotionDetector
from imutils.video import VideoStream
from flask import Response
import threading
import argparse
import imutils
import time
import sqlite3
import glob
import base64
from base64 import b64encode
import datetime as Day
from datetime import datetime
import array
import json
import pusher

app = Flask(__name__)

pusher_client = pusher.Pusher(
    '919386',
    '6d3a12086650daf9eda5',
    'daf8fc65251bcc8cc4c7',
    ssl=True,
    cluster='ap1')

outputFrame = None
lock = threading.Lock()

#################################################################################################### START the plate training #######################
plate_cascade = cv2.CascadeClassifier('plateTraining/1000.xml')

#################################################################################################### START to open the webcam #######################
# cap = cv2.VideoCapture("rtsp://192.168.0.184:5540/ch0")
cap = cv2.VideoCapture(0)
#################################################################################################### START to create a captured folder ##############
try:
    #to create a folder of plate captured
    if not os.path.exists('captured'):
        os.makedirs('captured')
#if the folder does not create then error raise
except OSError:
    print('Error: Creating directory of data')

#####################################################################################################################################################
def dict_factory(cursor, row):
    d ={}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def Enquiry(lis1): 
    if len(lis1) == 0: 
        return 0
    else: 
        return 1
#################################################################################################### START function to store to the database #################
def create_database(image, txt, masa):
    conn = sqlite3.connect("Plate3.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Plate3
    (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, image BLOB, txt TEXT, masa TEXT)""")

    cursor.execute("""
    INSERT INTO Plate3
    (image, txt, masa) VALUES (?,?,?)""", (image,txt,masa))

    conn.commit()
    cursor.close()
    conn.close()

#################################################################################################### START detect plate function ####################
def detect_motion(frameCount):
    frame_number = 0
    global cap, outputFrame, lock

    storePlate = 0 # to count frame that already capture !!!

    md = SingleMotionDetector(accumWeight=0.1)
    total = 0

    while True:
        ret, gmbr = cap.read()
        # cv2.imshow('VIDEO', gmbr)
        gray = cv2.cvtColor(gmbr, cv2.COLOR_BGR2GRAY)

        # noise removal with iterative bilateral filter(remove noise while preserving edges)
        gray = cv2.bilateralFilter(gray, 11, 17, 17)
        # cv2.imshow("2 - Bilateral Filter", gray)

        plates = plate_cascade.detectMultiScale(gray, 1.3, 5)

            # used for resizing the video
            # img = cv2.resize(img, (640,480))

        for (x,y,w,h) in plates:
            cv2.rectangle(gmbr,(x,y),(x+w,y+h),(255,0,0),2)
            plate_gray = gray[y:y+h, x:x+w] # gray plate
            plate_color = gmbr[y:y+h, x:x+w] # colour plate
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.putText(gmbr,'Plate',(x,y), font, 0.5, (11,255,255), 2, cv2.LINE_AA)

            # cv2.imshow('Colour Plate',plate_color)

            # time captured 
            dt = str(datetime.now())
            print(dt)

            # to store the grayscale image as a TEMPORARY file to apply the OCR
            filename = "./captured/temp" + ".png"
            cv2.imwrite(filename, plate_gray)

            # load image, apply OCR
            txt = pytesseract.image_to_string(Image.open(filename), lang = 'eng')
            print(txt)

            cv2.putText(gmbr, txt ,(x,y), font, 1, (11,255,255), 3, cv2.LINE_AA)

            # here -> cara untuk baca image dari file and hntr ke pusher
            for filename in glob.glob('captured/*.png'):
                if ".png" in filename:
                    with open(filename,"rb") as f:
                        data = f.read()
                        # data['img'] = base64.encodebytes(img).decode("utf-8")
                        # image = json.dumps(data)
                        image = base64.b64encode(data)
                        create_database(image=data, txt=txt, masa=dt )

            image = image.decode("utf-8")            
            print(image)

            data = {"image": image, "txt": txt, "masa": dt}
            pusher_client.trigger('Plate4', 'new-record', {'data': data})

        # to display day, date and time on the video
        timestamp = Day.datetime.now()
        cv2.putText(gmbr, timestamp.strftime("%A %d %B %Y %I:%M:%S%p"), (10,gmbr.shape[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

        md.update(gray)
        total += 1

        with lock:
            outputFrame = gmbr.copy()

###################################################################################################### START encode image for display video #############
def generate():
    global outputFrame, lock
    while True:
        with lock:
            if outputFrame is None:
                continue

            (flag, encodedImage) = cv2.imencode(".jpg", outputFrame)

            if not flag:
                continue

        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n')
    
###################################################################################################### START the video feed ##################
@app.route("/video_feed")
def video_feed():
    return Response(generate(),mimetype = "multipart/x-mixed-replace; boundary=frame")

###################################################################################################### START python <-> html #################
@app.route('/')
def index():

    conn = sqlite3.connect("Plate3.db")
    cursor = conn.cursor()

    return render_template('lpr.html')

###################################################################################################### START run Flask app ###################
if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument("-f", "--frame-count", type=int, default=32,help="# of frames used to construct the background model")
    args = vars(ap.parse_args())

    t = threading.Thread(target=detect_motion, args=(args["frame_count"],))
    t.daemon = True
    t.start()
    app.run(debug=True, threaded=True, use_reloader=False)

    app.run()
