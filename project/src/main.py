#!/usr/bin/env python3

import os, re, time, json, argparse, signal
import paho.mqtt.client as mqtt # pip install paho-mqtt
from my_config import MyConfig
import logging
import json
from threading import Thread

from wb_side_io import MCP23017
from wb_side_io import DO_LEAD_ADR, DI_LEAD_ADR
from wb_side_io import DO_ADR_RANGE, DI_ADR_RANGE
from i2c import I2C
import smbus ## pip install smbus-cffi
from side_dev import *
from timeit import default_timer as timer


verbose = False

def debug(msg):
    if verbose:
        print (msg + "\n")

class CTopinator:

    def __init__(self, Cfg: MyConfig):
        self.pause_pins_fl = True
        self.pause_blocks_fl = True
        self.pull_pins_thrd = None
        self.pull_blocks_thrd = None
        self.cfg = Cfg
        self.pins = Cfg.get_components()
        self.block_lst = []
        logging.debug(f'Total {str(len(self.pins))} controller onboard pins were taken')
        self.status_timer_begin = 0

    def signal_handler(self, signal, frame):
        print(' You pressed Ctrl+C!')
        client.disconnect()

    # TODO: restore of all pins state from persistent storage
    def on_start(self):

        total_pins = list()
        for every_pin in self.pins.values():
            total_pins.extend(every_pin)
        
        #TODO: really pins selected by objects - not by files with values
        unic_pins_set = set(total_pins)
        unic_pins_lst = list(unic_pins_set)

        [pin.on_start() for pin in unic_pins_lst]

        # wb side moduls
        wbus = I2C(smbus.SMBus(1))

        # looking for DIO
        devs_adr = wbus.scan()
        logging.info(f'Side I2C addresses were found: {list(map(hex, devs_adr))}')

        if devs_adr and (len(devs_adr)!= 0):
            block_adr_lst = MCP23017.get_ord_adr_list(wbus.get_current_adr_list())
        logging.info(f'Side modules ordered by address: {list(map(hex, block_adr_lst))}')
        
        ext_lst = Cfg.get_side_ext_blocks()

        if len(ext_lst) != len(block_adr_lst):
            logging.error(f'Config file doesn`t match to bus scan!')
            return

        block_cnt = 0
        for one_block in ext_lst:
            one_block.set_location( wbus, block_adr_lst[block_cnt].item(), block_cnt+1 )
            one_block.hw_init()
            self.block_lst.append(one_block)
            logging.info(f'Modul wad added for monitoring: {one_block.name}, {one_block.ord}, {one_block.address}')
            block_cnt += 1
            


    def on_connect(self, client, userdata, connect_flags, reason_code, properties):
        # Подписка при подключении означает, что если было потеряно соединение
        # и произошло переподключение - то подписка будет обновлена

        if reason_code != 0:
            logging.debug(f"Failed to connect: {reason_code}. loop_forever() will retry connection")
            return

        logging.debug("Connected with result code "+str(reason_code))

        for i, (key, CompLst) in enumerate(self.pins.items()):
            for OneComp in CompLst:
                OneComp.on_connect( client )

        for one_block in self.block_lst:
            one_block.link_to_broker(client)

        if( Cfg.pull_period_ms > 0 ):
            self.pause_pins_fl = False
            if not self.pull_pins_thrd:
                self.pull_pins_thrd = Thread(target=self.on_pin_pull)
                self.pull_pins_thrd.daemon = True
                self.pull_pins_thrd.start()

        self.status_timer_begin = timer()
        #if self.cfg.blocks_cfg["repetition_time_sec"] > 0:
        self.pause_blocks_fl = False
        if not self.pull_blocks_thrd:
            self.pull_blocks_thrd = Thread(target=self.on_blocks_pull)
            self.pull_blocks_thrd.daemon = True
            self.pull_blocks_thrd.start()    


    def on_disconnect(self):
        logging.debug('Disconected from client') 
        self.pause_pins_fl = True

        for i, (key, CompLst) in enumerate(self.pins.items()):
            for OneComp in CompLst:
                OneComp.on_disconnect()

    def on_pin_pull(self):
        while True:
            time.sleep(Cfg.pull_period_ms/1000)
            if not self.pause_pins_fl:
                for i, (key, CompLst) in enumerate(self.pins.items()):
                    for OneComp in CompLst:
                        # iterate by not initialized elements only
                        if OneComp.pull_period_ms == 0: OneComp.on_update()

    def on_blocks_pull(self):
        #TODO: may be could be faster
        re_time = self.cfg.blocks_cfg["repetition_time_sec"] if self.cfg.blocks_cfg["repetition_time_sec"]>0 else 1
        
        while True:
            time.sleep(Cfg.pull_period_ms/1000)   
            if not self.pause_blocks_fl:
                for one_block in self.block_lst:

                    if is_upd := one_block.upd_state():
                        one_block.send_state()
                    elif False == self.cfg.changes_only:
                        one_block.send_state()

                    if self.cfg.blocks_cfg["repetition_time_sec"] > 0:
                        if ( (the_time:=timer()) -self.status_timer_begin) > re_time:
                            one_block.send_state()
                            self.status_timer_begin = the_time


    def on_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):

        for item in self.pins[msg.topic]:
            item.on_message( client, userdata, msg )


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Send MQTT payload received from a topic to any.', 
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    
    parser.add_argument('-a', '--adr-broker', dest='host', action="store",
                    help='Specify the MQTT host to connect to.')
    parser.add_argument('-p', '--port-broker', dest='port', action="store",
                    help='Specify the MQTT host to connect to.')    
    parser.add_argument('-u', '--user-broker', dest='user', action="store",
                    help='User name for Broker connection')  
    parser.add_argument('-w', '--pass-broker', dest='pasw', action="store",
                    help='Password for Broker connection.')  
    parser.add_argument('-v', '--verbose', dest='verbose', action="store_true", default=False,
                    help='Enable debug messages.')
    parser.add_argument('-c', '--config', dest='cfg_file_name', action="store", default=False,
                    help='Single config file for this app instance.')

    args = parser.parse_args()
    
    loglevel = logging.INFO 
    if args.verbose: 
        loglevel = logging.DEBUG

    logging.basicConfig(level=loglevel)
    
    Cfg = MyConfig(args.cfg_file_name)
    
    topinator = CTopinator(Cfg)
    if args.verbose: 
        topinator.verbose = True

    signal.signal(signal.SIGINT, topinator.signal_handler)
    signal.signal(signal.SIGTERM, topinator.signal_handler)

    debug("topinator started!")

    topinator.on_start()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = topinator.on_connect
    client.on_message = topinator.on_message
    client.on_disconnect = lambda client, userdata, rc: topinator.on_disconnect() 
    client.on_socket_close = lambda client, userdata, rc: topinator.on_disconnect() 

    # For test purposes
    #if args.verbose: 
        # client.enable_logger()
    
    Host = args.host if args.host is not None else Cfg.host
    Port = args.port if args.port is not None else Cfg.port
    User = args.user if args.user is not None else Cfg.user
    Pasw = args.pasw if args.pasw is not None else Cfg.pasw

    logging.debug("Try connection to " + str(Host) + " with port " + str(Port) + ': '+User+'+'+Pasw)

    client.username_pw_set(User, Pasw)
 
    ConnectedFl = False
    while not ConnectedFl:
        try:
            client.connect(Host, Port)
            ConnectedFl = True
        except:
            logging.debug(f"Can't connect - wait for some seconds.." )
            time.sleep(5)
        
    client.loop_forever()

