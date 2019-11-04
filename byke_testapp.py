# --------------------------------------------
# File: byke_testapp.py
# Date: 30/09/2019
# Author: Tanner L
# Modified:
# Desc: Test application for testing of byke systems, gps, motion sensor, and pic communication.
#       Setup for sql db testing.
# --------------------------------------------
import tkinter as tk
import math
import sqlite3
import board

conn = sqlite3.connect('byke_testApp.db')

print("Opened database successfully")

conn.execute('''CREATE TABLE IF NOT EXISTS TRIP_STATS
        (TRIP_ID  INTEGER PRIMARY KEY NOT NULL,
        TRIP_DATE          TEXT,
        TRIP_TIME          INTEGER,
        TRIP_MAXSPEED      REAL,
        TRIP_AVGSPEED      REAL,
        TRIP_DISTANCE      REAL,
        TRIP_UPDISTANCE    REAL,
        TRIP_DOWNDISTANCE  REAL);''')

conn.execute('''CREATE TABLE IF NOT EXISTS GPS_DATA
         (ENTRY_ID INT PRIMARY KEY     NOT NULL,
         TIME           TEXT    NOT NULL,
         SPEED          REAL,
         LAT            REAL,
         LNG            REAL,
         ALT            REAL,
         CLIMB          REAL,
         XROT           REAL,
         YROT           REAL,
         TRIP_ID        INTEGER NOT NULL,
         FOREIGN KEY (TRIP_ID)
            REFERENCES TRIP_STATS (TRIP_ID) );''')

print("Table created successfully")

conn.close()

# raspberry pi libraries
import smbus  # i2c smbus for pic communication
import gpsd  # Gps library import
import adafruit_dht  # import library for temperature sensor

global leftpressed
leftpressed = 0

global rightpressed
rightpressed = 0

global brakepressed
brakepressed = 0

global headlightpressed
headlightpressed = 0

global i
i = 0

global recordrunning
recordrunning = 0

global list1
list1 = []

global totaldistance
totaldistance = 0

global tripNum
tripNum = 0

# i2c addresses
i2cBus = smbus.SMBus(1)  # Setup for i2c communication via smbus
tailEndPicAddress = 0x55  # i2c address of tail end pic
batteryPicAddress = 0x45  # i2c address of battery location pic

motionAddress = 0x68  # address for mpu5060 motion sensor
motionPowerMgmt1 = 0x6b  # memory location of power register
motionPowerMgmt2 = 0x6c  # memory location of power register


# -----------------------------------------------------
# Function: query_test
# Author:
# Modified: Tanner L
# Date: 01/10/19
# Desc: Test sql query
# Inputs:
# Outputs:
# -----------------------------------------------------
def query_test():

    cur = conn.cursor()
    cur.execute("SELECT * FROM TRIP_STATS WHERE TRIP_ID=?", (tripNum,))

    rows = cur.fetchall()

    conn.close()

    for row in rows:
        print(row)


# -----------------------------------------------------
# Function: temperature_read
# Author:
# Modified: Tanner L
# Date: 01/10/19
# Desc: Read temperature from DHT11 sensor
# Inputs:
# Outputs:
# -----------------------------------------------------
def temperature_read():

    try:
        sensor = adafruit_dht.DHT11(board.D16)  # call library for DHT11 temperature sensor

        temperature = sensor.temperature  # read in temperature and humidity

        temperaturebutton.config(text=str(temperature))
    except RuntimeError as e:
        print('temp error {}'.format(e.args))


# -----------------------------------------------------
# Function: record
# Author:
# Modified: Tanner L
# Date: 01/10/19
# Desc: Start and Stop recording
# Inputs:
# Outputs:
# -----------------------------------------------------
def record():

    global tripNum
    global i
    global recordrunning

    if recordrunning == 1:
        recordrunning = 0
        recordbutton.config(text="Record")

    else:
        recordrunning = 1

        recordbutton.config(text="Recording")

        conn = sqlite3.connect('byke_testApp.db')

        cur = conn.cursor()

        cur.execute("SELECT ENTRY_ID, TRIP_ID FROM GPS_DATA WHERE ENTRY_ID = (SELECT MAX(ENTRY_ID) FROM GPS_DATA)")

        max_entry = cur.fetchone()

        conn.close()

        try:
            i = max_entry[0] + 1
        except:
            i = 0

        try:
            tripNum = max_entry[1] + 1
        except:
            tripNum = 1


