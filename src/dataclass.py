from datetime import datetime
from bson import ObjectId
from dataclasses import dataclass
from dataclasses_json import dataclass_json

@dataclass_json
@dataclass
class Entry:
   """Class to identify an entry in Decware order list"""
   date: datetime
   name: str
   state: str
   quantity: int
   model: str
   base: str
   voltage: str
   options: str
   status: str

@dataclass_json
@dataclass
class LogEntry:
   """Log entries"""
   date: datetime
   entry_owner: ObjectId
   status: str

@dataclass_json
@dataclass
class RunStat:
   """Class to record metrics about each run"""
   date: datetime
   new_entries: int
   new_log_entries: int
   non_new: int
   skipped: int
   before_bill: int
   total_new: int
   status_updates: int
   status_breakdown: set