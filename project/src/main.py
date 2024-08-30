#!/usr/bin/env python3

import os, re, time, json, argparse, signal
import paho.mqtt.client as mqtt # pip install paho-mqtt
from my_config import MyConfig
import logging
import json
from threading import Thread


verbose = False

def debug(msg):
    if verbose:
        print (msg + "\n")

class CTopinator:
    def __init__(self, Cfg: MyConfig):
        self.cfg = Cfg
        self.pins = Cfg.get_components()
        logging.debug('Total ' + str(len(self.pins)) + ' was tacken')

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
      

    def on_connect(self, client, userdata, flags, rc):
        # Подписка при подключении означает, что если было потеряно соединение
        # и произошло переподключение - то подписка будет обновлена

        if rc != 0:
            logging.debug(f"Failed to connect: {rc}. loop_forever() will retry connection")
            return

        logging.debug("Connected with result code "+str(rc))

        for i, (key, CompLst) in enumerate(self.pins.items()):
            for OneComp in CompLst:
                OneComp.on_connect( client )

        self.pull_thrd = Thread(target=self.on_pool)
        self.pull_thrd.daemon = True
        self.pull_thrd.start()

    def on_pool(self):
        time.sleep(Cfg.pool_period_ms/1000)
        while True:
            for i, (key, CompLst) in enumerate(self.pins.items()):
                for OneComp in CompLst:
                    # iterate by not initialized elements only
                    if OneComp.pool_period_ms == 0: OneComp.on_update()


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

    args = parser.parse_args()
    
    loglevel = logging.INFO 
    if args.verbose: 
        loglevel = logging.DEBUG

    logging.basicConfig(level=loglevel)
    
    Cfg = MyConfig()
    
    topinator = CTopinator(Cfg)
    if args.verbose: 
        topinator.verbose = True


    signal.signal(signal.SIGINT, topinator.signal_handler)
    signal.signal(signal.SIGTERM, topinator.signal_handler)

    debug("topinator started!")

    topinator.on_start()

    client = mqtt.Client()
    client.on_connect = topinator.on_connect
    client.on_message = topinator.on_message

    # For test purposes
    #if args.verbose: 
        # client.enable_logger()
    
    Host = args.host if args.host is not None else Cfg.host
    Port = args.port if args.port is not None else Cfg.port
    User = args.user if args.user is not None else Cfg.user
    Pasw = args.pasw if args.pasw is not None else Cfg.pasw

    logging.debug("Try connection to " + str(Host) + " with port " + str(Port) + ': '+User+'+'+Pasw)

    client.username_pw_set(User, Pasw)
    client.connect(Host, Port)
        
    client.loop_forever()

