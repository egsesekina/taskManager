import redis.exceptions
from mongo_api import Notification, Task
from datetime import datetime, timedelta
import redis
import json

try:
    r = redis.Redis(host='localhost', port='27020', db=0)
    r.ping()
    print("connected to redis")
except redis.exceptions.ConnectionError as e:
    print(f'couldnot connect to redis: {e}')
    exit()

#n = Notification(datetime.now(), timedelta(seconds=2), 10, 0)
#n.insert()

while True:
    notifications = Notification.get_all()
    tasks = Task.get_all()
    current_time = datetime.now()


    for notification in notifications:
        wasUpdated = notification.update(current_time)
        
        if wasUpdated:
            r.rpush('reminders', json.dumps(notification.to_dict()))


    for task in tasks:
        wasLongen = task.update(current_time)

        if wasLongen:
            r.rpush('expired', json.dumps(task.to_dict()))
