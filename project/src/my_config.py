import glob
import re
import yaml #pip install pyyaml
from pathlib import Path
from constants import *

from threading import Lock, Thread
import logging
import os
from collections import defaultdict
from typing import List, Dict

class MySingletone(type):

    _instances = {}
    _lock: Lock = Lock()
  
    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]
    

class MyConfig(metaclass=MySingletone):

    def __init__(self, CfgFile = CONFIG_FILE) -> None:
        
        logging.debug("Load of configuration" )
        
        golden_p = Path(__file__).with_name(CfgFile)
        system_p = Path( SYSTEM_PATH + COMMON_PATH )/CfgFile
        user_p = Path.home()/COMMON_PATH/CfgFile

        logging.debug('golden file: ' + str(golden_p))
        logging.debug('system file: ' + str(system_p))
        logging.debug('user file: ' + str(user_p))

        self.host = "localhost"
        self.port = 1883
        self.pasw = ""
        self.user = ""

        cfg_files_p = []
        try:
            cfg_files_p = [f for f in (Path.home()/COMMON_PATH).iterdir() if f.match("*config.yaml")]
        except Exception as e:
            logging.error( "There is some problem with" + COMMON_PATH + " - it will be skipped: " + ': Message: ' + format(e) ) 

        #TODO: The same with system files

        cfg_files = [golden_p, system_p] + cfg_files_p

        for u_file in cfg_files:
            # todo: wrong file name processing
            try:
                with u_file.open("r") as user_f:
                    try:
                        u_CfgData = yaml.safe_load(user_f)
                        self.extract_config(u_CfgData)
                    except Exception as e:
                        logging.error("YAML file " + user_f.name + " is incorrect and will be skipped: " + ': Message: ' + format(e) )
                        pass     
            except Exception as e:
                logging.error("Can't open file" + user_f.name + " - it will be skipped: " + ': Message: ' + format(e) )
                pass     


    def extract_config(self, CfgData: list):
       
        self.extract_connection(CfgData)
        self.extract_components(CfgData)


    def extract_connection(self, CfgData: list):

        Broker = CfgData.get("broker", {})

        if Broker is not None:
            self.host = Broker.get("host", self.host)
            self.port = Broker.get("port", self.port)   
            self.user = Broker.get("user", self.user)
            self.pasw = Broker.get("password", self.pasw)
        

    def extract_components(self, CfgData: list):

        if CfgData and CfgData["sysfs_pins"] is not None:
            for item in CfgData.get("sysfs_pins", []):
                pass


if __name__ == "__main__":
        Cfg = MyConfig()