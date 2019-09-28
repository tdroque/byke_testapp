# -----------------------------------------------------
# File: byke_testapp.py
# Author: Tanner L
# Date: 09/18/19
# Desc: Test app for byke project, functions to test gps functions, save data, 
#		and read/write registers on microchips(motor controller pic and tail light pic)
# -----------------------------------------------------
import tkinter as tk
import math
import sqlite3
import board

conn = sqlite3.connect('byke_test.db')

print("Opened database successfully")

conn.execute('''CREATE TABLE BYKEDATA
         (ID INT PRIMARY KEY     NOT NULL,
         TIME           TIME    NOT NULL,
         SPEED          INT     NOT NULL,
         LAT            CHAR(30),
         LONG           CHAR(30),
         LOCATION       CHAR(60));''')

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

# i2c addresses
i2cBus = smbus.SMBus(1)  # Setup for i2c communication via smbus
tailEndPicAddress = 0x55  # i2c address of tail end pic
batteryPicAddress = 0x45  # i2c address of battery location pic
headEndPicAddress = 0x35  # i2c address of head end pic

motionAddress = 0x68  # address for mpu5060 motion sensor
motionPowerMgmt1 = 0x6b  # memory location of power register
motionPowerMgmt2 = 0x6c  # memory location of power register


def temperatureread():

    sensor = adafruit_dht.DHT11(board.D16)  # call library for DHT11 temperature sensor

    temperature = sensor.temperature  # read in temperature and humidity

    temperaturebutton.config(text=str(temperature))


def gps():

    global i
    global recordrunning

    gpsd.connect()
    gpsData = gpsd.get_current()

    if recordrunning == 1:
        recordrunning = 0
    else:
        recordrunning = 1

    if gpsData.mode > 1:
        gpsTime = gpsData.time
        gpsSpeed = gpsData.speed()
        gpsLat = gpsData.lat
        gpsLong = gpsData.lon
        gpsLoc = gpsData.position()
        timelist = list(gpsData.time[11:13])

        gpsbutton.config(text='Fix')

        conn = sqlite3.connect('byke_test.db')

        conn.execute("INSERT INTO BYKEDATA (ID,TIME,SPEED,LAT,LONG,LOCATION) \
              VALUES (i, gpsTime, gpsSpeed, gpsLat , gpsLong )")

        conn.commit()

        conn.close()

        i = i + 1

    gpsbutton.config(text='NO Fix')

    if recordrunning == 1:
        gpsbutton.after(1000, gps)


def read_word(adr):  # function for reading motion sensor data
    high = i2cBus.read_byte_data(motionAddress, adr)
    low = i2cBus.read_byte_data(motionAddress, adr + 1)
    val = (high << 8) + low
    return val


def readWordMotion(adr):  # function for calculating motion sensor data
    val = read_word(adr)
    if val >= 0x8000:
        return -((65535 - val) + 1)
    else:
        return val


def motion():  # function for communicating with motion sensor, mpu5060

    i2cBus.write_byte_data(motionAddress, motionPowerMgmt1, 0)
    accel_xout_scaled = readWordMotion(0x3b) / 16384.0
    accel_yout_scaled = readWordMotion(0x3d) / 16384.0
    accel_zout_scaled = readWordMotion(0x3f) / 16384.0
    yRotate = -math.degrees(math.atan2(accel_xout_scaled, (math.sqrt((accel_yout_scaled * accel_yout_scaled) +
                                                                             (accel_zout_scaled * accel_zout_scaled)))))
    xRotate = -math.degrees(math.atan2(accel_yout_scaled, (math.sqrt((accel_xout_scaled * accel_xout_scaled) +
                                                                             (accel_zout_scaled * accel_zout_scaled)))))


def headlight():  # function for handling button presses

    global headlightpressed

    if headlightpressed == 0:  # headlight button
        i2cBus.write_byte_data(tailEndPicAddress, 2, True)
        i2cBus.write_byte_data(tailEndPicAddress, 3, True)

    else:
        i2cBus.write_byte_data(tailEndPicAddress, 2, False)
        i2cBus.write_byte_data(tailEndPicAddress, 3, False)


def rightturn():

    global rightpressed

    if leftpressed == 0:  # left signal button
        i2cBus.write_byte_data(tailEndPicAddress, 1, True)
        rightpressed = 1

    else:
        rightpressed = 0
        i2cBus.write_byte_data(tailEndPicAddress, 1, False)


def leftturn():

    global leftpressed

    if leftpressed == 0:  # left signal button
        i2cBus.write_byte_data(tailEndPicAddress, 0, True)
        leftpressed = 1

    else:
        leftpressed = 0
        i2cBus.write_byte_data(tailEndPicAddress, 0, False)


def brake():

    global brakepressed

    if brakepressed == 0:  # brake signal button
        brakepressed = 1
        i2cBus.write_byte_data(tailEndPicAddress, 5, True)
    else:
        brakepressed = 0
        i2cBus.write_byte_data(tailEndPicAddress, 5, False)


mainWindow = tk.Tk()
mainWindow.title('Byke')
mainWindow.geometry('480x300+0+0')
mainWindow.columnconfigure(0, weight=1)
mainWindow.columnconfigure(1, weight=1)
mainWindow.columnconfigure(2, weight=1)
mainWindow.rowconfigure(0, weight=1)
mainWindow.rowconfigure(1, weight=1)
mainWindow.rowconfigure(2, weight=1)
mainWindow.config(bg='white')

leftturnbutton = tk.Button(mainWindow, text='Left Turn', borderwidth=2, command=leftturn)  # left turn signal button
leftturnbutton.grid(row=0, column=0, sticky='nswe')

rightturnbutton = tk.Button(mainWindow, text='Right Turn', borderwidth=2, command=rightturn)  # right turn signal button
rightturnbutton.grid(row=0, column=1, sticky='nswe')

brakebutton = tk.Button(mainWindow, text='Brake', borderwidth=2, command=brake)  # brake button
brakebutton.grid(row=0, column=2, sticky='nswe')

headlightbutton = tk.Button(mainWindow, text='Headlight', borderwidth=2, command=headlight)  # headlight button
headlightbutton.grid(row=1, column=0, sticky='nswe')

gpsbutton = tk.Button(mainWindow, text='gps', borderwidth=2, command=gps)  # headlight button
gpsbutton.grid(row=2, column=0, sticky='nswe')

if recordrunning == 1:
    gpsbutton.after(1000, gps)

temperaturebutton = tk.Button(mainWindow, text='temp', borderwidth=2, command=temperatureread)  # headlight button
temperaturebutton.grid(row=2, column=1, sticky='nswe')

mainWindow.mainloop()


