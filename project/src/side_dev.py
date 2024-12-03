import numpy as np
from wb_side_io import MCP23017
from wb_side_io import DO_LEAD_ADR, DI_LEAD_ADR
from wb_side_io import DO_ADR_RANGE, DI_ADR_RANGE
import paho.mqtt.client as mqtt
import logging

COMMON_TOPIC = "App/Topinator"

class CSideDev:

    def __init__(self, Adr=0, Order=0):
        self.address = np.uint8(Adr)
        self.ord = Order
        self.name = "side-device"
        self.desc = "General bus device"

    def link_to_brocker(self, client: mqtt.Client):

        common_prefix = f'{COMMON_TOPIC}/{self.name}/{self.ord}/'
        topic = f'{common_prefix}Address'
        message = str(self.address)

        msg_info = client.publish( f'{common_prefix}Address', str(self.address))
        logging.info(f'{str(msg_info)}')
        client.publish( f'{common_prefix}Name', str(self.name))
        client.publish( f'{common_prefix}Description', str(self.desc))

    def set_location(self, Adr, Order):
        self.address = np.uint8(Adr)
        self.ord = Order        

    


class CDoNum(CSideDev):

    def __init__(self, ChNum, Adr=0, Order=0):
        super().__init__(Adr, Order)
        self.ChNum = ChNum
        self.Name = f'do-general-{ChNum}'
        self.desc = "DO with configured bit depth"

    def link_to_brocker(self, client: mqtt.Client):

        common_prefix = f'{COMMON_TOPIC}/{self.name}/{self.ord}/'
        topic = f'{common_prefix}Address'
        message = str(self.address)

        msg_info = client.publish( f'{common_prefix}Address', str(self.address))
        logging.info(f'{str(msg_info)}')
        client.publish( f'{common_prefix}Name', str(self.name))
        client.publish( f'{common_prefix}Description', str(self.desc))



class CDiNum(CSideDev):

    def __init__(self, ChNum, Adr=0, Order=0):
        super().__init__(Adr, Order)
        self.ChNum = ChNum
        self.Name = f'di-general-{ChNum}'
        self.desc = "DI with configured bit depth"
