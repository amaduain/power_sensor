from ast import Global
import logging
from logging.handlers import RotatingFileHandler
from netifaces import interfaces, ifaddresses, AF_INET
from PyAccessPoint import pyaccesspoint
from flask import Flask, render_template, request, jsonify, Response
import multiprocessing
import os
import subprocess
import json
import sys
import time
import signal
from wifi import Cell,Scheme


##############################
#        GLOBAL VARS         #
##############################

LOG_LEVEL = logging.INFO
AP_IP = "192.168.100.1"
AP_NETMASK = "255.255.255.0"
AP_SSID = "POWER_WLAN"
AP_PASSWORD = "POWER_WLAN"
AP_PORT = "80"
INTERFACE = 'wlan0'
#INTERFACE = 'eth0'
IP_FILE = "last_ip.json"
SSID = ""
SSID_PASSWORD = ""
CONFIG_STOP = False
WPA_SUPPLICANT_FILE = "/etc/wpa_supplicant/wpa_supplicant.conf"

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

def check_interface(if_name):
    addr = ifaddresses(if_name)
    if AF_INET in addr:
        return addr[AF_INET][0]
    else:
        return None

def store_ip_info(ip_info):
    with open(IP_FILE,"w") as ip_file:
        json.dump(ip_info, ip_file)

def get_ip_info():
    with open(IP_FILE) as ip_file:
        ip_info = json.load(ip_file)
    return ip_info

def create_access_point():
    ap = pyaccesspoint.AccessPoint(
                                        wlan=INTERFACE,
                                        ip=AP_IP,
                                        inet=None,
                                        ssid=AP_SSID,
                                        netmask=AP_NETMASK,
                                        password=AP_PASSWORD
                                    )
    ap.start()
    return ap

def clean_ips():
    lines = subprocess.Popen(["ip", "addr", "show", "dev", INTERFACE],stdout=subprocess.PIPE).communicate()[0].splitlines()
    for line in lines:
        if str(line).find("inet") > -1:
            subprocess.Popen(["ip", "addr", "del", line.split()[1], "dev", INTERFACE])

config_app = Flask(__name__)
@config_app.route("/", methods=['GET', 'POST'])
def index():
    global SSID
    global SSID_PASSWORD
    error = False
    if os.path.isfile("errorfile"):
        error = True
        os.remove("errorfile") 
    if request.method == 'GET':
        return render_template("configure.html",error=error)
    if request.method == 'POST':
        SSID = request.form.get('ssid')
        SSID_PASSWORD = request.form.get('password')
        logger.info("Wifi form submitted.")
        logger.info(f"SSID: {SSID}")
        logger.info(f"Password: {SSID_PASSWORD}")
        creds = {'ssid': SSID, 'pass': SSID_PASSWORD}
        with open("creds","w") as creds_file:
            json.dump(creds, creds_file)
        with open("stopfile","w") as stop_file:
            stop_file.close()
        return render_template("message.html")
    return render_template("configure.html",error=error)

@config_app.get("/message")
def message():
    return render_template("message.html")

confirm_app = Flask(__name__)
@confirm_app.route("/", methods=['GET', 'POST'])
def confirm_index():
        ip = get_ip_info()
        return render_template("confirm.html",ip=ip["addr"])
@confirm_app.route("/restart", methods=['GET', 'POST'])
def restart():
    with open("stopfile","w") as stop_file:
            stop_file.close()
    return render_template("end.html",ip=ip["addr"])

    
if __name__ == "__main__":
    logger, log_handler = create_logger("./log/wifi.log",LOG_LEVEL)
    logger.info("Starting wifi AP configuration daemon.")
    logger.info("Checking actual IP for WLAN0")
    ip = check_interface(INTERFACE)
    ap = None
    try:
        if ip is None:
            logger.info("WLAN interface has no IP, starting AP")
            ap = create_access_point()
            proc = multiprocessing.Process(target=config_app.run, kwargs={"host": AP_IP,"port": AP_PORT})
            proc.start()
            while True:
                if os.path.isfile("stopfile"):
                    logger.info("Stopping All...")
                    os.kill(proc.pid, signal.SIGKILL) 
                    logger.info("All Stopped")
                    with open("creds") as cred_file:
                        creds = json.load(cred_file)
                    os.remove("creds") 
                    os.remove("stopfile")
                    break
                time.sleep(5)
            logger.info("Credentials entered:")
            logger.info(f"SSID: {creds['ssid']}")
            logger.info(f"Password: {creds['pass']}")
            logger.info("Stopping ap...")
            ap.stop()
            logger.info("Configuring wifi")
            wpa_suplicant_file=[]
            wpa_suplicant_file.append("country=ES")
            wpa_suplicant_file.append("ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev")
            wpa_suplicant_file.append("network={")
            wpa_suplicant_file.append('     ssid="' + creds["ssid"] + '"')
            wpa_suplicant_file.append('     psk="' + creds["pass"] + '"')
            wpa_suplicant_file.append("     key_mgmt=WPA-PSK")
            wpa_suplicant_file.append("}")
            wpa_suplicant_file.append("")
            with open(WPA_SUPPLICANT_FILE,"w") as wpa_file:
                wpa_file.write("\n".join(wpa_suplicant_file))
            os.system("sudo systemctl restart networking")
            ip = check_interface(INTERFACE)
            if ip is None:
                logger.error("Unable to get IP!")
                with open("errorfile","w") as errorfile:
                    errorfile.close()
                wpa_suplicant_file=[]
                wpa_suplicant_file.append("country=ES")
                wpa_suplicant_file.append("ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev")
                wpa_suplicant_file.append("")
                with open(WPA_SUPPLICANT_FILE,"w") as wpa_file:
                    wpa_file.write("\n".join(wpa_suplicant_file))
                logger.error("Rebooting system")
                os.system("sudo reboot now")
            else:
                store_ip_info(ip)
                ap.start()
                proc = multiprocessing.Process(target=confirm_app.run, kwargs={"host": AP_IP,"port": AP_PORT})
                proc.start()
                while True:
                    if os.path.isfile("stopfile"):
                        logger.info("Stopping All...")
                        os.kill(proc.pid, signal.SIGKILL) 
                        logger.info("All Stopped")
                        os.remove("stopfile")
                        break
                    time.sleep(5)
                os.kill(proc.pid, signal.SIGKILL) 
                ap.stop()
                os.system("sudo systemctl restart networking")
        else:
            #Try to check the IP from file.
            if os.path.isfile(IP_FILE):
                logger.info("IP file data found.")
                stored_ip = get_ip_info()
                if stored_ip == ip:
                    logger.info("IP is the same as before, nothing to do.")
                    logger.info("Ending program")
                    sys.exit(0)
                else:
                    #Create the file, start the AP Mode and wait for confirmation.
                    logger.info("New addess found, wait for the user to confirm IP")
                    logger.info(ip)
                    store_ip_info(ip)
                    ap = create_access_point()
                    proc = multiprocessing.Process(target=confirm_app.run, kwargs={"host": '0.0.0.0',"port": AP_PORT})
                    proc.start()
                    while True:
                        if os.path.isfile("stopfile"):
                            logger.info("Stopping All...")
                            os.kill(proc.pid, signal.SIGKILL) 
                            logger.info("All Stopped")
                            os.remove("stopfile")
                            break
                        time.sleep(5)
                    os.kill(proc.pid, signal.SIGKILL) 
                    ap.stop()
                    os.system("sudo systemctl restart networking")
    finally:
        if ap is not None:
            if ap.is_running():
                ap.stop()
                clean_ips()

