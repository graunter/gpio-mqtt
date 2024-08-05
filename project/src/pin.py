import paho.mqtt.client as mqtt
import logging
from threading import Thread
import time


class CPin:
    def __init__(self):
        self.name = ""
        self.pool_period_ms = 0
        self.changes_only = False
        self.topic = ""
        self.changes_only = False
        self.file_value = ""
        self.fd = None
        self.type = ""
        self.create_start_topic = True
        self.init = [ ]

        self.PinVal = ""


    def pin_open(self):
        self.fd = open(self.file_value, "r+")

    def check_open(self):
        if self.fd is None:
            self.pin_open()  


    def on_connect(self, client: mqtt.Client):

        self.client = client
        
        common_case = ["IN", "OUT"]

        if(self.create_start_topic):
            match self.type:
                case item if item in common_case:
                    try:
                        self.check_open()
                        self.fd.seek(0)
                        self.PinVal = self.fd.read()
                        if self.PinVal:
                            client.publish( self.topic, self.PinVal)
                            logging.debug('Create topic: ' + self.topic + "for pin " + self.file_value)
                        else:
                            #TODO
                            pass

                    except Exception as e:
                        logging.error("Can't read file " + str(self.file_value) + " - init of this topic will be skipped: " + ': Message: ' + format(e) )

                case _:
                    raise ValueError(f'Unknown pin type: {self.type}')

 
        match self.type:
            case "OUT":
                [res, mid] = self.client.subscribe( self.topic )  
                if res == mqtt.MQTT_ERR_SUCCESS:
                    logging.debug('Waiting OUT topic: ' + self.topic + "for pin " + self.file_value)
                else:
                    logging.error('Failed sub OUT topic: ' + self.topic + "for pin " + self.file_value)                    

            case "IN":
                #TODO: subscribe for interrupt
                pass
        
            case _:
                raise ValueError(f'Unknown pin type: {self.type}')
    
        # an individual pooling thread for every pin
        if( self.pool_period_ms >= 0 ):
            self.pull_thrd = Thread(target=self.self_pool)
            self.pull_thrd.daemon = True
            self.pull_thrd.start()

    def self_pool(self):
        time.sleep(self.pool_period_ms/1000)
        while True:
            self.on_update()

    def on_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
        # Really thip proc is aplicable for OUT only
        self.PinVal = msg.payload.decode("utf-8")

        try:
            self.check_open()
            self.fd.seek(0)
            self.fd.write(self.PinVal)
            self.fd.flush()
        except Exception as e:
            logging.error("Can't write to file " + str(self.file_value) + " - this event will be skipped: " + ': Message: ' + format(e) )

        logging.debug('Pin ' +str(self.name)+ ' value set to  "' + str(self.PinVal) + '"')


    def on_update( self ):
        match self.type:
            case "OUT":      
                try:
                    self.check_open()
                    self.fd.seek(0)

                    if not self.changes_only:
                        self.fd.write(self.PinVal)
                        self.fd.flush()
                    else:
                        PinValNew = self.fd.read()                        
                        
                        if (self.PinVal != PinValNew):
                            self.fd.write(self.PinVal)
                            self.fd.flush()              

                except Exception as e:
                    logging.error("Can't write to file " + str(self.file_value) + " - this update will be skipped: " + ': Message: ' + format(e) )
            case "IN":
                try:
                    self.check_open()
                    self.fd.seek(0)
                    PinValNew = self.fd.read()

                    if not self.changes_only:
                        self.client.publish( self.topic, PinValNew)
                    elif self.PinVal != PinValNew:
                        self.client.publish( self.topic, PinValNew)

                    self.PinVal = PinValNew

                except Exception as e:
                    logging.error("Can't read file " + str(self.file_value) + " - update of this topic will be skipped: " + ': Message: ' + format(e) )

        
            case _:
                raise ValueError(f'Unknown pin type: {self.type}')
    
