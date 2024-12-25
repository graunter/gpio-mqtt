import datetime
from threading import Thread
import time
import numpy as np
from wb_side_io import MCP23017
from wb_side_io import DO_LEAD_ADR, DI_LEAD_ADR
from wb_side_io import DO_ADR_RANGE, DI_ADR_RANGE
import paho.mqtt.client as mqtt
import logging
from wb_side_io import *
from constants import *


class CSideDev:

    def __init__(self, Cfg: list=[], GlobalCfg: list=[], Adr=0, Order=0):
        self.address = Adr
        self.ord = Order
        self.name = "side-device"
        self.desc = "General bus device"
        self.broker_client = None
        self.common_prefix = ""     # cached value
        self.pause_rep_fl = True
        self.pull_theblock_thrd = None

        self.glob_cfg = GlobalCfg
        self.cfg = Cfg
        self.pin_names = {}
        self.set_topics = {}
        self.clr_topics = {}
        self.re_names = {}
        self.read_time = 0

    def link_to_broker(self, client: mqtt.Client):

        if not self.glob_cfg.get("common_path"):
            self.glob_cfg["common_path"] = DEFAULT_COMMON_PATH_TOPIC

        if not self.cfg.get("control_path"):
            self.cfg["control_path"] = str(self.ord)

        self.common_prefix = f'{self.glob_cfg["common_path"]}/{self.cfg["control_path"]}'

        for one_pin in self.cfg.get("pins", []):
            if not (pin_num := one_pin["num"]):
                logging.error(f'pin configuration for {self.cfg["cfg_pos_cnt"]} is not correct - scipped') 
                break
            self.pin_names[pin_num] = one_pin.get("name", str(pin_num))
            self.set_topics[pin_num] = one_pin.get("set_path", "set")
            self.clr_topics[pin_num] = one_pin.get("clr_path", "clr")

        #TODO: all messages should be posted - may be group all to one packet
        #TODO: verify the response
        msg_info = client.publish( f'{self.common_prefix}/Address', str(self.address))
        client.publish( f'{self.common_prefix}/Name', str(self.name))
        client.publish( f'{self.common_prefix}/Description', str(self.desc))

        
        if self.cfg.get("repetition_time_sec", 0) > 0:
            self.pause_rep_fl = False
            if not self.pull_theblock_thrd:
                self.pull_theblock_thrd = Thread(target=self.on_theblock_pool)
                self.pull_theblock_thrd.daemon = True
                self.pull_theblock_thrd.start() 

    def on_theblock_pool(self):
        while True:
            time.sleep( self.cfg.get("repetition_time_sec") )
            if not self.pause_rep_fl:
                self.send_state()


    def set_location(self, i2c, Adr, Order):
        self.address = Adr
        self.ord = Order        
        self.i2c = i2c

    def hw_init(self):
        pass

    def upd_state(self):
        return False

    def send_state(self):
        pass