# -----------------------------------------------------
# Function: gps
# Author:
# Modified: Tanner L
# Date: 01/10/19
# Desc: Query gps module and save to database
# Inputs:
# Outputs:
# -----------------------------------------------------
def gps():

    global i
    global recordrunning
    global totaldistance
    global list1

    gpsd.connect()
    gpsData = gpsd.get_current()

    if gpsData.mode > 1:

        gpsTime = gpsData.time
        speed = gpsData.hspeed
        gpsLat = gpsData.lat
        gpsLong = gpsData.lon
        gpsAlt = gpsData.alt
        gpsClimb = gpsData.climb

        speed = speed * 3.6

        gpsbutton.config(text='Fix ' + str(i))

        if recordrunning == 1:

            xrotate, yrotate = motion()

            list1.append((i, str(gpsTime), speed, gpsLat, gpsLong, gpsAlt,
                         gpsClimb, xrotate, yrotate, tripNum))
            i += 1

            speed = float(speed)

            if speed > 0.5:
                distance = speed / 3600
                totaldistance = totaldistance + distance

                print("Speed: {} Distance: {} Total Distance: {}".format(speed, distance, totaldistance))

        else:
            try:
                conn = sqlite3.connect('byke_testApp.db')

                c = conn.cursor()

                entry = "INSERT INTO GPS_DATA (ENTRY_ID, TIME, SPEED, LAT, LNG, ALT, CLIMB, TRIP_ID) \
                      VALUES (?, ?, ?, ? ,?, ?, ?, ?)"

                c.executemany(entry, list1)

                conn.commit()

                c.execute("SELECT MAX(SPEED) FROM GPS_DATA")
                maxspeed = c.fetchone()
                print(maxspeed)

                c.execute("SELECT AVG(SPEED) FROM GPS_DATA")
                avgspeed = c.fetchone()
                print(avgspeed)

                listStats = ( (0, 0, maxspeed, avgspeed, totaldistance, 0, 0, tripNum) )

                entry2 = "INSERT INTO TRIP_STATS (TRIP_TIME, TRIP_DATE, TRIP_MAXSPEED, TRIP_AVGSPEED, TRIP_DISTANCE, " \
                         "TRIP_UPDISTANCE, TRIP_DOWNDISTANCE, TRIP_ID)" \
                         " VALUES (?, ?, ?, ?, ?, ?, ?, ?)"

                c.executemany(entry2, listStats)

                conn.commit()

                conn.close()
            except:
                pass

    else:
        gpsbutton.config(text='NO Fix')

    if recordrunning == 1:
        gpsbutton.after(1000, gps)


# -----------------------------------------------------
# Function: read_word
# Author:
# Modified: Tanner L
# Date: 01/10/19
# Desc: Combine two register from motion sensor
# Inputs:
# Outputs:
# -----------------------------------------------------
def read_word(adr):
    high = i2cBus.read_byte_data(motionAddress, adr)
    low = i2cBus.read_byte_data(motionAddress, adr + 1)
    val = (high << 8) + low
    return val


# -----------------------------------------------------
# Function: read_word_motion
# Author:
# Modified: Tanner L
# Date: 01/10/19
# Desc: Adjust value from motion sensor
# Inputs:
# Outputs:
# -----------------------------------------------------
def read_word_motion(adr):
    val = read_word(adr)
    if val >= 0x8000:
        return -((65535 - val) + 1)
    else:
        return val


# -----------------------------------------------------
# Function: motion
# Author:
# Modified: Tanner L
# Date: 01/10/19
# Desc: Query motion sensor
# Inputs:
# Outputs:
# -----------------------------------------------------
def motion():

    i2cBus.write_byte_data(motionAddress, motionPowerMgmt1, 0)
    accel_xout_scaled = read_word_motion(0x3b) / 16384.0
    accel_yout_scaled = read_word_motion(0x3d) / 16384.0
    accel_zout_scaled = read_word_motion(0x3f) / 16384.0
    yRotate = -math.degrees(math.atan2(accel_xout_scaled, (math.sqrt((accel_yout_scaled * accel_yout_scaled) +
                                                          (accel_zout_scaled * accel_zout_scaled)))))
    xRotate = -math.degrees(math.atan2(accel_yout_scaled, (math.sqrt((accel_xout_scaled * accel_xout_scaled) +
                                                          (accel_zout_scaled * accel_zout_scaled)))))

    motionbutton.config(text=str(round(yRotate, 2) + ' ' + str(round(xRotate, 2))))

    return xRotate, yRotate


