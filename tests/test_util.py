from queue import Queue
from socket import socketpair
from threading import Thread
from time import sleep
from unittest import TestCase

from samil.inverter import InverterFinder
from samil.util import get_bound_inverter_finder, KeepAliveInverter


class GetBoundInverterFinderTestCase(TestCase):
    """Test get_bound_inverter_finder function."""

    def test_exception(self):
        """Tests if OSError is thrown after all retries have failed."""
        port_blocker = InverterFinder()
        port_blocker.listen()
        with self.assertRaises(OSError):
            get_bound_inverter_finder(retries=2, period=0.01)
        port_blocker.close()

    def test_retry(self):
        """Tests if a retry happens when port is bound."""
        # Bind port
        port_blocker = InverterFinder()
        port_blocker.listen()

        # Try binding port using retry function in separate thread
        def try_bind(q: Queue):
            finder = get_bound_inverter_finder(retries=10, period=0.01)
            finder.close()
            # If bind failed, an exception should've been thrown by now
            # I assume the bind has succeeded here
            q.put(True)

        queue = Queue()
        thread = Thread(target=try_bind, args=(queue,))
        thread.start()

        # Unbind port
        sleep(0.001)
        port_blocker.close()

        # Check if bind succeeded
        thread.join()
        succeeded = queue.get(timeout=1.0)
        self.assertTrue(succeeded)


class KeepAliveInverterTestCase(TestCase):
    """Tests for KeepAliveInverter class."""

    def setUp(self) -> None:
        """Creates socket pair for local (app) and remote ('real' inverter) side."""
        local_sock, remote_sock = socketpair()
        local_sock.settimeout(1.0)
        remote_sock.settimeout(1.0)
        self.inverter = KeepAliveInverter(local_sock, None, keep_alive=0.01)
        self.sock = remote_sock

    def tearDown(self) -> None:
        """Closes the sockets to prevent warnings."""
        self.inverter.disconnect()
        self.sock.close()

    def test_keep_alive_sent(self):
        """Tests if a keep-alive message gets send periodically."""
        # Receive keep-alive message
        msg = self.sock.recv(4096)
        self.assertTrue(msg.startswith(b"\x55\xaa"))
        # Send some arbitrary response
        self.sock.send(bytes.fromhex("55 aa 01 02 02 00 00 01 04"))
        # Receive another keep-alive message
        msg = self.sock.recv(4096)
        self.assertTrue(msg.startswith(b"\x55\xaa"))
        # Send some arbitrary response
        self.sock.send(bytes.fromhex("55 aa 01 02 02 00 00 01 04"))

    def test_keep_alive_cancelled(self):
        """Tests if keep-alive messages are cancelled when other messages are sent."""
        sleep(0.008)  # Wait just before a keep-alive message will be sent
        self.inverter.send(b"\x01\x02\x03", b"")  # Send something arbitrary
        self.sock.recv(4096)  # Retrieve the sent message
        sleep(0.004)  # Wait until the keep-alive was supposed to happen
        # Check that no message was sent
        self.sock.setblocking(False)
        with self.assertRaises(BlockingIOError):
            self.sock.recv(4096)

    def test_disconnect(self):
        """Tests if the keep-alive messages will stop cleanly."""
        self.inverter.disconnect()
        sleep(0.02)
