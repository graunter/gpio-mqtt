import time
import numpy as np
from wb_side_io import MCP23017
from wb_side_io import DO_LEAD_ADR, DI_LEAD_ADR
from wb_side_io import DO_ADR_RANGE, DI_ADR_RANGE
import paho.mqtt.client as mqtt
import logging
from wb_side_io import *

COMMON_TOPIC = "App/Topinator/SideDev"

class CSideDev:

    def __init__(self, Adr=0, Order=0):
        self.address = Adr
        self.ord = Order
        self.name = "side-device"
        self.desc = "General bus device"
        self.broker_client = None

    def link_to_broker(self, client: mqtt.Client, common_prefix=None):

        if not common_prefix:
            common_prefix = f'{COMMON_TOPIC}/{self.ord}/'

        #TODO: all messages should be posted - may be group all to one packet
        #TODO: verify the response
        msg_info = client.publish( f'{common_prefix}Address', str(self.address))
        client.publish( f'{common_prefix}Name', str(self.name))
        client.publish( f'{common_prefix}Description', str(self.desc))

    def set_location(self, i2c, Adr, Order):
        self.address = Adr
        self.ord = Order        
        self.i2c = i2c

    def hw_init(self):
        pass

    def upd_state(self):
        pass


class CDoNum(CSideDev):

    def __init__(self, ChNum, Adr=0, Order=0):
        super().__init__(Adr, Order)
        self.ChNum = ChNum
        self.name = f'do-general-{ChNum}'
        self.desc = "DO with configured bit depth"
        self.state = [LOW]*ChNum

    def hw_init(self):
         
        self.hw = MCP23017(self.address, self.i2c, MCP23017.IO_type_enum.e_DO)
        self.hw.set_all_output()

        for one_pin in ALL_GPIO:
            self.hw.digital_write(one_pin, LOW)
           

    def link_to_broker(self, client: mqtt.Client):

        self.broker_client = client

        common_prefix = f'{COMMON_TOPIC}/{self.ord}/'
        super().link_to_broker(client, common_prefix)

        client.publish( f'{common_prefix}State', f'{self.state}' )

        pin_cnt = 1
        for one_pin in self.state:
            client.publish( f'{common_prefix}State/{str(pin_cnt)}', f'{one_pin}' )

            set_topic = f'{common_prefix}State/{str(pin_cnt)}/Set'
            client.message_callback_add( f'{set_topic}', self.on_set_msg)
            client.publish( f'{set_topic}', "" )
            client.subscribe( f'{set_topic}', 0)

            clr_topic = f'{common_prefix}State/{str(pin_cnt)}/Clr'
            client.message_callback_add( f'{clr_topic}', self.on_clr_msg)
            client.publish( f'{clr_topic}', "" )
            client.subscribe( f'{clr_topic}', 0)

            pin_cnt += 1


    def on_set_msg(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):

        if not msg.payload.decode("utf-8"):
            return
        
        pin_num = int(msg.topic.split("/")[-2])

        self.hw.digital_write(ALL_GPIO[pin_num-1], HIGH)

        common_prefix = f'{COMMON_TOPIC}/{self.ord}/'
        client.publish( f'{common_prefix}State/{str(pin_num)}', "HIGH" )

        set_topic = f'{common_prefix}State/{str(pin_num)}/Set'
        client.publish( f'{set_topic}', None )

    def on_clr_msg(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):

        if not msg.payload.decode("utf-8"):
            return

        pin_num = int(msg.topic.split("/")[-2])

        self.hw.digital_write(ALL_GPIO[pin_num-1], LOW)

        common_prefix = f'{COMMON_TOPIC}/{self.ord}/'
        client.publish( f'{common_prefix}State/{str(pin_num)}', "LOW" )

        clr_topic = f'{common_prefix}State/{str(pin_num)}/Clr'
        client.publish( f'{clr_topic}', None )



class CDiNum(CSideDev):

    def __init__(self, ChNum, Adr=0, Order=0):
        super().__init__(Adr, Order)
        self.ch_num = ChNum
        self.name = f'di-general-{ChNum}'
        self.desc = "DI with configured bit depth"
        self.state = [LOW]*ChNum

    def hw_init(self):
         
        self.hw = MCP23017(self.address, self.i2c, MCP23017.IO_type_enum.e_DI)
        # TODO: stoped here  
        # self.hw.write()
        self.hw.set_all_input()
        self.state = self.hw.digital_read_all()

    def link_to_broker(self, client: mqtt.Client):

        self.broker_client = client
        
        common_prefix = f'{COMMON_TOPIC}/{self.ord}/'

        super().link_to_broker(client, common_prefix)

        client.publish( f'{common_prefix}State', f'{self.state}' )

    def upd_state(self):
        state = self.hw.digital_read_all()

        next_state = []
        bit_cnt = self.ch_num
        for one_byte in state:
            for i in range(8):
                if not bit_cnt: break
                next_state.append(one_byte >> i & 1)
                bit_cnt -= 1

        self.state = next_state

        common_prefix = f'{COMMON_TOPIC}/{self.ord}/'
        self.broker_client.publish( f'{common_prefix}State', f'{self.state}' )
