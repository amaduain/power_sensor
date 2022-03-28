# Reading PZEM-004t power sensor (new version v3.0) through Modbus-RTU protocol over TTL UART
# Run as:
# python3 pzem_004t.py

# To install dependencies: 
# pip install modbus-tk
# pip install pyserial

import serial
import time
import modbus_tk.defines as cst
from modbus_tk import modbus_rtu

import pymodbus

from pymodbus.pdu import ModbusRequest
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from pymodbus.transaction import ModbusRtuFramer


# Connect to the sensor
sensor = serial.Serial(
                       port='/dev/ttyUSB0',
                       baudrate=9600,
                       bytesize=8,
                       parity='N',
                       stopbits=1,
                       xonxoff=0
                      )

master = modbus_rtu.RtuMaster(sensor)
master.set_timeout(2.0)
master.set_verbose(True)
try:
    while True:
        data = master.execute(1, cst.READ_INPUT_REGISTERS, 0, 10)

        voltage = data[0] / 10.0 # [V]
        current = (data[1] + (data[2] << 16)) / 1000.0 # [A]
        power = (data[3] + (data[4] << 16)) / 10.0 # [W]
        energy = data[5] + (data[6] << 16) # [Wh]
        frequency = data[7] / 10.0 # [Hz]
        powerFactor = data[8] / 100.0
        alarm = data[9] # 0 = no alarm

        print('Voltage [V]: ', voltage)
        print('Current [A]: ', current)
        print('Power [W]: ', power) # active power (V * I * power factor)
        print('Energy [Wh]: ', energy)
        print('Frequency [Hz]: ', frequency)
        print('Power factor []: ', powerFactor)
        print('Alarm : ', alarm)
        time.sleep(1)
    # Changing power alarm value to 100 W
    # master.execute(1, cst.WRITE_SINGLE_REGISTER, 1, output_value=100)
except KeyboardInterrupt:
        print("Power measurement finished.")

try:
    master.close()
    if sensor.is_open:
        sensor.close()
    #RESET POWER COUNTER EXAMPLE
    client = ModbusClient (method = "rtu", port="/dev/ttyUSB0", stopbits = 1, bytesize = 8, parity = 'N', baudrate = 9600)
    if client.connect ():
        try:
            # Reset energy count
            # 0x01 Slave address
            # 0x42 Magic code
            # 0x80 CRC for slave address (0x01)
            # 0x11 CRC for magic code (0x42)         
            data = [0x01, 0x42, 0x80, 0x11]
            print(client.send(data))
        finally:
            client.close()
except:
    pass
