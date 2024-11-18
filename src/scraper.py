#!/usr/bin/env python

import logging
import requests

from bs4 import BeautifulSoup
from datetime import datetime
from pymongo import MongoClient
from pymongo.collation import Collation
import numpy as np
from bson import ObjectId

from dataclass import Entry, LogEntry, RunStat
from Config import Config

# logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s",
    handlers=[
        logging.FileHandler(Config().log_file()),
        logging.StreamHandler()
    ]
)

logging.info("Starting")
method = "http"
headers = {
   "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
   "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
   "accept-language": "en-US,en;q=0.9"
}

if method == "http":
   logging.debug("Fetching from http")
   url = Config().decwarae_url()
   order_list = requests.get(url, headers=headers)
   content = order_list.content
   order_list.close()
else:
   logging.debug("Using local copy")
   order_list = open("waiting_list.html", "r")
   content = order_list.read()

logging.debug("soup processing")
soup = BeautifulSoup(content, features="lxml")
table = soup.find('table', id="example2")

logging.info("Crunching through table rows")
entries = []
scrape_processing_times = []

for table in table.find_all('tbody'):
   for row in table.find_all('tr'):
      table_data = row.find_all('td')

      date = datetime.strptime(table_data[0].text, "%Y-%m-%d %H:%M:%S")
      name = table_data[1].text
      state = table_data[2].text
      quantity = int(table_data[3].text)
      model = table_data[4].text
      base = table_data[5].text
      voltage = table_data[6].text
      options = table_data[7].text
      status = table_data[8].text

      entries.append(Entry(date, name, state, quantity, model, base, voltage, options, status))

logging.debug("connect to mongo")
mc = MongoClient(Config().mongo_uri())
db = mc.get_database(Config().database_name())

# collections we'll call
entry_col = db.get_collection("entries")
log_col = db.get_collection("log")
stats_col = db.get_collection("stats")

inserted_entries = 0
new_log_entries = 0
skipped = 0
status_updates = 0
entry_procesing_times = []

logging.info("Comparing database entries to decware state")
for entry in entries:

   # This should be unique enough
   db_entry = entry_col.find_one({'date': entry.date, 'name': entry.name, 'model': entry.model})

   if db_entry is None:
      # If new just insert it into entry table
      inserted_entries += 1
      new_log_entries += 1
      insert_result = entry_col.insert_one(entry.to_dict())
      insert_id = insert_result.inserted_id
      log_entry = LogEntry(entry.date, insert_id, entry.status)
      log_result = log_col.insert_one(log_entry.to_dict())

      logging.debug("Calculating processing time and appending")
      logging.info(f"New entry id: {insert_id} for {entry.name} model {entry.model}")
   else:
      # If we already have it in entry table go see if we have a log event matching the status
      db_name = db_entry.get("name")
      db_status = db_entry.get("status")
      entry_id = db_entry.get("_id")

      if entry.status != db_status:
         logging.info(f"Update status for id: {entry_id} for {db_name} from status of ({db_status}) to ({entry.status})")
         db_entry.update({"$set": {"status": entry.status}})
         log_entry = LogEntry(datetime.now(), entry_id, entry.status)
         log_result = log_col.insert_one(log_entry.to_dict())
         log_id = log_result.inserted_id

         status_updates += 1
         new_log_entries += 1
         logging.info(f"Stored new event {entry_id} and log_id {log_id} status: {status}")

#
# Loop over database entries
#   - If we find an entry in the database which is not in entries 
#     1) update its status to Complete
#     2) log the Complete status
#
logging.info("Finding database entries to mark as Complete")
db_entries = entry_col.find({"status": { "$ne": "Complete" }})
completed = 0

for db_entry in db_entries:
   # loop over all entries
   found = False

   # Same logic as our find - compare name date and model to determine a match
   for x in entries:
      if x.name == db_entry.get("name") and x.date == db_entry.get("date") and x.model == db_entry.get("model"):
         found = True
         break

   if found == False:
      completed += 1
      inserted_entries += 1
      new_log_entries += 1
      id = db_entry.get("_id")
      status = db_entry.get("status")
      logging.info(f"Updating {id} from status {status} - setting status to Complete")

      # TODO: This ... should work
      # update_result = db_entry.update({"$set": {"status": "Complete"}})
      update_result = entry_col.update_one({"_id": id}, {"$set": {"status": "Complete"}})

      logging.debug(update_result)
      log_entry = LogEntry(datetime.now(), id, "Complete")
      log_col.insert_one(log_entry.to_dict())

before_bill = 0
total_new = 0
non_new = 0
bill_order_dt = datetime(2024, 11, 3, 16, 34)

# The entry collection only ever shows new
# We need to look in the log collection to calculate things that changed status since the initial
logging.info("Generating stats")

total_new_count = entry_col.count_documents({"status": "New"})
non_new = entry_col.count_documents({
   "status": 
      [
         { "$ne": "New" },
         { "$ne": "Complete" }
      ]
   },
)
before_bill = entry_col.count_documents({ "date": { "$lt": bill_order_dt }, "status": "New" })

logging.info(f"Inserted {inserted_entries} new entries")
logging.info(f"Inserted {new_log_entries} new log events")
logging.info(f"skipped {skipped} entries with no new updates")
logging.info(f"status updates: {status_updates}")
logging.info(f"in-flight count: {non_new}")
logging.info(f"Number of new before Bill: {before_bill}")
logging.info(f"total new: {total_new_count}")
logging.info(f"completed: {completed}")

run_stats = RunStat(datetime.now(), inserted_entries, new_log_entries, non_new, skipped, before_bill, total_new_count, status_updates, completed)
logging.debug(f"Submitting stats: {run_stats}")
stats_col.insert_one(run_stats.to_dict())

logging.info("Done")