class CDoNum(CSideDev):

    def __init__(self, ChNum, Cfg: list=[], GlobalCfg: list=[], Adr=0, Order=0):
        super().__init__(Cfg, GlobalCfg, Adr, Order)
        self.ch_num = ChNum
        self.name = f'do-general-{ChNum}'
        self.desc = "DO with configured bit depth"
        self.state = [LOW]*ChNum
        self.hw_state = 0


    def hw_init(self):
         
        self.hw = MCP23017(self.address, self.i2c, MCP23017.IO_type_enum.e_DO)
        self.hw.check_chip_type()
        self.hw.set_all_output()
        self.read_time = datetime.datetime.now()

        # TODO: state should be restored here
        self.hw.set_all_output_to_zero()
           

    def link_to_broker(self, client: mqtt.Client):

        self.broker_client = client

        super().link_to_broker(client)

        pin_cnt = 1
        for one_pin in self.state:
            if pin_cnt not in self.pin_names.keys():
                self.pin_names[pin_cnt] = str(pin_cnt)    

            if pin_cnt not in self.set_topics.keys():
                self.set_topics[pin_cnt] = "set"

            if pin_cnt not in self.clr_topics.keys():
                self.clr_topics[pin_cnt] = "clr"     

            pin_topic = self.pin_names[pin_cnt]

            set_topic = f'{self.common_prefix}/State/{pin_topic}/{self.set_topics[pin_cnt]}'
            self.broker_client.message_callback_add( set_topic, self.on_set_msg)
            self.broker_client.publish( set_topic, "" )
            self.broker_client.subscribe( set_topic, 0)

            clr_topic = f'{self.common_prefix}/State/{pin_topic}/{self.clr_topics[pin_cnt]}'
            self.broker_client.message_callback_add( f'{clr_topic}', self.on_clr_msg)
            self.broker_client.publish( f'{clr_topic}', "" )
            self.broker_client.subscribe( f'{clr_topic}', 0)

            pin_cnt += 1

        self.re_names = dict((v,k) for k,v in self.pin_names.items())

        self.send_state()

    def upd_state(self):
        
        state = self.hw.digital_read_all()
        self.read_time = datetime.datetime.now()

        next_state = []
        bit_cnt = 1
        for one_byte in state:
            for i in range(8):
                if bit_cnt > self.ch_num: break
                this_bit = one_byte >> i & 1
                next_state.append(this_bit)

                #self.broker_client.publish( f'{self.common_prefix}/State/{self.pin_names[bit_cnt]}', f'{this_bit}' )
                bit_cnt += 1

        ret = (set(self.state) != set(next_state))
        self.state = next_state
        return ret

    def send_state(self):

        self.broker_client.publish( f'{self.common_prefix}/State', f'{self.state}' )
        self.broker_client.publish( f'{self.common_prefix}/Time', f'{self.read_time}' )

        pin_cnt = 1
        for one_pin in self.state:

            pin_topic = self.pin_names[pin_cnt]
            self.broker_client.publish( f'{self.common_prefix}/State/{pin_topic}', f'{one_pin}' )

            pin_cnt += 1


    def on_set_msg(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):

        if not msg.payload.decode("utf-8"):
            return
        
        in_pin_name = msg.topic.split("/")[-2]

        if in_pin_name in self.re_names.keys():
            pin_num = self.re_names[in_pin_name]
        else:
            logging.error(f'pin name=={in_pin_name} for set op is wrong - scipped') 
            return

        self.hw.digital_write(ALL_GPIO[pin_num-1], HIGH)

        client.publish( f'{self.common_prefix}/State/{self.pin_names[pin_num]}', "HIGH" )
        self.state[pin_num] = 1
        self.broker_client.publish( f'{self.common_prefix}/State', f'{self.state}' )
        self.broker_client.publish( f'{self.common_prefix}/Time', f'{self.read_time}' )

        set_topic = f'{self.common_prefix}/State/{self.pin_names[pin_num]}/{self.set_topics[pin_num]}'
        client.publish( set_topic, None )

    def on_clr_msg(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):

        if not msg.payload.decode("utf-8"):
            return

        in_pin_name = msg.topic.split("/")[-2]

        if in_pin_name in self.re_names.keys():
            pin_num = self.re_names[in_pin_name]
        else:
            logging.error(f'pin name=={in_pin_name} for clear op is wrong - scipped') 
            return

        self.hw.digital_write(ALL_GPIO[pin_num-1], LOW)

        client.publish( f'{self.common_prefix}/State/{self.pin_names[pin_num]}', "LOW" )
        self.state[pin_num] = 0
        self.broker_client.publish( f'{self.common_prefix}/State', f'{self.state}' )
        self.broker_client.publish( f'{self.common_prefix}/Time', f'{self.read_time}' )

        clr_topic = f'{self.common_prefix}/State/{self.pin_names[pin_num]}/{self.clr_topics[pin_num]}'
        client.publish( clr_topic, None )



class CDiNum(CSideDev):

    def __init__(self, ChNum, Cfg: list=[], GlobalCfg: list=[], Adr=0, Order=0):
        super().__init__(Cfg, GlobalCfg, Adr, Order)
        self.ch_num = ChNum
        self.name = f'di-general-{ChNum}'
        self.desc = "DI with configured bit depth"
        self.state = [LOW]*ChNum

    def hw_init(self):
         
        self.hw = MCP23017(self.address, self.i2c, MCP23017.IO_type_enum.e_DI)
        self.hw.check_chip_type()
        # TODO: stoped here  
        # self.hw.write()
        self.hw.set_all_input()
        hw_state = self.hw.digital_read_all()
        self.read_time = datetime.datetime.now()

    def link_to_broker(self, client: mqtt.Client):

        self.broker_client = client

        super().link_to_broker(client)

        pin_cnt = 1
        for one_pin in self.state:

            if pin_cnt not in self.pin_names.keys():
                self.pin_names[pin_cnt] = str(pin_cnt)

            #pin_topic = self.pin_names[pin_cnt]
            #client.publish( f'{self.common_prefix}/State/{pin_topic}', f'{one_pin}' )

            pin_cnt += 1

        self.re_names = dict((v,k) for k,v in self.pin_names.items())

        self.send_state()

    def upd_state(self):
        state = self.hw.digital_read_all()
        self.read_time = datetime.datetime.now()

        next_state = []
        bit_cnt = 1
        for one_byte in state:
            for i in range(8):
                if bit_cnt > self.ch_num: break
                this_bit = one_byte >> i & 1
                next_state.append(this_bit)

                #self.broker_client.publish( f'{self.common_prefix}/State/{self.pin_names[bit_cnt]}', f'{this_bit}' )
                bit_cnt += 1

        ret = (set(self.state) != set(next_state))
        self.state = next_state
        return ret


    def send_state(self):

        self.broker_client.publish( f'{self.common_prefix}/State', f'{self.state}' )
        self.broker_client.publish( f'{self.common_prefix}/Time', f'{self.read_time}' )

        for position, this_bit in enumerate(self.state):
            self.broker_client.publish( f'{self.common_prefix}/State/{self.pin_names[position+1]}', f'{this_bit}' )

