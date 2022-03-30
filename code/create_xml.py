import logging
import pytz
import jinja2
from datetime import datetime, timedelta
from influxdb import InfluxDBClient
from dateutil.relativedelta import relativedelta


##GLOBAL VARIABLES####
sessions_db_name = "sessions"
log_level = logging.INFO
template_file = "template.xml"

def create_logger(log_level):
    """
        Create the logger for the script.

       :returns: logger, log_handler Objects properly configured.
       :rtype: tuple
    """
    logger = logging.getLogger()
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    #log_handler = RotatingFileHandler(log_file_name, maxBytes=20000000,
    #                                  backupCount=5)
    #log_handler.setFormatter(formatter)
    logger.setLevel(log_level)
    # Enable the screen logging.
    #logger.addHandler(log_handler)
    console = logging.StreamHandler()
    console.setLevel(log_level)
    console.setFormatter(formatter)
    logger.addHandler(console)
    return logger


if __name__ == '__main__':
    logger = create_logger(log_level)
    logger.info("Starting XML Creation...")
    query = 'select *  from ev_sessions;'
    # Using the actual month for now....
    timestamp = datetime.utcnow().replace(tzinfo=pytz.utc)
    cet_date = timestamp.astimezone(pytz.timezone('Europe/Madrid'))
    month_start = cet_date.replace(day=1,hour=0,minute=0,second=0,microsecond=0)
    month_end = month_start + relativedelta(months=1)
    month_end = month_end + relativedelta(seconds=-1)
    logger.info(f"First day of month: {month_start}")
    logger.info(f"Last day of month: {month_end}")
    client = InfluxDBClient(host='localhost', port=8086,database=sessions_db_name)
    utc_month_start = month_start.astimezone(pytz.timezone('UTC'))
    utc_mont_end = month_end.astimezone(pytz.timezone('UTC'))
    query = f'SELECT * FROM "ev_session" WHERE time > \'{utc_month_start.strftime("%Y-%m-%d %H:%M:%S")}\' AND time <\'{utc_mont_end.strftime("%Y-%m-%d %H:%M:%S")}\''
    result = client.query(query)
    templateLoader = jinja2.FileSystemLoader(searchpath="./")
    templateEnv = jinja2.Environment(loader=templateLoader)
    template = templateEnv.get_template(template_file)
    for sessions in result:
        for session in sessions:
            logger.info(f"Session ID: {session['session_id']}")
            logger.info(f"Start Date: {session['start_date']}")
            logger.info(f"Start Time: {session['start_time']}")
            logger.info(f"End Time: {session['end_time']}")
            logger.info(f"Duration: {session['duration']}")
            logger.info(f"Energy: {session['energy']}")
            energy = (session['energy'] / 1000)
            price = (session['energy'] / 1000) * 0.40
            outputText = template.render(id=session['session_id'],
                                         session_date=session['start_date'],
                                         start_time=session['start_time'],
                                         end_time=session['end_time'],
                                         energy=energy,
                                         duration=session['duration'],
                                         price="{:.2f}".format(price)
                                        )
            with open("output.xml", "w") as output_file:
                output_file.write(outputText)
