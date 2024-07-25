import paho.mqtt.client as mqtt
import logging


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
        self.create_empty_topic = True
        self.init = [ ]


    def pin_open(self):
        self.fd = open(self.file_value, "r+")

    def check_open(self):
        if self.fd is None:
            self.pin_open()  


    def on_connect(self, client: mqtt.Client):
        match self.type:
            case "DO":
                if(self.create_empty_topic):
                    client.publish( self.topic, "")
                    logging.debug('Create DO topic: ' + self.topic + "for pin " + self.file_value)
                else:
                    logging.debug('Waiting DO topic: ' + self.topic + "for pin " + self.file_value)
                
                client.subscribe( self.topic )

            case "DI":
                logging.debug('Create DI topic: ' + self.topic + "for pin " + self.file_value)
                #TODO

            case _:
                raise ValueError(f'Unknown pin type: {self.type}')
            

    def on_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
        PinVal = msg.payload
        
        try:
            self.check_open()
            self.fd.seek(0)
            self.fd.write(PinVal)
            self.fd.flush()
        except Exception as e:
            logging.error("Can't write to file " + str(self.file_value) + " - this event will be skipped: " + ': Message: ' + format(e) )

        logging.debug('Pin ' +str(self.name)+ ' value set to  "' + str(PinVal) + '"')



        
 

        #client.publish( self.OutTopicName, self.OutPayload)