# -----------------------------------------------------
# Function: send_tail
# Author:
# Modified: Tanner L
# Date: 01/10/19
# Desc: Send value to tail end pic
# Inputs:
# Outputs:
# -----------------------------------------------------
def send_tail():

    i2cBus.write_byte_data(tailEndPicAddress, int(regspinner.get()), int(regvaluespinner.get()))


# -----------------------------------------------------
# Function: send_motor
# Author:
# Modified: Tanner L
# Date: 01/10/19
# Desc: Send value to motor pic
# Inputs:
# Outputs:
# -----------------------------------------------------
def send_motor():

    i2cBus.write_byte_data(batteryPicAddress, int(regspinner.get()), int(regvaluespinner.get()))


# -----------------------------------------------------
# Function: read_motor
# Author:
# Modified: Tanner L
# Date: 01/10/19
# Desc: Read value from motor pic
# Inputs:
# Outputs:
# -----------------------------------------------------
def read_motor():

    motorrec = i2cBus.read_byte_data(batteryPicAddress, int(regspinner.get()))
    regvaluespinner.delete(0, 'end')
    regvaluespinner.insert(0, motorrec)


# -----------------------------------------------------
# Function: read_tail
# Author:
# Modified: Tanner L
# Date: 01/10/19
# Desc: Read value from tail end pic
# Inputs:
# Outputs:
# -----------------------------------------------------
def read_tail():

    tailrec = i2cBus.read_byte_data(tailEndPicAddress, int(regspinner.get()))
    regvaluespinner.delete(0, 'end')
    regvaluespinner.insert(0, tailrec)


mainWindow = tk.Tk()
mainWindow.title('Byke')
mainWindow.geometry('400x250+0+0')
mainWindow.columnconfigure(0, weight=1)
mainWindow.columnconfigure(1, weight=1)
mainWindow.columnconfigure(2, weight=1)
mainWindow.rowconfigure(0, weight=1)
mainWindow.rowconfigure(1, weight=1)
mainWindow.rowconfigure(2, weight=1)
mainWindow.rowconfigure(3, weight=1)
mainWindow.config(bg='white')

gpsbutton = tk.Button(mainWindow, text='gps', borderwidth=2, command=gps)
gpsbutton.grid(row=0, column=0, sticky='nswe')

if recordrunning == 1:
    gpsbutton.after(1000, gps)

temperaturebutton = tk.Button(mainWindow, text='temperature', borderwidth=2, command=temperature_read)
temperaturebutton.grid(row=2, column=0, sticky='nswe')

motionbutton = tk.Button(mainWindow, text='motion', borderwidth=2, command=motion)
motionbutton.grid(row=3, column=0, sticky='nswe')

recordbutton = tk.Button(mainWindow, text='record', borderwidth=2, command=record)
recordbutton.grid(row=1, column=0, sticky='nswe')

reglabel = tk.Label(mainWindow, text='Register')
reglabel.grid(row=0, column=1, sticky='nsew')

regspinner = tk.Spinbox(mainWindow, width=3, from_=0, to=12, font=(None, 18))
regspinner.grid(row=1, column=1, sticky='nswe')

tailsendbutton = tk.Button(mainWindow, text='Send to Tail', borderwidth=2, command=send_tail)
tailsendbutton.grid(row=0, column=2, sticky='nswe')

motorsendbutton = tk.Button(mainWindow, text='Send to Motor', borderwidth=2, command=send_motor)
motorsendbutton.grid(row=1, column=2, sticky='nswe')

regvalue = tk.Label(mainWindow, text='REG Value')
regvalue.grid(row=2, column=1, sticky='nsew')

tailreadbutton = tk.Button(mainWindow, text='Read Tail', borderwidth=2, command=read_tail)
tailreadbutton.grid(row=2, column=2, sticky='nswe')

motorreadbutton = tk.Button(mainWindow, text='Read Motor', borderwidth=2, command=read_motor)
motorreadbutton.grid(row=3, column=2, sticky='nswe')

regvaluespinner = tk.Spinbox(mainWindow, width=3, from_=0, to=100, font=(None, 18))
regvaluespinner.grid(row=3, column=1, sticky='nswe')

mainWindow.mainloop()


