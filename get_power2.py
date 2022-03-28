import pymodbus
import serial
import math
import time

from pymodbus.pdu import ModbusRequest
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from pymodbus.transaction import ModbusRtuFramer


def calc (registers, factor):
    format = '%%0.%df' % int (math.ceil (math.log10 (factor)))
    if len(registers) == 1:
        return format % ((1.0 * registers[0]) / factor)
    elif len(registers) == 2:
        return format % (((1.0 * registers[1] * 65535) + (1.0 * registers[0])) / factor)


client = ModbusClient (method = "rtu", port="/dev/ttyUSB0", stopbits = 1, bytesize = 8, parity = 'N', baudrate = 9600)

#Connect to the serial modbus server
connection = client.connect()
if client.connect ():
        try:
            # Reset energy count
            # 0x01 Slave address
            # 0x42 Magic code
            # 0x80 CRC for slave address (0x01)
            # 0x11 CRC for magic code (0x42)         
           # data = [0x01, 0x42, 0x80, 0x11]
           # print(client.send(data))
            #time.sleep(2)
            data = client.read_input_registers (0x0000, 10, unit = 0x01)
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
            #time.sleep(1)
            #print(result.registers)
            #print (calc (result.registers[5:7], 1) + 'Wh')
        finally:
            client.close()

