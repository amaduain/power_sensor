import pymodbus
import serial
import math
import time
import logging
from datetime import datetime

from pymodbus.pdu import ModbusRequest
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from pymodbus.transaction import ModbusRtuFramer

usb_port = "/dev/ttyUSB0"

def create_logger(log_file_name):
    """
        Create the logger for the script.

       :returns: logger, log_handler Objects properly configured.
       :rtype: tuple
    """
    logger = logging.getLogger()
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    log_handler = RotatingFileHandler(log_file_name, maxBytes=20000000,
                                      backupCount=5)
    log_level = logging.INFO
    log_handler.setFormatter(formatter)
    logger.setLevel(log_level)
    # Enable the screen logging.
    logger.addHandler(log_handler)
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    logger.addHandler(console)
    return logger, log_handler



if __name__ == '__main__':
    logger, log_handler = create_logger("./log/power.log")
    logger.info("Starting power measurements...")
    logger.debug("Creating USB connection client.")
    client = ModbusClient (method = "rtu", port=usb_port, stopbits = 1, bytesize = 8, parity = 'N', baudrate = 9600)
    
#Connect to the serial modbus server
#connection = client.connect()
    logger.debug("Starting infinite loop")
    try: 
        while True:
            if client.connect():
            
                    # Reset energy count
                    # 0x01 Slave address
                    # 0x42 Magic code
                    # 0x80 CRC for slave address (0x01)
                    # 0x11 CRC for magic code (0x42)         
                # data = [0x01, 0x42, 0x80, 0x11]
                # print(client.send(data))
                    #time.sleep(2)
                    result = client.read_input_registers (0x0000, 10, unit = 0x01)
                    data = result.registers
                    voltage = data[0] / 10.0 # [V]
                    current = (data[1] + (data[2] << 16)) / 1000.0 # [A]
                    power = (data[3] + (data[4] << 16)) / 10.0 # [W]
                    energy = data[5] + (data[6] << 16) # [Wh]
                    frequency = data[7] / 10.0 # [Hz]
                    powerFactor = data[8] / 100.0
                    alarm = data[9] # 0 = no alarm
                    logger.debug(f'Voltage [V]: {voltage}')
                    logger.debug(f'Current [A]: {current}')
                    logger.debug(f'Power [W]: {power}') # active power (V * I * power factor)
                    logger.debug(f'Energy [Wh]: {energy}')
                    logger.debug(f'Frequency [Hz]: {frequency}')
                    logger.debug(f'Power factor []: {powerFactor}')
                    logger.debug(f'Alarm : {alarm}')
                    #Set a read per minute for now
                    sleeptime = 10 - datetime.utcnow().second
                    time.sleep(sleeptime)
                    #time.sleep(1)
                    #print(result.registers)
                    #print (calc (result.registers[5:7], 1) + 'Wh')
            else: 
                logger.error("USB Serial port not connected, trying in 10 seconds...")
                time.sleep(10)
    except KeyboardInterrupt:
        logger.info("Power measurement finished.")
    finally:
        client.close()

