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
import enum
from StateHolder import StateHolder


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

        #TODO: all messages should be posted - may be group all to one packet
        #TODO: verify the response
        msg_info = client.publish( f'{self.common_prefix}/Address', str(self.address))
        msg_info = client.publish( f'{self.common_prefix}/Order', str(self.ord))
        msg_info = client.publish( f'{self.common_prefix}/Name', str(self.name))
        msg_info = client.publish( f'{self.common_prefix}/Description', str(self.desc))
        
        if self.cfg.get("repetition_time_sec", 0) > 0:
            self.pause_rep_fl = False
            if not self.pull_theblock_thrd:
                self.pull_theblock_thrd = Thread(target=self.on_theblock_pull)
                self.pull_theblock_thrd.daemon = True
                self.pull_theblock_thrd.start() 

    def on_theblock_pull(self):
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

    @enum.unique
    class start_state_enum(enum.Enum):
        e_Lo = 0
        e_Hi = 1
        e_Re = 2
        e_None = 3

    def __init__(self, ChNum, Cfg: list=[], GlobalCfg: list=[], Adr=0, Order=0):
        super().__init__(Cfg, GlobalCfg, Adr, Order)
        self.ch_num = ChNum
        self.name = f'do-general-{ChNum}'
        self.desc = "DO with configured bit depth"
        self.state = dict.fromkeys(range(1, ChNum), False)
        self.hw_state = 0
        self.invert = dict.fromkeys(range(1, ChNum), False)
        self.start_state = dict.fromkeys(range(1, ChNum), CDoNum.start_state_enum.e_None)


    def hw_init(self):
         
        self.hw = MCP23017(self.address, self.i2c, MCP23017.IO_type_enum.e_DO)
        self.hw.fix_protocol()
        self.hw.set_all_output()
        self.read_time = datetime.datetime.now()

        # TODO: state should be restored here
        #self.hw.set_all_output_to_zero()

        for one_pin in self.cfg.get("pins", []):
            if not (pin_num := one_pin["num"]):
                logging.error(f'pin configuration for {self.name} is not correct - scipped') 
                break

            self.invert[pin_num] = one_pin.get("invert", False)
            self.start_state[pin_num] = one_pin.get("start_state", CDoNum.start_state_enum.e_None)
                      
        storage = StateHolder()

        for one_pin_num, one_pin_state in self.start_state.items():

            if one_pin_state == CDoNum.start_state_enum.e_Lo:
                this_real_bit = HIGH if self.invert[one_pin_num] else LOW
                self.hw.digital_write(ALL_GPIO[pin_num-1], this_real_bit)    
            elif one_pin_state == CDoNum.start_state_enum.e_Hi:   
                this_real_bit = LOW if self.invert[one_pin_num] else HIGH
                self.hw.digital_write(ALL_GPIO[pin_num-1], this_real_bit)   
            elif one_pin_state == CDoNum.start_state_enum.e_Re:           
                self.PinVal = storage.load(f'{str(self.ord)}-{one_pin_num}')
            elif one_pin_state == CDoNum.start_state_enum.e_None:  
                pass
            else:
                logging.error(f'{self.name} wrong value for state enum') 


    def link_to_broker(self, client: mqtt.Client):

        self.broker_client = client

        super().link_to_broker(client)

        for one_pin in self.cfg.get("pins", []):
            if not (pin_num := one_pin["num"]):
                logging.error(f'pin configuration for {self.name} is not correct - scipped') 
                break
            self.set_topics[pin_num] = one_pin.get("set_path", "set")
            self.clr_topics[pin_num] = one_pin.get("clr_path", "clr")
            #self.invert[pin_num] = one_pin.get("invert", False)
            #self.start_state[pin_num] = one_pin.get("start_state", CDoNum.start_state_enum.e_None)


        pin_cnt = 1
        for one_pin in self.state:
            if pin_cnt not in self.pin_names.keys():
                self.pin_names[pin_cnt] = str(pin_cnt)    

            if pin_cnt not in self.set_topics.keys():
                self.set_topics[pin_cnt] = "set"

            if pin_cnt not in self.clr_topics.keys():
                self.clr_topics[pin_cnt] = "clr"    

            if pin_cnt not in self.start_state.keys():
                self.start_state[pin_cnt] = "CDoNum.start_state_enum.e_None"  

            pin_topic = self.pin_names[pin_cnt]

            # TODO: all messages should be accumulated
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
                this_real_bit = (~this_bit & 1) if self.invert[bit_cnt-1] else this_bit
                next_state.append(this_real_bit)
                bit_cnt += 1

        ret = (set(self.state) != set(next_state))
        self.state = next_state
        return ret

    def send_state(self):

        self.broker_client.publish( f'{self.common_prefix}/State', f'{self.state}' )
        self.broker_client.publish( f'{self.common_prefix}/Time', f'{self.read_time}' )

        bit_cnt = 1
        for this_bit in self.state:

            this_real_bit = (~this_bit & 1) if self.invert[bit_cnt] else this_bit

            pin_topic = self.pin_names[bit_cnt]
            self.broker_client.publish( f'{self.common_prefix}/State/{pin_topic}', f'{this_real_bit}' )

            bit_cnt += 1


    def on_set_msg(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):

        if not msg.payload.decode("utf-8"):
            return
        
        in_pin_name = msg.topic.split("/")[-2]

        if in_pin_name in self.re_names.keys():
            pin_num = self.re_names[in_pin_name]
        else:
            logging.error(f'pin name=={in_pin_name} for set op is wrong - scipped') 
            return

        this_real_bit = LOW if self.invert[pin_num-1] else HIGH
        self.hw.digital_write(ALL_GPIO[pin_num-1], this_real_bit)

        client.publish( f'{self.common_prefix}/State/{self.pin_names[pin_num]}', "HIGH" )
        self.state[pin_num] = 1
        self.broker_client.publish( f'{self.common_prefix}/State', f'{self.state}' )
        self.broker_client.publish( f'{self.common_prefix}/Time', f'{self.read_time}' )

        set_topic = f'{self.common_prefix}/State/{self.pin_names[pin_num]}/{self.set_topics[pin_num]}'
        self.broker_client.publish( set_topic, None )

        storage = StateHolder()
        storage.save(True, f'{str(self.ord)}-{pin_num}')


    def on_clr_msg(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):

        if not msg.payload.decode("utf-8"):
            return

        in_pin_name = msg.topic.split("/")[-2]

        if in_pin_name in self.re_names.keys():
            pin_num = self.re_names[in_pin_name]
        else:
            logging.error(f'pin name=={in_pin_name} for clear op is wrong - scipped') 
            return

        this_real_bit = HIGH if self.invert[pin_num-1] else LOW
        self.hw.digital_write(ALL_GPIO[pin_num-1], this_real_bit)

        client.publish( f'{self.common_prefix}/State/{self.pin_names[pin_num]}', "LOW" )
        self.state[pin_num] = 0
        self.broker_client.publish( f'{self.common_prefix}/State', f'{self.state}' )
        self.broker_client.publish( f'{self.common_prefix}/Time', f'{self.read_time}' )

        clr_topic = f'{self.common_prefix}/State/{self.pin_names[pin_num]}/{self.clr_topics[pin_num]}'
        self.broker_client.publish( clr_topic, None )

        storage = StateHolder()
        storage.save(False, f'{str(self.ord)}-{pin_num}')


