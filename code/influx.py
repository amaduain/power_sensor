from datetime import datetime
from influxdb import InfluxDBClient
db_name = "power"



def create_db(client,db_name):
    client = InfluxDBClient(host='localhost', port=8086)
    db_list = client.get_list_database()
    for db in db_list:
        if db['name'] == db_name:
            print(f"Database {db_name} already exists, skipping creation")
            return
    client.create_database(db_name)



from datetime import datetime
from influxdb import InfluxDBClient
db_name = "power"
query = 'select *  from ev_power;'
qyery = "SELECT mean(\"current\") FROM \"ev_power\" WHERE (\"user\" = 'Alex') AND time >= now() - 6h and time <= now() GROUP BY time(1m) fill(null)"
client = InfluxDBClient(host='localhost', port=8086,database=db_name)
client.query(query)