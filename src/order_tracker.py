#!/usr/bin/env python

from pymongo import MongoClient
from Config import Config

print("connect to mongo")
mc = MongoClient(Config().mongo_uri())
db = mc.get_database(Config().database_name())

# collections we'll call
entry_col = db.get_collection("entries")
log_col = db.get_collection("log")

complete_amps = entry_col.find({"status": "Complete"})
days = []

for amp in complete_amps:
    id = amp.get("_id")
    model = amp.get("model")
    order_date = amp.get("date")
    log = log_col.find_one({"entry_owner": id, "status": "Complete"})
    complete_date = log.get("date")
    diff = complete_date - order_date
    days.append(diff.days)

    print(f"{id} model {model} order date: {order_date} complete date: {complete_date} - took {diff.days} days")

avg_days_to_complete = sum(days) / len(days)
print(f"Average days to complete: {avg_days_to_complete}")