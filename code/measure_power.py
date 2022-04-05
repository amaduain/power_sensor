import pymodbus
import serial
import math
import time
import logging
from logging.handlers import RotatingFileHandler
from datetime import date, datetime
import pytz
from pymodbus.pdu import ModbusRequest
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from pymodbus.transaction import ModbusRtuFramer
from influxdb import InfluxDBClient
import string
import random

##GLOBAL VARIABLES####

power_db_name = "power"
sessions_db_name = "sessions"
usb_port = "/dev/ttyUSB0"
log_level = logging.INFO
interval = 10 #Seconds


#### FUNCTIONS #####

def random_string(length):
    return ('S01' + ''.join(random.choice(string.ascii_letters) for m in range(length))).upper()

def start_session(current_energy, timestamp):
    session = {}
    session["start_energy"] = current_energy
    session["start_time"] = timestamp
    session["total_energy"] = 0
    session["session_id"] = random_string(24)
    return session


def create_db(db_name):
    client = InfluxDBClient(host='localhost', port=8086)
    db_list = client.get_list_database()
    for db in db_list:
        if db['name'] == db_name:
            logger.debug(f"Database {db_name} already exists, skipping creation")
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
    #logger.addHandler(console)
    return logger, log_handler

def reset_energy(usb_client):
    data = [0x01, 0x42, 0x80, 0x11]
    usb_client.send(data)
    time.sleep(1)

def format_duration(hours, minutes, seconds):
    duration = ""
    if hours > 0:
        duration = str(hours) + "h"
    if len(duration) > 0:
           duration = duration + " " + str(minutes) + "m"
    else:
        if minutes > 0:
           duration = str(minutes) + "m"
    if len(duration) > 0:
        duration = duration + " "
    duration = duration + str(seconds) + "s"
    return duration



if __name__ == '__main__':
    logger, log_handler = create_logger("./log/power.log",log_level)
    logger.info("Starting power measurements...")
    logger.debug("Creating USB connection client.")
    usb_client = ModbusClient (method = "rtu", port=usb_port, stopbits = 1, bytesize = 8, parity = 'N', baudrate = 9600)
    logger.debug("Configuring DB")
    create_db(power_db_name)
    create_db(sessions_db_name)
    power_db_client = InfluxDBClient(host='localhost', port=8086,database=power_db_name)
#Connect to the serial modbus server
#connection = client.connect()
    logger.debug("Starting infinite loop")
    in_session = False
    timestamp = datetime.utcnow().replace(tzinfo=pytz.utc)
    cet_date = timestamp.astimezone(pytz.timezone('Europe/Madrid'))
    working_day = cet_date.day
    sleeptime = 60 - datetime.utcnow().second
    #Sync the time to start at 0s
    time.sleep(sleeptime)
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
                    timestamp = datetime.utcnow().replace(tzinfo=pytz.utc)
                    cet_date = timestamp.astimezone(pytz.timezone('Europe/Madrid'))
                    result = usb_client.read_input_registers (0x0000, 10, unit = 0x01)
                    data = result.registers
                    voltage = data[0] / 10.0 # [V]
                    current = (data[1] + (data[2] << 16)) / 1000.0 # [A]
                    power = (data[3] + (data[4] << 16)) / 10.0 # [W]
                    energy = data[5] + (data[6] << 16) # [Wh]
                    frequency = data[7] / 10.0 # [Hz]
                    powerFactor = data[8] / 100.0
                    alarm = data[9] # 0 = no alarm
                    if working_day != cet_date.day:
                        #Reseting counter
                        logger.info("Resesting day Energy counter.")
                        if in_session:
                            session["total_energy"] = energy - session["start_energy"]
                            session["start_energy"] = 0
                        reset_energy(usb_client)
                        working_day = cet_date.day
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
                    power_db_client.write_points(json_body)
                    if not in_session:
                        if power > 10:
                            in_session = True
                            session = start_session(energy, timestamp)
                            logger.info(f"Charging session started at: {timestamp.isoformat()}")
                            cet_start_date = session["start_time"].astimezone(pytz.timezone('Europe/Madrid'))
                            session_start_date = cet_start_date.strftime("%m/%d/%Y")
                            session_start_time = cet_start_date.strftime("%I:%M:%S %p")
                            session_id  = session["session_id"]
                            logger.info(f"Session start date: {session_start_date}")
                            logger.info(f"Session start time: {session_start_time}")
                            logger.info(f"Session Id: {session_id}")
                            session_json_body = [
                                    {
                                        "measurement": "ev_session",
                                        "tags": {
                                            "user": "Alex"
                                        },
                                        "time": session["start_time"].isoformat(),
                                        "fields": {
                                            "start_date": session_start_date,
                                            "start_time": session_start_time,
                                            "session_id": session_id
                                        }
                                    }
                                ]
                            sessions_db_client = InfluxDBClient(host='localhost', port=8086,database=sessions_db_name)
                            sessions_db_client.write_points(session_json_body)
                            sessions_db_client.close()
                    if in_session:
                        if power < 10:
                            in_session = False
                            logger.info(f"Charging session ended at: {timestamp.isoformat()}")
                            end_timestamp = datetime.utcnow().replace(tzinfo=pytz.utc)
                            cet_start_date = session["start_time"].astimezone(pytz.timezone('Europe/Madrid'))
                            cet_end_date = end_timestamp.astimezone(pytz.timezone('Europe/Madrid'))
                            session_start_date = cet_start_date.strftime("%m/%d/%Y")
                            session_start_time = cet_start_date.strftime("%I:%M:%S %p")
                            session_end_time = cet_end_date.strftime("%I:%M:%S %p")
                            session_energy = session["total_energy"] + energy - session["start_energy"]
                            session_delta = end_timestamp - session["start_time"]
                            session_id  = session["session_id"]
                            hours, remainder = divmod(session_delta.seconds, 3600)
                            minutes, seconds = divmod(remainder, 60)
                            session_duration = format_duration(hours, minutes, seconds)
                            logger.info(f"Session start date: {session_start_date}")
                            logger.info(f"Session start time: {session_start_time}")
                            logger.info(f"Session end time: {session_end_time}")
                            logger.info(f"Energy: {session_energy}")
                            logger.info(f"Duration: {session_duration}")
                            logger.info(f"Session Id: {session_id}")
                            session_json_body = [
                                    {
                                        "measurement": "ev_session",
                                        "tags": {
                                            "user": "Alex"
                                        },
                                        "time": session["start_time"].isoformat(),
                                        "fields": {
                                            "start_date": session_start_date,
                                            "start_time": session_start_time,
                                            "end_time": session_end_time,
                                            "energy": session_energy,
                                            "duration": session_duration,
                                            "session_id": session_id
                                        }
                                    }
                                ]
                            sessions_db_client = InfluxDBClient(host='localhost', port=8086,database=sessions_db_name)
                            sessions_db_client.write_points(session_json_body)
                            sessions_db_client.close()
                            session={}
                            logger.info("Session Added successfully.")
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
                    time.sleep(interval)
                    #time.sleep(1)
                    #print(result.registers)
                    #print (calc (result.registers[5:7], 1) + 'Wh')
            else: 
                logger.error("USB Serial port not connected, trying in 10 seconds...")
                time.sleep(10)
    except KeyboardInterrupt:
        logger.info("Power measurement finished.")
    finally:
        power_db_client.close()
        usb_client.close()


