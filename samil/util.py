"""Higher-level utility functions."""
import logging
from socket import socket
from threading import Event, Thread
from time import sleep
from typing import List, Tuple

from samil.inverter import Inverter, InverterFinder


def get_bound_inverter_finder(interface_ip="", retries=300, period=1.0) -> InverterFinder:
    """Creates an InverterFinder, retrying if the port is already bound.

    Args:
        interface_ip: See InverterListener.
        retries: Maximum number of retries for when the listener port is bound.
        period: Period between retries.

    Raises:
        OSError: When all tries failed.
    """
    tries = 0
    while True:
        finder = InverterFinder(interface_ip=interface_ip)
        try:
            finder.listen()
            return finder
        except OSError as e:
            # Reraise if the thrown error does not equal 'port already bound'
            if e.errno != 98:
                raise e
            # Prevent ResourceWarning (unclosed socket)
            finder.close()
            logging.info("Listening port (1200) already in use, retrying")
            # Check for maximum number of retries
            tries += 1
            if tries >= retries:
                raise e
            sleep(period)
    # This is unreachable


def connect_to_inverters(finder: InverterFinder,
                         n=1,
                         keep=None) -> List[Inverter]:
    """Connects to one or more inverters with optional filtering.

    Args:
        finder: InverterFinder used for searching.
        n: Continue searching until n filtered inverters are found.
        keep: Function that should return True or False depending on whether
            the inverter should be kept/filtered or not. If None, no filter
            will be applied.
    """
    inverters = []
    discard = []
    while len(inverters) < n:
        inverter = KeepAliveInverter(*finder.find_inverter())
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
    """Inverter that is kept alive by sending a request every couple seconds.

    Keep-alive messages are only sent when the last sent message became too
    long ago. When the program makes requests quicker than the keep-alive
    period, no keep-alive messages will be sent.
    """

    def __init__(self, sock: socket, addr, keep_alive: float = 11.0):
        """See base class.

        Args:
            sock: The inverter socket, which is assumed to be connected.
            addr: The inverter network address.
            keep_alive: Maximum time since last message before a keep-alive
                message is triggered. The default of 11 seconds is chosen such
                that keep-alive messages will not be sent when status is
                retrieved every 10 seconds.
        """
        super().__init__(sock, addr)
        self.keep_alive_period = keep_alive
        self.keep_alive_timer = None

        self._ka_thread = None  # Keep-alive thread
        self._ka_stop = Event()  # Used for stopping keep-alive messages
        self.start_keep_alive()

    def stop_keep_alive(self) -> None:
        """Stops the periodic keep-alive messages.

        Blocks for a moment if a keep-alive request is currently being handled.
        """
        if not self._ka_thread:
            return  # No-op if already stopped
        self._ka_stop.set()
        self._ka_thread.join()
        self._ka_thread = None

    def start_keep_alive(self):
        """Starts sending keep-alive messages periodically."""
        if self._ka_thread:
            raise RuntimeError("Keep-alive thread already exists")
        self._ka_stop.clear()
        self._ka_thread = Thread(target=self._ka_runner, daemon=True)
        self._ka_thread.start()

    def _ka_runner(self):
        """Sends a keep-alive periodically until stopped."""
        while True:
            # stopped will be False when the timeout occurred
            stopped = self._ka_stop.wait(timeout=self.keep_alive_period)
            if stopped:
                return
            self.keep_alive()

    def keep_alive(self):
        """Sends a keep-alive message."""
        # We have to call the superclass because self.send/self.receive
        #  interfere with the keep-alive runner.
        super().send(b"\x01\x02\x02", b"")  # Status message
        # super().send(b"\x01\x09\x02", b"")  # Unknown message
        super().receive()

    def send(self, identifier: bytes, payload: bytes):
        """See base class."""
        self.stop_keep_alive()
        super().send(identifier, payload)
        self.start_keep_alive()

    def receive(self) -> Tuple[bytes, bytes]:
        """See base class."""
        self.stop_keep_alive()
        msg = super().receive()
        self.start_keep_alive()
        return msg

    def disconnect(self):
        """See base class."""
        self.stop_keep_alive()
        super().disconnect()
