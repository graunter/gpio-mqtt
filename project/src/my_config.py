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
from block_factory import *


class MyConfig(metaclass=MySingletone):

    def __init__(self, CfgFile) -> None:
        

        self.pins = defaultdict(list[CPin])
        self.side_blocks = [] 

        self.host = "localhost"
        self.port = 1883
        self.pasw = ""
        self.user = ""

        self.pool_period_ms = 1000
        self.status_period_sec = 0
        self.changes_only = False

        self.NoNameCnt=0

        self.blocks_cfg = defaultdict(dict)

        self.blocks_cfg["common_path"] = ""
        self.blocks_cfg["repetition_time_sec"] = 0
        self.blocks_cfg["reset_to_def_topic"] = ""
     


        logging.debug("Load of configuration" )
        
        if CfgFile:
            __location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
            cfg_files = [ Path(os.path.join(__location__, CfgFile)) ]
        else:
            golden_p = Path(__file__).with_name(CONFIG_FILE)
            system_p = Path( SYSTEM_PATH + COMMON_PATH )/CONFIG_FILE
            #user_p = Path.home()/COMMON_PATH/CONFIG_FILE

            cfg_files_p = []
            try:
                cfg_files_p = [f for f in (Path.home()/COMMON_PATH).iterdir() if f.match("*config.yaml")]
            except FileNotFoundError as e:
                logging.warning( "There is no file " + e.filename + " : " + ': Message: ' + format(e) ) 
            except Exception as e:
                logging.error( "There is some problem with " + COMMON_PATH + " - it will be skipped: " + ': Message: ' + format(e) ) 

            #TODO: The same with system files

            #cfg_files = [golden_p, system_p] + cfg_files_p # TODO: golden file should be without config for hardware
            cfg_files = [system_p] + cfg_files_p

        for cfg_file in cfg_files:
            # todo: wrong file name processing
            try:
                with cfg_file.open("r") as user_f:
                    logging.debug('config file processing: ' + str(user_f.name))
                    try:
                        u_CfgData = yaml.safe_load(user_f)
                        self.extract_config(u_CfgData)
                    except Exception as e:
                        logging.error("YAML file " + user_f.name + " is incorrect and will be skipped: " + ': Message: ' + format(e) )
                        pass     
            except Exception as e:
                logging.error("Can't open file" + str(cfg_file) + " - it will be skipped: " + ': Message: ' + format(e) )
                pass     


    def extract_config(self, CfgData: list):
       
        self.extract_connection(CfgData)
        self.extract_misc_conf(CfgData)        
        self.extract_components(CfgData)
        self.extrct_i2c_mods(CfgData)


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
        
        if CfgData and CfgData["sysfs_pins"] is not None:
            for item in CfgData.get("sysfs_pins", []):
                pin = CPin()
                pin.name = item.get("name", "")
                if not pin.name:
                    pin.name = "NoName" + self.NoNameCnt
                    self.NoNameCnt += 1
                    
                pin.changes_only = item.get("changes_only", self.changes_only)

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

                pin.pool_period_ms = item.get("pool_period_ms", self.pool_period_ms)

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
 
                    pin.initFs.append( InitStep_t(OutFile, OutText) )

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

    def extrct_i2c_mods(self, CfgData: list):
        if CfgData and CfgData["ext_i2c"] is None:
            return
        
        item = CfgData.get("ext_i2c", [])

        self.blocks_cfg["common_path"] = item.get("common_path", self.blocks_cfg["common_path"])
        self.blocks_cfg["repetition_time_sec"] = item.get("repetition_time_sec", self.blocks_cfg["repetition_time_sec"])
        self.blocks_cfg["reset_to_def_topic"] = item.get("reset_to_def_topic", self.blocks_cfg["reset_to_def_topic"])

        cfg_pos_cnt = 0
        for one_blk_cfg in item.get("modules", []):
            one_blk_cfg["cfg_pos_cnt"] = cfg_pos_cnt
            the_block = CLibirator.GetByConfig(one_blk_cfg, self.blocks_cfg)
            self.side_blocks.append(the_block)
            cfg_pos_cnt += 1

    def get_side_ext_blocks(self) -> List[CSideDev]:
        return self.side_blocks

    def get_components(self) -> Dict[str, List[CPin]]:   
        logging.debug('Total ' + str(len(self.pins)) + ' was passed')
        return self.pins




if __name__ == "__main__":
        Cfg = MyConfig("config.yaml")