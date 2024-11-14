#!/usr/bin/env python

import logging
from pymongo import MongoClient
from pymongo.collation import Collation

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

logging.debug("connect to mongo")
mc = MongoClient(Config().mongo_uri())
db = mc.get_database(Config().database_name())

# collections we'll call
entry_col = db.get_collection("entries")
log_col = db.get_collection("log")
stats_col = db.get_collection("stats")

# mongo indices for queries we are going to make
entry_col.create_index({"date": 1, "name": 1, "model": 1})
entry_col.create_index({"status": 1})

log_col.create_index({"entry_owner": 1, "status": 1})
