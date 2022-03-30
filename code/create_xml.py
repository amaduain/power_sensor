import logging
import pytz
from datetime import datetime, timedelta
from influxdb import InfluxDBClient


##GLOBAL VARIABLES####
sessions_db_name = "sessions"
log_level = logging.INFO



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
    #logger.setLevel(log_level)
    # Enable the screen logging.
    #logger.addHandler(log_handler)
    console = logging.StreamHandler()
    console.setLevel(log_level)
    console.setFormatter(formatter)
    logger.addHandler(console)
    return logger, console


def last_day_of_month(any_day):
    # this will never fail
    # get close to the end of the month for any day, and add 4 days 'over'
    next_month = any_day.replace(day=28) + timedelta(days=4)
    # subtract the number of remaining 'overage' days to get last day of current month, or said programattically said, the previous day of the first of next month
    return next_month - timedelta(days=next_month.day)

if __name__ == '__main__':
    logger, log_handler = create_logger(log_level)
    logger.info("Starting XML Creation...")
    query = 'select *  from ev_sessions;'
    # Using the actual month for now....
    timestamp = datetime.utcnow().replace(tzinfo=pytz.utc)
    cet_date = timestamp.astimezone(pytz.timezone('Europe/Madrid'))
    month_start = cet_date.replace(day=1,hour=0,minute=0,second=0,microsecond=0)
    month_end =last_day_of_month(month_start)
    month_end = month_end.replace(hour=23,minute=59,second=59)
    logger.info(f"First day of month: {month_start}")
    logger.info(f"Last day of month: {month_end}")
    client = InfluxDBClient(host='localhost', port=8086,database=sessions_db_name)
