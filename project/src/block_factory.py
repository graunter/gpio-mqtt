from typing import Hashable, Callable
import re

from side_dev import *


# fake component factory

class ClassNotFoundError(ValueError):
    pass


class CLibirator:

    @staticmethod
    def GetByConfig(Cfg: list, GlobalCfg: list) -> object:
        
        if Cfg and (my_name := Cfg["type"]) is not None:
            blk_name = my_name
        else:
            raise ClassNotFoundError

        if blk_name.startswith("do"):
            bit_num = re.compile(r'(\d+)$').search(blk_name).group(1)
            component = CDoNum( int(bit_num), Cfg, GlobalCfg )
        elif blk_name.startswith("di"):
            bit_num = re.compile(r'(\d+)$').search(blk_name).group(1)
            component = CDiNum( int(bit_num), Cfg, GlobalCfg )            
        else:
            raise ClassNotFoundError


        return component

        
