from typing import Hashable, Callable
import re

from side_dev import *



# fake component factory

class ClassNotFoundError(ValueError):
    pass



class CLibirator:

    @staticmethod
    def GetByConfig(Cfg: list) -> object:
        
        if Cfg is not None:
            Name = Cfg[0]
        else:
            raise ClassNotFoundError

        if Name.startswith("do"):
            bit_num = re.compile(r'(\d+)$').search(Name).group(1)
            component = CDoNum(bit_num)
        elif Name.startswith("di"):
            bit_num = re.compile(r'(\d+)$').search(Name).group(1)
            component = CDiNum(bit_num)            
        else:
            raise ClassNotFoundError


        return component

        
