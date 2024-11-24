#!/usr/bin/env python

import logging
from pymongo import MongoClient
from pymongo.collation import Collation
from datetime import datetime, timedelta
import numpy as np

from Config import Config

# logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s",
    handlers=[
        logging.FileHandler(Config().rolling_completion_log_file()),
        logging.StreamHandler()
    ]
)

logging.debug("connect to mongo")
mc = MongoClient(Config().mongo_uri())
db = mc.get_database(Config().database_name())

# collections we"ll call
entry_col = db.get_collection("entries")
log_col = db.get_collection("log")

end_date = datetime.now()
# start_date = end_date - timedelta(days=5)
start_date = datetime(2024, 11, 19)

completed_over_time_query = {
    "status": "Complete",
    "date": {
        "$gte": start_date, 
        "$lt": end_date 
    }
}
completed_over_time = log_col.find(completed_over_time_query)
completed_days = []

for completed_entry in completed_over_time:
    entry_id = completed_entry.get("entry_owner")
    completed_date = completed_entry.get("date")
    completed_date_short = f"{completed_date.year}-{completed_date.month}-{completed_date.day}"
    entry = entry_col.find_one({"_id": entry_id})
    order_date = entry.get("date")
    complete_date = completed_entry.get("date")
    took = complete_date - order_date

    completed_days.append(took.days)
    logging.debug(f"Order {entry_id} completed on {completed_date_short} took {took.days} days to complete")

avg = np.average(completed_days)
min = np.min(completed_days)
max = np.max(completed_days)

logging.info(f"Min: {min}, Max: {max}, Avg: {avg}")

my_order_date = datetime(2024, 11, 3)
avg_days_from_now = my_order_date + timedelta(days=int(avg))
max_days_from_now = my_order_date + timedelta(days=int(max))

logging.info("Projected completion dates")
logging.info(f"avg:             {avg_days_from_now}")
logging.info(f"max:             {max_days_from_now}")

for p in [80, 90, 99]:
    x = my_order_date + timedelta(days=int(np.percentile(completed_days, p)))
    logging.info(f"{p}th percentile: {x}")
