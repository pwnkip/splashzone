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

tSample = 90  # take samples this often (seconds)
tempLimit = 95 # turn off heater if above this temp (C)
pressLimit = 1  # turn off heater if below this pressure (psi)
DWLimit = 1.5  #turn off heater if above this voltage (v)

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

#calibraion table: (coefficient, offset)
cals = [(.78,-0.2),  # HP
        (1.05,0.13),  # LP1
        (1.06,0.82),  # LP2
        (1,0),  # DW
        (1.01,3.95),  # TC1
        (1.01,3.94),  # TC2
        (1.01,4.65),  # TC3
        (1.01,3.85)]  # TC4

# create DAQ
DAC0_REGISTER = 5000
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

    # Calibrate data
    calData = [scaledData[i]*cals[i][0]+cals[i][1] for i in range(len(scaledData))]


    # add timestamp
    data = [time.time()]+calData

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

    #Limit Check
    if (data[1]>pressLimit and data[2]>pressLimit and data[3]>pressLimit and
        data[4]<DWLimit and
        data[5]<tempLimit and data[6]<tempLimit and data[7]<tempLimit and data[8]<tempLimit):
        d.writeRegister(DAC0_REGISTER, 5) # Set DAC0 to 5 V, turn on heater
    else:
        d.writeRegister(DAC0_REGISTER, 0) # Set DAC0 to 0 V, turn off heater
        print('limit exceeded, heater disabled!')

    time.sleep(tSample)
