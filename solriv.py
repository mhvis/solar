#!/usr/bin/python

# solriv.py
# PVOutput uploader for Samil Power Solar River4000TL-D
# May work with other inverters

import sys
import socket
import struct
import time
import datetime
import subprocess
import syslog

# Get these from PVOutput.org
apiKey = "insert your api key here"
systemId = "enter your system id here"

def DebugMessage(message):
    syslog.syslog("solriv: " + message)

def BroadcastMessage(interfaceip):
    DebugMessage("Sending broadcast")
    UDPPORT = 1300
    MESSAGE = "\x55\xaa\x00\x40\x02\x00\x0bI AM SERVER\x04\x3a"
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if(interfaceip != ""):
        s.bind((interfaceip, 0))
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.connect(("<broadcast>", UDPPORT))
    s.send(MESSAGE)
    s.close()

def SetUpConnection(waittime):
    DebugMessage("Setting up connection")
    TCPPORT = 1200
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', TCPPORT))
    s.settimeout(waittime)
    s.listen(1)
    return s

def WaitForConnection(s):
    DebugMessage("Waiting for connection")
    try:
        news, address = s.accept()
        DebugMessage("Connected to: " + str(address))
        news.setblocking(1)
    except socket.timeout:
        news = None
    return news

def RequestData(s):
    #DebugMessage("Sending request")
    REQUEST="\x55\xaa\x01\x02\x02\x00\x00\x01\x04"
    s.send(REQUEST)

def ReceiveData(s):
    #DebugMessage("Waiting for data")
    try:
        s.settimeout(5.0)
        data = s.recv(1024)
    except socket.timeout:
        #DebugMessage("None received")
        data = ""
    if (len(data) < 63 or data[0:4] != "\x55\xaa\x01\x82"):
        if (len(data) > 0):
            DebugMessage("Bad data")
            DebugMessage("Received: " + ' '.join(x.encode('hex') for x in data))
        return None
    else:
        #DebugMessage("Data received")
        dataentries = data[7:]
        try:
            entries = struct.unpack_from('!hhhhhhhhhhhhhhhhhhhhhhhhhhhh', dataentries)
            internaltemp = entries[0] / 10.0
            pv1voltage = entries[1] / 10.0
            pv2voltage = entries[2] / 10.0
            pv1current = entries[3] / 10.0
            pv2current = entries[4] / 10.0
            hoursoperational = entries[6]
            energytoday = entries[8] * 10.0
            pv1inputpower = entries[19]
            pv2inputpower = entries[20]
            gridcurrent = entries[21] / 10.0
            gridvoltage = entries[22] / 10.0
            gridfreq = entries[23] / 100.0
            outputpower = entries[24]
            energytotal = entries[26] * 100.0
            currenttime = datetime.datetime.now()
            #DebugMessage("currenttime: " + str(currenttime))
            #DebugMessage("internaltemp: " + str(internaltemp))
            #DebugMessage("outputpower: " + str(outputpower))
            #DebugMessage("energytoday: " + str(energytoday))
            return (currenttime, internaltemp, outputpower, energytoday)
        except struct.error:
            DebugMessage("struct.error")
            return None

def SendData(data, starttime):
    # TODO: send on 5-minute boundary
    timedeltas = datetime.timedelta()
    internaltemp = 0
    outputpower = 0
    for entry in data:
        timedeltas += entry[0] - starttime
        internaltemp += entry[1]
        outputpower += entry[2]
        energytoday = entry[3]
    midtime = starttime + (timedeltas / len(data))
    middatestring = midtime.strftime("%Y%m%d")
    midtimestring = midtime.strftime("%H:%M")
    internaltemp /= len(data)
    outputpower /= len(data)

    curlargs = ["curl",]
    curlargs += ["-s",]
    curlargs += ["-S",]
    #curlargs += ["-v",]
    curlargs += ["-d", "d=" + middatestring]
    curlargs += ["-d", "t=" + midtimestring]
    curlargs += ["-d", "v1=" + str(energytoday)]
    curlargs += ["-d", "v2=" + str(outputpower)]
    if (internaltemp != 0.0):
        curlargs += ["-d", "v5=" + str(internaltemp)]
    curlargs += ["-H", "X-Pvoutput-Apikey: " + apiKey]
    curlargs += ["-H", "X-Pvoutput-SystemId: " + systemId]
    curlargs += ["http://pvoutput.org/service/r2/addstatus.jsp",]

    subprocess.call(curlargs)

interfaceip=""
if(len(sys.argv) == 2):
    interfaceip=sys.argv[1]

listensocket = SetUpConnection(20.0)
runningdata = ()
starttime = datetime.datetime.now()
while True:
    s = None
    while(s == None):
        BroadcastMessage(interfaceip)
        s = WaitForConnection(listensocket)
        time.sleep(1)

    try:
        lastdatatime = datetime.datetime.now()
        while(True):
            RequestData(s)
            newdata = ReceiveData(s)
            if (newdata != None):
                lastdatatime = datetime.datetime.now()
                runningdata += (newdata,)
                if ((runningdata[-1][0] - starttime).seconds > 5 * 60):
                    if (runningdata[0][2] > 0 or runningdata[-1][2] > 0):
                        # Power has been generated, so upload.
                        SendData(runningdata, starttime)
                    runningdata = ()
                    starttime = datetime.datetime.now()
                time.sleep(10)
            else:
                #DebugMessage("Data last received: " + str(lastdatatime))
                if ((datetime.datetime.now() - lastdatatime).seconds > 10 * 60):
                    DebugMessage("No data received for 10 minutes; reconnecting.")
                    break
                time.sleep(1)
    except socket.error as e:
        print(e)
        if (e.strerror is None):
                DebugMessage("Socket error")
        else:
                DebugMessage("Socket error: " + e.strerror)
