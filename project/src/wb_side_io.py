import enum
from i2c import I2C
import numpy as np
#pip install --upgrade pip
#apt install cmake
import smbus ## pip install smbus-cffi
import logging


IODIRA   = 0x00  # Pin direction register
IODIRB   = 0x01  # Pin direction register
IPOLA    = 0x02
IPOLB    = 0x03
GPINTENA = 0x04
GPINTENB = 0x05
DEFVALA  = 0x06
DEFVALB  = 0x07
INTCONA  = 0x08
INTCONB  = 0x09
IOCONA   = 0x0A
IOCONB   = 0x0B
GPPUA    = 0x0C
GPPUB    = 0x0D

INTFA    = 0x0E
INTFB    = 0x0F
INTCAPA  = 0x10
INTCAPB  = 0x11
GPIOA    = 0x12
GPIOB    = 0x13
OLATA    = 0x14
OLATB    = 0x15
ALL_OFFSET = [IODIRA, IODIRB, IPOLA, IPOLB, GPINTENA, GPINTENB, DEFVALA, DEFVALB, INTCONA, INTCONB, IOCONA, IOCONB, GPPUA, GPPUB, GPIOA, GPIOB, OLATA, OLATB]

BANK_BIT    = 7
MIRROR_BIT  = 6
SEQOP_BIT   = 5
DISSLW_BIT  = 4
HAEN_BIT    = 3
ODR_BIT     = 2
INTPOL_BIT  = 1

GPA0 = 0
GPA1 = 1
GPA2 = 2
GPA3 = 3
GPA4 = 4
GPA5 = 5
GPA6 = 6
GPA7 = 7
GPB0 = 8
GPB1 = 9
GPB2 = 10
GPB3 = 11
GPB4 = 12
GPB5 = 13
GPB6 = 14
GPB7 = 15
ALL_GPIO = [GPA0, GPA1, GPA2, GPA3, GPA4, GPA5, GPA6, GPA7, GPB0, GPB1, GPB2, GPB3, GPB4, GPB5, GPB6, GPB7]

HIGH = 0xFF
LOW = 0x00

INPUT = 0xFF
OUTPUT = 0x00

DO_LEAD_ADR = 0x20
DO_ADR_RANGE = [0x20, 0x21, 0x22, 0x24]
DI_LEAD_ADR = 0x27
DI_ADR_RANGE = [ 0x27, 0x26, 0x25, 0x23 ]
DI_HW_ADR_RANGE = [0b111, 0b110, 0b101, 0b011]

ADR_MASK = 0b0111
ADR_PRFX = 0b0100
ADR_PRFX_OFFSET = 3
ADR_HEAD = ADR_PRFX << ADR_PRFX_OFFSET


