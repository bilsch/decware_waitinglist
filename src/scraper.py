#!/usr/bin/env python

import logging
import requests

from bs4 import BeautifulSoup
from datetime import datetime
from pymongo import MongoClient
from pymongo.collation import Collation
import numpy as np

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
      scrape_time_start = datetime.now().timestamp()
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

      scrape_time_end = datetime.now().timestamp()
      scrape_time = scrape_time_end - scrape_time_start
      scrape_processing_times.append(scrape_time)

scrape_procesing_time_avg = np.mean(scrape_processing_times)
scrape_procesing_time_max = np.max(scrape_processing_times)
scrape_procesing_time_pcnt = np.percentile(scrape_processing_times, 99)
scrape_procesing_time_sum = np.sum(scrape_processing_times)

logging.info(f"scrape processing stats - average: {scrape_procesing_time_avg} max: {scrape_procesing_time_max} 99th percentile: {scrape_procesing_time_pcnt} total time: {scrape_procesing_time_sum}")

logging.debug("connect to mongo")
mc = MongoClient(Config().mongo_uri())
db = mc.get_database(Config().database_name())

# collections we'll call
entry_col = db.get_collection("entries")
log_col = db.get_collection("log")
stats_col = db.get_collection("stats")

# mongo indices for queries we are going to make
entry_col.create_index({"date": 1, "name": 1, "model": 1})
log_col.create_index({"entry_owner": 1, "status": 1})

inserted_entries = 0
new_log_entries = 0
skipped = 0
status_updates = 0
entry_procesing_times = []

logging.info("Comparing database entries to decware state")
for entry in entries:
   entry_start_time = datetime.now().timestamp()

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

      entry_end_time = datetime.now().timestamp()
      processing_time = entry_end_time - entry_start_time
      entry_procesing_times.append(processing_time)
   else:
      # If we already have it in entry table go see if we have a log event matching the status
      db_name = db_entry.get("name")
      db_status = db_entry.get("status")
      entry_id = db_entry.get("_id")

      if entry.status != db_status:
         logging.info(f"Update status for id: {entry_id} for {db_name} from status of ({db_status}) to ({entry.status})")
         db_entry.update({"$set": {"status": entry.status}})
         status_updates += 1

      # Do we have a matching log entry for the current status
      log_event = log_col.find_one({"entry_owner": entry_id, "status": db_status})
      if log_event:
         # We have already recorded this status just continue to the next record
         logging.debug("Skipping {entry} as we already indexed in present state")
         skipped += 1

         logging.debug("Calculating processing time and appending")
         entry_end_time = datetime.now().timestamp()
         processing_time = entry_end_time - entry_start_time
         entry_procesing_times.append(processing_time)
      else:
         new_log_entries += 1
         log_entry = LogEntry(entry.date, entry_id, entry.status)
         log_result = log_col.insert_one(log_entry.to_dict())
         log_id = log_result.inserted_id
         logging.info(f"Stored new event {entry_id} and log_id {log_id} status: {status}")

         logging.debug("Calculating processing time and appending")
         entry_end_time = datetime.now().timestamp()
         processing_time = entry_end_time - entry_start_time
         entry_procesing_times.append(processing_time)

entry_procesing_time_avg = np.mean(entry_procesing_times)
entry_procesing_time_max = np.max(entry_procesing_times)
entry_procesing_time_pcnt = np.percentile(entry_procesing_times, 99)
entry_procesing_time_sum = np.sum(entry_procesing_times)

before_bill = 0
total_new = 0
non_new = 0
bill_order_dt = datetime(2024, 11, 3, 16, 34)

logging.info(f"Entry processing stats - average: {entry_procesing_time_avg} max: {entry_procesing_time_max} 99th percentile: {entry_procesing_time_pcnt} total time: {entry_procesing_time_sum}")

# The entry collection only ever shows new
# We need to look in the log collection to calculate things that changed status since the initial
logging.info("Generating stats")

total_new_count = entry_col.count_documents({"status": "New"})
non_new = entry_col.count_documents({"status": { "$ne": "New" }})
before_bill = entry_col.count_documents({ "date": { "$lt": bill_order_dt }, "status": "New" })

status_breakdown = {}
agg_result = entry_col.aggregate([
   { 
      "$group" :  {
         "_id" : "$status",
         "count" : {"$sum" : 1} 
      }
   } 
])

for i in agg_result: 
   status = i.get("_id")
   count = i.get("count")
   status_breakdown[status] = count

   logging.debug(f"Append {status}={count}")

logging.info(f"Inserted {inserted_entries} new entries")
logging.info(f"Inserted {new_log_entries} new log events")
logging.info(f"skipped {skipped} entries with no new updates")
logging.info(f"status updates: {status_updates}")
logging.info(f"in-flight count: {non_new}")
logging.info(f"Number of new before Bill: {before_bill}")
logging.info(f"total new: {total_new_count}")
logging.info(f"By-status breakdown: {status_breakdown}")

run_stats = RunStat(datetime.now(), inserted_entries, new_log_entries, non_new, skipped, before_bill, total_new_count, status_updates, status_breakdown)
logging.debug(f"Submitting stats: {run_stats}")
stats_col.insert_one(run_stats.to_dict())

logging.info("Done")