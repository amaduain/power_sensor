import pymodbus
import serial
import math
import time
import logging
from logging.handlers import RotatingFileHandler
from datetime import date, datetime
from pymodbus.pdu import ModbusRequest
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from pymodbus.transaction import ModbusRtuFramer
from influxdb import InfluxDBClient


##GLOBAL VARIABLES####

db_name = "power"
usb_port = "/dev/ttyUSB0"
log_level = logging.DEBUG


#### FUNCTIONS #####

def create_db(db_name):
    client = InfluxDBClient(host='localhost', port=8086)
    db_list = client.get_list_database()
    for db in db_list:
        if db['name'] == db_name:
            print(f"Database {db_name} already exists, skipping creation")
            return
    client.create_database(db_name)


def create_logger(log_file_name, log_level):
    """
        Create the logger for the script.

       :returns: logger, log_handler Objects properly configured.
       :rtype: tuple
    """
    logger = logging.getLogger()
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    log_handler = RotatingFileHandler(log_file_name, maxBytes=20000000,
                                      backupCount=5)
    log_handler.setFormatter(formatter)
    logger.setLevel(log_level)
    # Enable the screen logging.
    logger.addHandler(log_handler)
    console = logging.StreamHandler()
    console.setLevel(log_level)
    logger.addHandler(console)
    return logger, log_handler



if __name__ == '__main__':
    logger, log_handler = create_logger("./log/power.log",log_level)
    logger.info("Starting power measurements...")
    logger.debug("Creating USB connection client.")
    usb_client = ModbusClient (method = "rtu", port=usb_port, stopbits = 1, bytesize = 8, parity = 'N', baudrate = 9600)
    logger.debug("Configuring DB")
    create_db(db_name)
    db_client = InfluxDBClient(host='localhost', port=8086,database=db_name)
#Connect to the serial modbus server
#connection = client.connect()
    logger.debug("Starting infinite loop")
    try: 
        while True:
            if usb_client.connect():
            
                    # Reset energy count
                    # 0x01 Slave address
                    # 0x42 Magic code
                    # 0x80 CRC for slave address (0x01)
                    # 0x11 CRC for magic code (0x42)         
                # data = [0x01, 0x42, 0x80, 0x11]
                # print(client.send(data))
                    #time.sleep(2)
                    timestamp = datetime.now()
                    result = usb_client.read_input_registers (0x0000, 10, unit = 0x01)
                    data = result.registers
                    voltage = data[0] / 10.0 # [V]
                    current = (data[1] + (data[2] << 16)) / 1000.0 # [A]
                    power = (data[3] + (data[4] << 16)) / 10.0 # [W]
                    energy = data[5] + (data[6] << 16) # [Wh]
                    frequency = data[7] / 10.0 # [Hz]
                    powerFactor = data[8] / 100.0
                    alarm = data[9] # 0 = no alarm
                    json_body = [
                                    {
                                        "measurement": "ev_power",
                                        "tags": {
                                            "user": "Alex"
                                        },
                                        "time": timestamp.isoformat(),
                                        "fields": {
                                            "voltage": voltage,
                                            "current": current,
                                            "power": power,
                                            "energy": energy,
                                            "frequency": frequency,
                                            "powerFactor": powerFactor
                                        }
                                    }
                                ]
                    db_client.write_points(json_body)
                    logger.debug(f"DB Object: {json_body}")
                    logger.debug(f'Voltage [V]: {voltage}')
                    logger.debug(f'Current [A]: {current}')
                    logger.debug(f'Power [W]: {power}') # active power (V * I * power factor)
                    logger.debug(f'Energy [Wh]: {energy}')
                    logger.debug(f'Frequency [Hz]: {frequency}')
                    logger.debug(f'Power factor []: {powerFactor}')
                    logger.debug(f'Alarm : {alarm}')
                    #Set a read per minute for now
                    #sleeptime = 60 - datetime.utcnow().second
                    sleeptime = 10
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
        db_client.close()
        usb_client.close()


