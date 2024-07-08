#!/usr/bin/env python3

import os, re, time, json, argparse, signal
import paho.mqtt.client as mqtt # pip install paho-mqtt
from my_config import MyConfig
import logging
import json


verbose = False

def debug(msg):
    if verbose:
        print (msg + "\n")

class CTopinator:
    def __init__(self, Cfg: MyConfig):
        self.cfg = Cfg

    def signal_handler(self, signal, frame):
        print('You pressed Ctrl+C!')
        client.disconnect()

    def on_connect(self, client, userdata, flags, rc):
        
        logging.debug("Connected with result code "+str(rc))
        # Подписка при подключении означает, что если было потеряно соединение
        # и произошло переподключение - то подписка будет обновлена


    def on_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
        pass


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Send MQTT payload received from a topic to any.', 
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    
    parser.add_argument('-a', '--adr-broker', dest='host', action="store",
                    help='Specify the MQTT host to connect to.')
    parser.add_argument('-p', '--port-broker', dest='port', action="store",
                    help='Specify the MQTT host to connect to.')    
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

    client = mqtt.Client()
    client.on_connect = topinator.on_connect
    client.on_message = topinator.on_message
    
    Host = args.host if args.host is not None else Cfg.host
    Port = args.port if args.host is not None else Cfg.port

    logging.debug("Try connection to " + str(Host) + " with port " + str(Port) )
    client.connect(Host, Port)
        
    client.loop_forever()

