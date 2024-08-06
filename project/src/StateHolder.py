from common import MySingletone
from constants import *
from pathlib import Path
import logging
import os


class StateHolder(metaclass=MySingletone):

    def __init__(self) -> None:
        pass

    def save(self, state: str, name: str):

        data_file_name = os.path.join(VAR_PATH, COMMON_PATH, name)

        try:
            os.makedirs(os.path.dirname(data_file_name), exist_ok=True)

            with open(data_file_name, "w") as data_f:
                data_f.write(state)
  
        except Exception as e:
            logging.error("Can't open file" + str(data_file_name) + " - state not saved: " + ': Message: ' + format(e) )
            pass     

    def load(self, name: str) -> str:

        data_file_name = os.path.join(VAR_PATH, COMMON_PATH, name)

        with open(data_file_name, "r") as data_f:
            state = data_f.read()
            return state

