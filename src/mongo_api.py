import pymongo
from datetime import datetime, timedelta
from bson.objectid import ObjectId

db = pymongo.MongoClient("mongodb://mongoadmin:mongoadmin@localhost:27017/")
python_bot_db = db.pybot

tasks_collection = python_bot_db.tasks
notifications_collection = python_bot_db.notifications


class Notification:
    next: datetime
    period: timedelta
    times_left: int
    _id: str
    _task_id: str

    def __init__(self, next: datetime = datetime.now() + timedelta(days=1), period: timedelta = timedelta(days=1), timesLeft: int = 3, _task_id: str = "-1", _id: str = "-1"):
        self.next = next
        self.period = period
        self.times_left = timesLeft
        self._id = _id
        self._task_id = _task_id


    def insert(self):       
        
        result = notifications_collection.insert_one({
            "_task_id": ObjectId(self._task_id),
            "next": self.next,
            "period_sec": self.period.total_seconds(),
            "times_left": self.times_left,
        })

        self._id = result.inserted_id    

    def to_dict(self):
        related_task = Task.get_task_by_id(self._task_id)
        if related_task == None:
            print("DROP", self._task_id)

        return {
            "next": self.next.isoformat(), 
            "period_sec": self.period.total_seconds(), 
            'deadline': related_task.deadline.isoformat(),
            "times_left": self.times_left,
            "user_id": related_task.user_id,
            "title": related_task.title,
            "description": related_task.description
        }
    
    def get_all() -> list:
        query = notifications_collection.find()
        result = list()
        for notification in query:
            result.append(Notification(next=notification["next"], period=timedelta(seconds=notification["period_sec"]), timesLeft=notification["times_left"], _task_id=notification["_task_id"], _id=notification["_id"]))

        return result
    
    def delete(self):
        notifications_collection.delete_one({"_id": ObjectId(self._id)})


    def commit(self):
        notifications_collection.update_one({"_id": ObjectId(self._id)}, {"$set": {
            "next": self.next,
            "period_sec": self.period.total_seconds(),
            "times_left": self.times_left,
        }})


    def update(self, current_time: datetime) -> bool:
        if(current_time > self.next):
            self.times_left -= 1

            if self.times_left < 0:
                self.delete()
                return False
                        
            self.next = self.next + self.period
            self.commit()
            return True
        
        return False
    

class Task:
    user_id: int
    title: str
    description: str
    deadline: datetime
    _id: str
    was_longen: bool

    def __init__(self, user_id, title, description, deadline, _id=None, wasLongen = False,):
        self.user_id = user_id
        self.title = title
        self.description = description
        self.deadline = deadline
        self.was_longen = wasLongen

        if(_id != None):
            self._id = _id

    def commit(self):
        tasks_collection.update_one({"_id": ObjectId(self._id)}, {"$set": {
            "title": self.title,
            "description": self.description,
            "deadline": self.deadline,
            "was_longen": self.was_longen
        }})

    def insert(self):
        result = tasks_collection.insert_one({
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "deadline": self.deadline,
            "was_longen": False,
        })
        
        self._id = result.inserted_id

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "deadline": self.deadline.isoformat()
        }

    def update(self, current_time: datetime) -> bool:
        if not self.was_longen and current_time > self.deadline:
            self.was_longen = True
            self.deadline += timedelta(days=1)
            self.commit()
            return True
        
        return False

    def get_all() -> list:
        query = tasks_collection.find()
        result = list()
        for task in query:
            ParsedTask = Task(task["user_id"], task["title"], task["description"], task["deadline"], task["_id"], task["was_longen"])
            result.append(ParsedTask)

        return result
    
    def get_all_by_day(target_day: datetime, user_id: int) -> list:
        start_of_day = datetime(target_day.year, target_day.month, target_day.day, 0, 0, 0)
        end_of_day = datetime(target_day.year, target_day.month, target_day.day, 23, 59, 59)
        query = tasks_collection.find({
            "deadline": {
                "$gte": start_of_day,
                "$lte": end_of_day,
            },
            "user_id": user_id,
        })
        result = list()
        for task in query:
            ParsedTask = Task(task["user_id"], task["title"], task["description"], task["deadline"], task["_id"], task["was_longen"])
            result.append(ParsedTask)

        return result
    
    def delete_all_by_day(target_day: datetime, user_id: int):
        tasks = Task.get_all_by_day(target_day, user_id)
        for task in tasks:
            task.delete()

    def get_all_by_user(user_id: int) -> list:
        query = tasks_collection.find({"user_id": user_id})
        result = list()
        for task in query:
            ParsedTask = Task(task["user_id"], task["title"], task["description"], task["deadline"], task["_id"], task["was_longen"])
            result.append(ParsedTask)

        return result

    def get_task_by_id(_task_id: str):
        query = tasks_collection.find_one({"_id": ObjectId(_task_id)})
        if(query == None):
            return None
        
        ParsedTask = Task(query["user_id"], query["title"], query["description"], query["deadline"], query["_id"], query["was_longen"])
        return ParsedTask
    
    def delete(self):
        tasks_collection.delete_one({"_id": ObjectId(self._id)})
        notifications_collection.delete_many({"_task_id": ObjectId(self._id)})

    

        
    
