import glob
import re
import yaml #pip install pyyaml
from pathlib import Path
from constants import *
from pin import CPin, InitStep_t

from threading import Lock, Thread
import logging
import os
from collections import defaultdict
from collections import namedtuple
from typing import List, Dict

from common import MySingletone


class MyConfig(metaclass=MySingletone):

    def __init__(self, CfgFile = CONFIG_FILE) -> None:
        
        logging.debug("Load of configuration" )
        
        golden_p = Path(__file__).with_name(CfgFile)
        system_p = Path( SYSTEM_PATH + COMMON_PATH )/CfgFile
        user_p = Path.home()/COMMON_PATH/CfgFile

        logging.debug('golden file: ' + str(golden_p))
        logging.debug('system file: ' + str(system_p))
        logging.debug('user file: ' + str(user_p))

        self.pins = defaultdict(list[CPin])

        self.host = "localhost"
        self.port = 1883
        self.pasw = ""
        self.user = ""

        self.pool_period_ms = 1000
        self.status_period_sec = 0
        self.changes_only = False

        cfg_files_p = []
        try:
            cfg_files_p = [f for f in (Path.home()/COMMON_PATH).iterdir() if f.match("*config.yaml")]
        except FileNotFoundError as e:
            logging.warning( "There is no file " + e.filename + " : " + ': Message: ' + format(e) ) 
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
                logging.error("Can't open file" + str(u_file) + " - it will be skipped: " + ': Message: ' + format(e) )
                pass     


    def extract_config(self, CfgData: list):
       
        self.extract_connection(CfgData)
        self.extract_components(CfgData)
        self.extract_misc_conf(CfgData)

    def extract_misc_conf(self, CfgData: list):

        MiscCfg = CfgData.get("cfg", {})

        if MiscCfg is not None:
            self.pool_period_ms = MiscCfg.get("pool_period_ms", self.pool_period_ms)
            self.changes_only = MiscCfg.get("changes_only", self.changes_only) 
            self.status_period_sec = MiscCfg.get("status_period_sec", self.status_period_sec) 
            

    def extract_connection(self, CfgData: list):

        Broker = CfgData.get("broker", {})

        if Broker is not None:
            self.host = Broker.get("host", self.host)
            self.port = Broker.get("port", self.port)   
            self.user = Broker.get("user", self.user)
            self.pasw = Broker.get("password", self.pasw)
        

    def extract_components(self, CfgData: list):
        
        NoNameCnt=0
        if CfgData and CfgData["sysfs_pins"] is not None:
            for item in CfgData.get("sysfs_pins", []):
                pin = CPin()
                pin.name = item.get("name", "")
                if not pin.name:
                    pin.name = "NoName" + NoNameCnt
                    NoNameCnt += 1
                    
                pin.changes_only = item.get("changes_only", False)


                pin_topics = item.get("topic")
                if not pin_topics:
                    # Instead of one general topic for control - two can be used
                    pin.topic_wr = item.get("topic_wr")
                    if not pin.topic_wr: pin.topic_wr = item.get("topic_cmd", "")
                    if not pin.topic_wr: logging.warning( f"The topic name for WR commands in {pin.name} is absent" )

                    pin.topic_rd = item.get("topic_rd")
                    if not pin.topic_rd: pin.topic_rd = item.get("topic_state", "")
                    if not pin.topic_rd: logging.warning( f"The topic name for RD states in {pin.name} is absent" )                    
                else:
                    pin.topic_wr = pin_topics
                    pin.topic_rd = pin_topics

                pin.pool_period_ms = item.get("pool_period_ms", 0)

                pin.file_value = item.get("file_value")
                # TODO: Check file not empty and exist after init
                pin.type = item.get("type")
                # TODO: Check ftype is correct
                pin.create_start_topic = item.get("create_start_topic", False)

                for InitStep in item.get("init", []):
                    OutFile = InitStep.get("file")
                    if OutFile is None:
                        continue                    # TODO: Err msg
                    OutText = InitStep.get("text")
 
                    pin.init.append( InitStep_t(OutFile, OutText) )

                pin.status_period_sec = item.get("status_period_sec", self.status_period_sec)

                pin_convert_table = item.get("convert_table")
                if pin_convert_table is not None:
                    for ConvStep in item.get("convert_table"):
                        Name = ConvStep.get("Name")
                        BrokerVal = ConvStep.get("broker")
                        FileVal = ConvStep.get("file")

                        print( f"{pin.name} = 1: {Name}, 2: {BrokerVal}, 3: {FileVal}" )

                        pin.conv_tbl.append( [BrokerVal, FileVal] )

                self.pins.setdefault( pin.topic_wr, [] )   
                self.pins[pin.topic_wr].append(pin)



    def get_components(self) -> Dict[str, List[CPin]]:   
        logging.debug('Total ' + str(len(self.pins)) + ' was passed')
        return self.pins




if __name__ == "__main__":
        Cfg = MyConfig()