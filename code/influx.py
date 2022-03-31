from datetime import datetime
from influxdb import InfluxDBClient
db_name = "sessions"



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
db_name = "sessions"
query = 'select *  from ev_session;'
client = InfluxDBClient(host='localhost', port=8086,database=db_name)
client.query(query)
session_json_body = [
                                    {
                                        "measurement": "ev_session",
                                        "tags": {
                                            "user": "Alex"
                                        },
                                        "time": "2022-03-30T20:34:01.190177Z",
                                        "fields": {
                                            "start_date": "03/30/2022",
                                            "start_time": "10:34:01 PM",
                                            "end_time": "01:10:28 AM",
                                            "energy": 10351,
                                            "duration": "2h 36m 27s",
                                            "session_id": "S01OMXAXDUTPUZURQROPNAPEQEG"
                                        }
                                    }
                                ]

sessions_db_name = db_name
sessions_db_client = InfluxDBClient(host='localhost', port=8086,database=sessions_db_name)
sessions_db_client.write_points(session_json_body)
sessions_db_client.close()