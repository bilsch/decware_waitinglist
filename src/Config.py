from os import environ
from yaml import safe_load

class Config:
    def __init__(self):
        homedir = environ.get('HOME')
        self.config = safe_load(open(f"{homedir}/.decware_scraper.yaml"))
    
    def mongo_uri(self):
        return self.config.get("scraper").get("mongo_uri")

    def decwarae_url(self):
        return self.config.get("scraper").get("decware_url")

    def log_file(self):
        return self.config.get("scraper").get("log_file")

    def database_name(self):
        return self.config.get("scraper").get("database_name")