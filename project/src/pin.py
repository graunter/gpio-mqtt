import paho.mqtt.client as mqtt
import logging
from threading import Thread
import time
from StateHolder import StateHolder
from typing import List, Dict
from collections import namedtuple
from timeit import default_timer as timer
import numpy as np
import subprocess

InitStep_t = namedtuple("InitStep_t", "OutFile Text")

class CPin:
    def __init__(self):
        self.name = ""
        self.pull_period_ms = 0
        self.status_period_sec = 0
        self.status_timer_begin = 0
        self.changes_only = False
        self.topic_rd = ""
        self.topic_wr = ""
        self.file_value = ""
        self.file_val_desc = None
        self.type = ""
        self.create_start_topic = False
        self.pause_fl = False
        self.pull_thrd = None
        self.status_thrd = None
        self.invert = False

        self.initFs: List[ InitStep_t ] = []

        self.pin_val = ""
        self.conv_tbl: List[str, str] = []


    def pin_open(self):
        self.file_val_desc = open(self.file_value, "r+")

    def check_open(self):
        if self.file_val_desc is None:
            self.pin_open()  

    def on_start(self):

        #TODO: just for user safety - should be redesigned
        try:
            return_code = subprocess.run("systemctl stop wb-mqtt-gpio")
        except Exception as e:
            pass

        for one_step in self.initFs:
            out_file = one_step.OutFile
            text = one_step.Text
            try:
                with open(out_file, "w") as this_file:
                    this_file.write(text)
            except Exception as e:
                logging.error("Some problem with file: " + str(self.name) + " - this init step was skipped: " + ': Message: ' + format(e) )                


        if self.type == "OUT":
            try:
                storage = StateHolder()
                self.pin_val = storage.load(self.name)

                self.check_open()

                real_pin_val_new = self.pin_val if not self.invert else "1" if "0"==self.pin_val else "0"
                
                self.file_val_desc.write(real_pin_val_new)
                self.file_val_desc.flush()          

            except Exception as e:
                logging.error("Can't open file: " + str(self.name) + " - state was not restored: " + ': Message: ' + format(e) )


    def on_connect(self, client: mqtt.Client):

        self.client = client
        self.status_timer_begin = timer()
        
        common_case = ["IN", "OUT"]

        if(self.create_start_topic):
            if self.type in common_case:
                try:
                    self.check_open()
                    self.file_val_desc.seek(0)
                    pin_val = self.file_val_desc.read().rstrip('\n')

                    self.pin_val = pin_val if not self.invert else "1" if "0"==pin_val else "0"

                    client.publish( self.topic_rd, self.pin_val)

                    logging.debug('Create topic: ' + self.topic_rd + "for pin " + self.file_value)


                except Exception as e:
                    logging.error("Can't read file " + str(self.file_value) + " - init of this topic will be skipped: " + ': Message: ' + format(e) )
            else:
                raise ValueError(f'Unknown pin type: {self.type}')

 
        if self.type == "OUT":
            [res, mid] = self.client.subscribe( self.topic_wr )  
            if res == mqtt.MQTT_ERR_SUCCESS:
                logging.debug('Waiting OUT topic: ' + self.topic_wr + "for pin " + self.file_value)
            else:
                logging.error('Failed sub OUT topic: ' + self.topic_wr + "for pin " + self.file_value)                    

        elif self.type ==  "IN":
            #TODO: subscribe for interrupt
            #TODO: additional read of state?
            pass
        else:
            raise ValueError(f'Unknown pin type: {self.type}')
    
        self.pause_fl = False

        # an individual pulling thread for every pin
        if( self.pull_period_ms > 0 and not self.pull_thrd ):
            self.pull_thrd = Thread(target=self.self_pull)
            self.pull_thrd.daemon = True
            self.pull_thrd.start()

        if( self.status_period_sec > 0 and not self.status_thrd ):
            self.status_thrd = Thread(target=self.self_status)
            self.status_thrd.daemon = True
            self.status_thrd.start()            

    def self_pull(self):
        while True:
            time.sleep(self.pull_period_ms/1000)
            if not self.pause_fl:
                self.on_update()

    def self_status(self):
        common_case = ["IN", "OUT"]
        while True:
            time.sleep( self.status_period_sec )
            if not self.pause_fl:
                if self.type in common_case:
                    if (timer()-self.status_timer_begin) > self.status_period_sec :
                        self.client.publish( self.topic_rd, self.pin_val )  

    def on_disconnect(self):
        self.pause_fl = True

    def on_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
        # Really this process is applicable for OUT only
        TmpPinVal = msg.payload.decode("utf-8")

        was_found = False
        if not self.conv_tbl:
            self.pin_val = TmpPinVal
        else:
            for [InVal, OutVal] in self.conv_tbl:
                if InVal == TmpPinVal:
                    self.pin_val = OutVal
                    was_found = True
                    break
                
            if not was_found:
                logging.error(f"Wrong inpit for {self.name} - this message will be skipped" )
                return

        storage = StateHolder()

        try:
            self.check_open()
            #self.fd.seek(0)    # not required really
            real_pin_val = self.pin_val if not self.invert else "1" if "0"==self.pin_val else "0"

            self.file_val_desc.write(self.real_pin_val)
            self.file_val_desc.flush()
            storage.save(str(self.pin_val), str(self.name))
            logging.debug('Pin ' +str(self.name)+ ' value set to  "' + str(self.pin_val) + '"')

            if self.topic_rd != self.topic_wr:
                client.publish( self.topic_rd, self.pin_val)

        except Exception as e:
            logging.error("Can't write to file " + str(self.file_value) + " - this event will be skipped: " + ': Message: ' + format(e) )


    def on_update( self ):

        common_case = ["IN", "OUT"]

        if self.type in common_case:
            try:
                self.check_open()
                self.file_val_desc.seek(0)
                pin_val_new = self.file_val_desc.read().strip("\n")

                real_pin_val_new = pin_val_new if not self.invert else "1" if "0"==pin_val_new else "0"

                if (timer()-self.status_timer_begin) > self.status_period_sec :
                    self.status_timer_begin = timer()
                    self.client.publish( self.topic_rd, real_pin_val_new)
                else:
                    if not self.changes_only:
                        self.client.publish( self.topic_rd, real_pin_val_new)
                    elif self.pin_val != real_pin_val_new:
                        self.client.publish( self.topic_rd, real_pin_val_new)
                        logging.debug('Pin ' +str(self.name)+ ' value set to  "' + str(real_pin_val_new) + '"')

                self.pin_val = real_pin_val_new

            except Exception as e:
                logging.error("Can't read file " + str(self.file_value) + " - update of this topic will be skipped: " + ': Message: ' + format(e) )

        else:
            raise ValueError(f'Unknown pin type: {self.type}')

