import paho.mqtt.client as mqtt
import logging
from threading import Thread
import time
from StateHolder import StateHolder
from typing import List, Dict
from collections import namedtuple
from timeit import default_timer as timer

InitStep_t = namedtuple("InitStep_t", "OutFile Text")

class CPin:
    def __init__(self):
        self.name = ""
        self.pool_period_ms = 0
        self.status_period_sec = 0
        self.status_timer_begin = 0
        self.changes_only = False
        self.topic_rd = ""
        self.topic_wr = ""
        self.changes_only = False
        self.file_value = ""
        self.fd = None
        self.type = ""
        self.create_start_topic = False

        self.initFs: List[ InitStep_t ] = []

        self.PinVal = ""
        self.conv_tbl: List[str, str] = []


    def pin_open(self):
        self.fd = open(self.file_value, "r+")

    def check_open(self):
        if self.fd is None:
            self.pin_open()  

    def on_start(self):

        for one_step in self.initFs:
            out_file = one_step.OutFile
            text = one_step.Text
            try:
                with open(out_file, "w") as this_file:
                    this_file.write(text)
            except Exception as e:
                logging.error("Some problem with file: " + str(self.name) + " - this init step was skipped: " + ': Message: ' + format(e) )                


        match self.type:
            case "OUT":
                try:
                    storage = StateHolder()
                    self.PinVal = storage.load(self.name)
                    self.check_open()
                    self.fd.write(self.PinVal)
                    self.fd.flush()          

                except Exception as e:
                    logging.error("Can't open file: " + str(self.name) + " - state was not restored: " + ': Message: ' + format(e) )


    def on_connect(self, client: mqtt.Client):

        self.client = client
        self.status_timer_begin = timer()
        
        common_case = ["IN", "OUT"]

        if(self.create_start_topic):
            match self.type:
                case item if item in common_case:
                    try:
                        self.check_open()
                        self.fd.seek(0)
                        self.PinVal = self.fd.read().rstrip('\n')
                        if self.PinVal:
                            client.publish( self.topic_rd, self.PinVal)
                            client.publish( self.topic_wr, self.PinVal)
                            logging.debug('Create topic: ' + self.topic_rd + "for pin " + self.file_value)
                        else:
                            #TODO
                            pass

                    except Exception as e:
                        logging.error("Can't read file " + str(self.file_value) + " - init of this topic will be skipped: " + ': Message: ' + format(e) )

                case _:
                    raise ValueError(f'Unknown pin type: {self.type}')

 
        match self.type:
            case "OUT":
                [res, mid] = self.client.subscribe( self.topic_wr )  
                if res == mqtt.MQTT_ERR_SUCCESS:
                    logging.debug('Waiting OUT topic: ' + self.topic_wr + "for pin " + self.file_value)
                else:
                    logging.error('Failed sub OUT topic: ' + self.topic_wr + "for pin " + self.file_value)                    

            case "IN":
                #TODO: subscribe for interrupt
                pass
        
            case _:
                raise ValueError(f'Unknown pin type: {self.type}')
    
        # an individual pooling thread for every pin
        if( self.pool_period_ms > 0 ):
            self.pull_thrd = Thread(target=self.self_pool)
            self.pull_thrd.daemon = True
            self.pull_thrd.start()

        if( self.status_period_sec > 0):
            self.status_thrd = Thread(target=self.self_status)
            self.status_thrd.daemon = True
            self.status_thrd.start()            

    def self_pool(self):
        while True:
            time.sleep(self.pool_period_ms/1000)
            self.on_update()

    def self_status(self):
        common_case = ["IN", "OUT"]
        while True:
            time.sleep( self.status_period_sec )
            match self.type:
                case item if item in common_case:
                    if (timer()-self.status_timer_begin) > self.status_period_sec :
                        self.client.publish( self.topic_rd, self.PinVal)  

    def on_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
        # Really this process is applicable for OUT only
        TmpPinVal = msg.payload.decode("utf-8")

        Found = False
        if not self.conv_tbl:
            self.PinVal = TmpPinVal
        else:
            for [InVal, OutVal] in self.conv_tbl:
                if InVal == TmpPinVal:
                    self.PinVal = OutVal
                    Found = True
                    break
                
            if not Found:
                logging.error(f"Wrong inpit for {self.name} - this message will be skipped" )
                return

        storage = StateHolder()

        try:
            self.check_open()
            #self.fd.seek(0)    # not required really
            self.fd.write(self.PinVal)
            self.fd.flush()
            storage.save(str(self.PinVal), str(self.name))
            logging.debug('Pin ' +str(self.name)+ ' value set to  "' + str(self.PinVal) + '"')

            if self.topic_rd != self.topic_wr:
                client.publish( self.topic_rd, self.PinVal)

        except Exception as e:
            logging.error("Can't write to file " + str(self.file_value) + " - this event will be skipped: " + ': Message: ' + format(e) )


    def on_update( self ):
        match self.type:

            case "IN" | "OUT":
                try:
                    self.check_open()
                    self.fd.seek(0)
                    PinValNew = self.fd.read().strip("\n")

                    if (timer()-self.status_timer_begin) > self.status_period_sec :
                        self.status_timer_begin = timer()
                        self.client.publish( self.topic_rd, PinValNew)
                    else:
                        if not self.changes_only:
                            self.client.publish( self.topic_rd, PinValNew)
                        elif self.PinVal != PinValNew:
                            self.client.publish( self.topic_rd, PinValNew)
                            logging.debug('Pin ' +str(self.name)+ ' value set to  "' + str(self.PinVal) + '"')

                    self.PinVal = PinValNew

                except Exception as e:
                    logging.error("Can't read file " + str(self.file_value) + " - update of this topic will be skipped: " + ': Message: ' + format(e) )

            case _:
                raise ValueError(f'Unknown pin type: {self.type}')

