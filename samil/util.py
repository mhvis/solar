"""Higher-level utility functions."""
import logging
from socket import socket
from time import sleep
from typing import List

from samil.inverter import Inverter, InverterListener


def create_inverter_listener(interface_ip="", retries=300, period=1.0) -> InverterListener:
    """Creates an InverterListener instance, retrying if the port is bound.

    Args:
        interface_ip: See InverterListener.
        retries: Maximum number of retries for when the listener port is bound.
        period: Period between retries.
    """
    tries = 0
    while True:
        try:
            listener = InverterListener(interface_ip=interface_ip)
            return listener
        except OSError as e:
            # Reraise if the thrown error does not equal 'port already bound'
            if e.errno != 98:
                raise e
            logging.info("Listening port (1200) already in use, retrying")
            # Check for maximum number of retries
            tries += 1
            if tries >= retries:
                raise e
            sleep(period)
    # This is unreachable


def connect_to_inverters(listener: InverterListener,
                         n=1,
                         keep=None) -> List[Inverter]:
    """Connects to one or more inverters with optional filtering.

    Args:
        listener: Inverter listener used for connecting.
        n: Continue searching until n filtered inverters are found.
        keep: Function that should return True or False depending on whether
            the inverter should be kept/filtered or not. If None, no filter
            will be applied.
    """
    inverters = []
    discard = []
    while len(inverters) < n:
        inverter = listener.accept_inverter()
        if keep is None or keep(inverter):
            inverters.append(inverter)
        else:
            logging.info("Inverter at address %s is discarded", inverter.addr)
            discard.append(inverter)
    # Disconnect discarded so that they can directly be reconnected to
    for inv in discard:
        inv.disconnect()

    return inverters


class KeepAliveInverter(Inverter):
    """Inverter that is kept alive by sending a request every couple seconds."""

    @classmethod
    def from_inverter(cls, inverter: Inverter):
        pass


    def __init__(self, sock: socket, addr):
        """See base class.


        """
        super().__init__(sock, addr)