class MCP23017:
	"""
	MCP23017 class to handle ICs register setup

	RegName  |ADR | bit7    | bit6   | bit5   | bit4   | bit3   | bit2   | bit1   | bit0   | POR/RST
	--------------------------------------------------------------------------------------------------
	IODIRA   | 00 | IO7     | IO6    | IO5    | IO4    | IO3    | IO2    | IO1    | IO0    | 1111 1111
	IODIRB   | 01 | IO7     | IO6    | IO5    | IO4    | IO3    | IO2    | IO1    | IO0    | 1111 1111
	IPOLA    | 02 | IP7     | IP6    | IP5    | IP4    | IP3    | IP2    | IP1    | IP0    | 0000 0000
	IPOLB    | 03 | IP7     | IP6    | IP5    | IP4    | IP3    | IP2    | IP1    | IP0    | 0000 0000
	GPINTENA | 04 | GPINT7  | GPINT6 | GPINT5 | GPINT4 | GPINT3 | GPINT2 | GPINT1 | GPINT0 | 0000 0000
	GPINTENB | 05 | GPINT7  | GPINT6 | GPINT5 | GPINT4 | GPINT3 | GPINT2 | GPINT1 | GPINT0 | 0000 0000
	DEFVALA  | 06 | DEF7    | DEF6   | DEF5   | DEF4   | DEF3   | DEF2   | DEF1   | DEF0   | 0000 0000
	DEFVALB  | 07 | DEF7    | DEF6   | DEF5   | DEF4   | DEF3   | DEF2   | DEF1   | DEF0   | 0000 0000
	INTCONA  | 08 | IOC7    | IOC6   | IOC5   | IOC4   | IOC3   | IOC2   | IOC1   | IOC0   | 0000 0000
	INTCONB  | 09 | IOC7    | IOC6   | IOC5   | IOC4   | IOC3   | IOC2   | IOC1   | IOC0   | 0000 0000
	IOCON    | 0A | BANK    | MIRROR | SEQOP  | DISSLW | HAEN   | ODR    | INTPOL | -      | 0000 0000
	IOCON    | 0B | BANK    | MIRROR | SEQOP  | DISSLW | HAEN   | ODR    | INTPOL | -      | 0000 0000
	GPPUA    | 0C | PU7     | PU6    | PU5    | PU4    | PU3    | PU2    | PU1    | PU0    | 0000 0000
	GPPUB    | 0D | PU7     | PU6    | PU5    | PU4    | PU3    | PU2    | PU1    | PU0    | 0000 0000


	"""

	@enum.unique
	class IO_type_enum(enum.Enum):
		e_DI = 0
		e_DO = 1
		e_unknown = 3

	def __init__(self, address, i2c: I2C, io_type: IO_type_enum):
		self.i2c = i2c
		self.address = np.uint8(address)
		self.type = io_type

	def set_all_output(self):
		""" sets all GPIOs as OUTPUT"""
		self.i2c.write_to(self.address, IODIRA, 0x00)
		self.i2c.write_to(self.address, IODIRB, 0x00)

	def set_all_input(self):
		""" sets all GPIOs as INPUT"""
		self.i2c.write_to(self.address, IODIRA, 0xFF)
		self.i2c.write_to(self.address, IODIRB, 0xFF)

	def pin_mode(self, gpio, mode):
		"""
		Sets the given GPIO to the given mode INPUT or OUTPUT
		:param gpio: the GPIO to set the mode to
		:param mode: one of INPUT or OUTPUT
		"""
		pair = self.get_offset_gpio_tuple([IODIRA, IODIRB], gpio)
		self.set_bit_enabled(pair[0], pair[1], True if mode is INPUT else False)

	def digital_write(self, gpio, direction):
		"""
		Sets the given GPIO to the given direction HIGH or LOW
		:param gpio: the GPIO to set the direction to
		:param direction: one of HIGH or LOW
		"""
		pair = self.get_offset_gpio_tuple([OLATA, OLATB], gpio)
		self.set_bit_enabled(pair[0], pair[1], True if direction is HIGH else False)

	def digital_read(self, gpio):
		"""
		Reads the current direction of the given GPIO
		:param gpio: the GPIO to read from
		:return:
		"""
		pair = self.get_offset_gpio_tuple([GPIOA, GPIOB], gpio)
		bits = self.i2c.read_from(self.address, pair[0])
		return HIGH if (bits & (1 << pair[1])) > 0 else LOW

	def digital_read_all(self):
		"""
		Reads the current direction of the given GPIO
		:param gpio: the GPIO to read from
		:return:
		"""
		return [self.i2c.read_from(self.address, GPIOA),
		        self.i2c.read_from(self.address, GPIOB)]

	def set_interrupt(self, gpio, enabled):
		"""
		Enables or disables the interrupt of a given GPIO
		:param gpio: the GPIO where the interrupt needs to be set, this needs to be one of GPAn or GPBn constants
		:param enabled: enable or disable the interrupt
		"""
		pair = self.get_offset_gpio_tuple([GPINTENA, GPINTENB], gpio)
		self.set_bit_enabled(pair[0], pair[1], enabled)

	def set_all_interrupt(self, enabled):
		"""
		Enables or disables the interrupt of a all GPIOs
		:param enabled: enable or disable the interrupt
		"""
		self.i2c.write_to(self.address, GPINTENA, 0xFF if enabled else 0x00)
		self.i2c.write_to(self.address, GPINTENB, 0xFF if enabled else 0x00)

	def set_interrupt_mirror(self, enable):
		"""
		Enables or disables the interrupt mirroring
		:param enable: enable or disable the interrupt mirroring
		"""
		self.set_bit_enabled(IOCONA, MIRROR_BIT, enable)
		self.set_bit_enabled(IOCONB, MIRROR_BIT, enable)

	def read_interrupt_captures(self):
		"""
		Reads the interrupt captured register. It captures the GPIO port value at the time the interrupt occurred.
		:return: a tuple of the INTCAPA and INTCAPB interrupt capture as a list of bit string
		"""
		return (self._get_list_of_interrupted_values_from(INTCAPA),
		        self._get_list_of_interrupted_values_from(INTCAPB))

	def _get_list_of_interrupted_values_from(self, offset):
		list = []
		interrupted = self.i2c.read_from(self.address, offset)
		bits = '{0:08b}'.format(interrupted)
		for i in reversed(range(8)):
			list.append(bits[i])

		return list

	def read_interrupt_flags(self):
		"""
		Reads the interrupt flag which reflects the interrupt condition. A set bit indicates that the associated pin caused the interrupt.
		:return: a tuple of the INTFA and INTFB interrupt flags as list of bit string
		"""
		return (self._read_interrupt_flags_from(INTFA),
		        self._read_interrupt_flags_from(INTFB))

	def _read_interrupt_flags_from(self, offset):
		list = []
		interrupted = self.i2c.read_from(self.address, offset)
		bits = '{0:08b}'.format(interrupted)
		for i in reversed(range(8)):
			list.append(bits[i])

		return list

	def read(self, offset):
		return self.i2c.read_from(self.address, offset)

	def write(self, offset, value):
		return self.i2c.write_to(self.address, offset, value)

	def get_offset_gpio_tuple(self, offsets, gpio):
		if offsets[0] not in ALL_OFFSET or offsets[1] not in ALL_OFFSET:
			raise TypeError("offsets must contain a valid offset address. See description for help")
		if gpio not in ALL_GPIO:
			raise TypeError("pin must be one of GPAn or GPBn. See description for help")

		offset = offsets[0] if gpio < 8 else offsets[1]
		_gpio = gpio % 8
		return (offset, _gpio)

	def set_bit_enabled(self, offset, gpio, enable):
		stateBefore = self.i2c.read_from(self.address, offset)
		value = (stateBefore | self.bitmask(gpio)) if enable else (stateBefore & ~self.bitmask(gpio))
		self.i2c.write_to(self.address, offset, value)

	def bitmask(self, gpio):
		return 1 << (gpio % 8)
	
	@staticmethod
	def get_ord_adr_list(last_adr_lst: list) -> list:
		
		adr_list = []

		if DO_LEAD_ADR in last_adr_lst:
			cur_adr = DO_LEAD_ADR
			cur_type = MCP23017.IO_type_enum.e_DO
		elif DI_LEAD_ADR in last_adr_lst:
			cur_adr = DI_LEAD_ADR
			cur_type = MCP23017.IO_type_enum.e_DI			
		else:
			return adr_list
		
		adr_list.append(np.uint8(cur_adr))
		last_adr_lst.remove(cur_adr)

		while len(last_adr_lst) != 0:
			cur_hw_adr = np.uint8(ADR_MASK & cur_adr)
			if cur_type == MCP23017.IO_type_enum.e_DI:
				cur_hw_adr = ADR_MASK & (~ np.uint8(cur_hw_adr))

			next_adr = 0
			if cur_hw_adr == 0:
				next_hw_adr = np.uint8(1)
			elif cur_hw_adr == 4:
				next_hw_adr	= np.uint8(0)
			else:
				next_hw_adr = np.uint8(ADR_MASK & (cur_hw_adr << 1 ))

			if next_adr == 0:
				next_adr = ADR_HEAD | next_hw_adr

			if next_adr in last_adr_lst:
				last_adr_lst.remove(next_adr)
				adr_list.append(next_adr)
				cur_adr = next_adr
			else:
				# lets try DI module
				next_hw_adr = ADR_MASK & (~ np.uint8(next_hw_adr) )
				next_adr = ADR_HEAD | next_hw_adr

				if next_adr in last_adr_lst:
					last_adr_lst.remove(next_adr)
					adr_list.append(next_adr)
					cur_adr = next_adr				
				else:
					return adr_list
			
			# Dx -> Dy
			if cur_adr in DO_ADR_RANGE:
				cur_type = MCP23017.IO_type_enum.e_DO
			elif next_adr in DI_ADR_RANGE:
				cur_type = MCP23017.IO_type_enum.e_DI
			else:
				logging.error(f'Wrong I2C addresses: {map(hex, next_adr)}')
				return 0
				
		return adr_list


	def get_next_mod_adr(self):

		adr_lst = self.i2c.get_current_adr_list()

		ord_lst = MCP23017.get_ord_adr_list( adr_lst )

		self_pos = ord_lst.index( self.address)
		
		next_pos = self_pos + 1

		return ord_lst[next_pos] if next_pos != len(ord_lst) else 0


if __name__ == "__main__":
		
        wbus = I2C(smbus.SMBus(1))
        # looking for DO
        devs_adr = wbus.scan()
        logging.info(f'Side I2C addresses were found: {list(map(hex, devs_adr))}')

        test_lst = MCP23017.get_ord_adr_list( wbus.get_current_adr_list() )

        logging.info(f'Side modules ordered by address: {list(map(hex, test_lst))}')
        logging.info(f'Stop')
