"""Higher-level utility functions."""
from contextlib import contextmanager

from samil.inverter import InverterFinder, KeepAliveInverter


@contextmanager
def connect_inverters(interface: str = '', n: int = 1):
    """Finds and connects to inverters.

    Needs to be used as context manager. Disconnects the inverters after exit
    of the with statement.
    """
    with InverterFinder(interface_ip=interface) as finder:
        inverters = [KeepAliveInverter(*finder.find_inverter()) for i in range(n)]

    try:
        yield inverters
    finally:
        for i in inverters:
            i.disconnect()
