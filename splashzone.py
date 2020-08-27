# Logs data from splashzone sensors. Takes one argument of log file name.
# Will append to logfile if name already exists.

import sys
import u3
import time
from csv import writer
import paho.mqtt.publish as publish

#parse argument as filename (test title)
filename = sys.argv[1]

# register numbers
HPreg = 0
LPreg = [1,2]
DWreg = 3
TCreg = [4,5,6,7]

tSample = 60  # take samples this often (seconds)

print('Starting test '+filename+'...')

# Setup Thingspeak
channelID = "1119567"
writeAPIKey = "G4S8A66J30PLWPPS"
mqttHost = "mqtt.thingspeak.com"
mqttUsername = "splashzone"
mqttAPIKey = "G3TR6RV7VOHBN0T6"
tTransport = "websockets"
tPort = 80
topic = "channels/" + channelID + "/publish/" + writeAPIKey


# create DAQ
d=u3.U3()
d.configIO(FIOAnalog = 0xff)

while True:
    # read registers
    newData = [d.getAIN(i) for i in range(0,8)]

    # scale data
    scaledData = [0]*8  # create empty array
    # HP high-pressure sensor 0-100psi on 0.5-4.5v
    scaledData[HPreg] = 100*(newData[HPreg]-0.5)/(4.5-0.5)
    # LP low-pressure sensors 0-30psi on 0.5-4.5v
    for reg in LPreg:
        scaledData[reg] = 30*(newData[reg]-0.5)/(4.5-0.5)
    # TC for thermocouples, scale to C from amplifier datasheet
    for reg in TCreg:
        scaledData[reg] = (newData[reg]-1.25)/0.005
    # DW don't scale drip wire
    scaledData[DWreg] = newData[DWreg]

    # add timestamp
    data = [time.time()]+scaledData

    # append to csv
    with open ("data/"+filename+".csv",'a') as logfile:                            
        logWriter = writer(logfile, delimiter=',')
        logWriter.writerow(data) 

    print('logged locally: ',data)

    # Send to Thingspeak
    payload = "field1=" + str(data[1]) + "&field2=" + str(data[2]) + "&field3=" + str(data[3]) + "&field4=" + str(data[4]) + "&field5=" + str(data[5]) + "&field6=" + str(data[6]) + "&field7=" + str(data[7]) + "&field8=" + str(data[8])
    try:
        publish.single(topic, payload, hostname=mqttHost, transport=tTransport, port=tPort,auth={'username':mqttUsername,'password':mqttAPIKey})
        print("successfuly uploaded")
    except:
        print ("There was an error while publishing the data.")

    time.sleep(tSample)