from datetime import datetime
from influxdb import InfluxDBClient
dbname = "power"



def create_db(client,db_name):
    client = InfluxDBClient(host='localhost', port=8086)
    db_list = client.get_list_database()
    for db in db_list:
        if db['name'] == db_name:
            print(f"Database {db_name} already exists, skipping creation")
            return
    client.create_database(db_name)



client = InfluxDBClient(host='localhost', port=8086,database='dbname')