class CDiNum(CSideDev):

    def __init__(self, ChNum, Cfg: list=[], GlobalCfg: list=[], Adr=0, Order=0):
        super().__init__(Cfg, GlobalCfg, Adr, Order)
        self.ch_num = ChNum
        self.name = f'di-general-{ChNum}'
        self.desc = "DI with configured bit depth"
        self.state = dict.fromkeys(range(1, ChNum), LOW)
        self.invert = dict.fromkeys(range(1, ChNum), False)

    def hw_init(self):
         
        self.hw = MCP23017(self.address, self.i2c, MCP23017.IO_type_enum.e_DI)
        self.hw.fix_protocol()
        self.upd_state()


    def link_to_broker(self, client: mqtt.Client):

        self.broker_client = client

        super().link_to_broker(client)

        for one_pin in self.cfg.get("pins", []):
            if not (pin_num := one_pin["num"]):
                logging.error(f'pin configuration for {self.name} is not correct - scipped') 
                break
            self.invert[pin_num] = one_pin.get("invert", False)

        pin_cnt = 1
        for one_pin in self.state:

            if pin_cnt not in self.pin_names.keys():
                self.pin_names[pin_cnt] = str(pin_cnt)

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
                bit_cnt += 1

        ret = (set(self.state) != set(next_state))
        self.state = next_state
        return ret


    def send_state(self):

        self.broker_client.publish( f'{self.common_prefix}/State', f'{self.state}' )
        self.broker_client.publish( f'{self.common_prefix}/Time', f'{self.read_time}' )

        for position, this_bit in enumerate(self.state):
            self.broker_client.publish( f'{self.common_prefix}/State/{self.pin_names[position+1]}', f'{this_bit}' )

