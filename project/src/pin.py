import paho.mqtt.client as mqtt
import logging


class CComponent:
    def __init__(self, InTopicName: str, OutTopicName: str, Operation: str=""):
        self.name = "Mod1_K12"
        self.topic = "dev/extender/do12"
        self.changes_only = False
        self.file_value = "/sys/class/gpio/gpio563/value"
        self.fd = None
        self.type = "DO"
        self.create_empty_topic = True
        self.init = [ 
            ("/sys/class/gpio/export", "563"),
            ("/sys/class/gpio/gpio563/direction", "out")
        ]

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
                logging.debug('Create DO topic: ' + self.topic + "for pin " + self.file_value)
                #TODO

            case _:
                raise ValueError(f'Unknown pin type: {self.type}')
            

    def on_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
        PinVal = msg.payload
        
        self.check_open()
        self.fd.seek(0)
        self.fd.write(PinVal)
        self.fd.flush()



        
 

        #client.publish( self.OutTopicName, self.OutPayload)