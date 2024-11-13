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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s",
    handlers=[
        logging.FileHandler("stats.log"),
        logging.StreamHandler()
    ]
)

logging.info("Starting")

logging.debug("connect to mongo")
mc = MongoClient(Config().mongo_uri())
db = mc.get_database(Config().database_name())

# collections we'll call
entry_col = db.get_collection("entries")
log_col = db.get_collection("log")
stats_col = db.get_collection("stats")

count_order_over_time_query = [
    {
        '$project': {
            'count': {
                '$dateToString': {
                    'format': '%Y-%m', 
                    'date': '$date'
                }
            }
        }
    }, {
        '$group': {
            '_id': {
                'date': '$count'
            }, 
            'orderCount': {
                '$sum': 1
            }
        }
    }, {
        '$sort': {
            '_id': 1
        }
    }
]
orders_by_date_agg = entry_col.aggregate(count_order_over_time_query)
header = "date, count"
orders_by_date_histo = []

for result in orders_by_date_agg:
    date = result["_id"].get("date")
    value = result.get("orderCount")

    if value == None:
        value = 0

    orders_by_date_histo.append(f"{date}, {value}")

with open("order_count.csv", "w+") as f:
    f.writelines(f"{header}\n")

    for row in orders_by_date_histo:
        f.writelines(f"{row}\n")

# order count by amp model
agg_result = entry_col.aggregate([
   { 
      "$group" :  {
         "_id" : "$model",
         "count" : {"$sum" : 1} 
      }
   } 
])

with open("model_stats.csv", "w+") as f:
    f.write("model, count\n")

    for i in agg_result: 
        model = i.get("_id")
        count = i.get("count")
        
        f.write(f"{model}, {count}\n")