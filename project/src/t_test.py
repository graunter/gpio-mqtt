import pytest
import main as tp

def test_first():
    print('T First')

def test_second(capfd):
    tp.verbose = True
    tp.debug("Dbg msg")
    out, err = capfd.readouterr()
    assert out == "Dbg msg\n\n"
    print('T2')
