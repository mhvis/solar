"""Test cases for inverter.py."""
from io import BytesIO
from queue import Queue
from socket import socketpair, create_connection
from threading import Thread
from time import sleep
from unittest import TestCase

from samil.inverter import calculate_checksum, construct_message, Inverter, InverterEOFError, InverterFinder, \
    InverterNotFoundError, read_message, KeepAliveInverter


class MessageTestCase(TestCase):
    """Test message construction/destruction functions."""

    def test_checksum(self):
        """Tests checksum calculation."""
        message = bytes.fromhex("55 aa 01 89 00 00 04 55 0c 00 00")
        checksum = bytes.fromhex("01 ee")
        self.assertEqual(checksum, calculate_checksum(message))

    def test_construct(self):
        """Tests message construction."""
        identifier = b'\x06\x01\x02'
        payload = b'\x10\x10'
        expect = bytes.fromhex("55 aa 06 01 02 00 02 10 10 01 2a")
        self.assertEqual(expect, construct_message(identifier, payload))

    def test_read(self):
        """Tests read_message function."""
        f = BytesIO(bytes.fromhex("55 aa 06 01 02 00 02 10 10 01 2a"))
        ident, payload = read_message(f)
        self.assertEqual(b"\x06\x01\x02", ident)
        self.assertEqual(b"\x10\x10", payload)


message = b"\x55\xaa\x00\x01\x02\x00\x00\x01\x02"  # Sample inverter message


class InverterConnectionTestCase(TestCase):
    """Test low-level send/receive inverter messages over a socket connection.

    These test cases exist mainly because the sockets might behave differently
    in Windows.
    """

    def setUp(self) -> None:
        """Creates socket pair for local (app) and remote (fake inverter) side."""
        local_sock, remote_sock = socketpair()  # We apparently can't use family=AF_INET on Linux
        local_sock.settimeout(1.0)
        remote_sock.settimeout(1.0)
        self.inverter = Inverter(local_sock, None)
        # This sock mimics the actual inverter, i.e. the remote side of the
        #  connection. Send messages on it to mimic the actual inverter sending
        #  messages to the Inverter class.
        self.sock = remote_sock

    def tearDown(self) -> None:
        """Closes the sockets to prevent warnings."""
        self.inverter.sock.close()
        self.sock.close()

    def test_eof_on_send(self):
        """Tests if exception is raised on sending when connection is closed."""
        self.sock.close()  # Mimic inverter closed connection
        with self.assertRaises((BrokenPipeError, ConnectionAbortedError)):
            self.inverter.send(b"\x00\x01\x02", b"")
            # For Windows it only raises an error on the second try and it
            # raises ConnectionAbortedError instead of BrokenPipeError
            self.inverter.send(b"\x00\x01\x02", b"")

    def test_eof_on_recv(self):
        """Tests if exception is raised for closed connection when receiving."""
        self.sock.close()  # Mimic inverter closed connection
        with self.assertRaises(InverterEOFError):
            self.inverter.receive()

    def test_multiple_messages_received_at_once(self):
        """Multiple messages might arrive at once for TCP sockets."""
        # Send 2 messages
        self.sock.send(message + message)
        # Receive them back
        ident, payload = self.inverter.receive()
        self.assertEqual(b"\x00\x01\x02", ident)
        self.assertEqual(b"", payload)
        ident, payload = self.inverter.receive()
        self.assertEqual(b"\x00\x01\x02", ident)
        self.assertEqual(b"", payload)

    def test_chopped_message(self):
        """Messages might arrive chopped for TCP sockets."""
        queue = Queue()
        # Receive the message in a separate thread, because it blocks
        thread = Thread(target=lambda q: q.put(self.inverter.receive()), args=(queue,))
        thread.start()
        self.sock.send(message[0:1])  # Send some message parts
        sleep(0.01)
        self.sock.send(message[1:3])
        sleep(0.01)
        self.sock.send(message[3:7])
        sleep(0.01)
        self.sock.send(message[7:])
        thread.join()
        # Check result
        ident, payload = queue.get(timeout=1.0)
        self.assertEqual(b"\x00\x01\x02", ident)
        self.assertEqual(b"", payload)

    def test_send(self):
        """Tests whether a message from the app will arrive at the receiver."""
        self.inverter.send(b"\x00\x01\x02", b"")
        received_message = self.sock.recv(4096)
        self.assertEqual(message, received_message)

    def test_disconnect_multiple(self):
        """Tests if disconnect can be called multiple times."""
        self.inverter.disconnect()
        self.inverter.disconnect()  # Should not raise exception

    def test_disconnect_closed(self):
        """Tests if disconnect can be called on a closed socket."""
        self.sock.close()
        self.inverter.sock.close()
        self.inverter.sock_file.close()
        self.inverter.disconnect()  # Should not raise exception


class InverterFinderTestCase(TestCase):
    def test_inverter_not_found(self):
        """Tests if InverterNotFoundError is raised."""
        with InverterFinder() as finder:
            with self.assertRaises(InverterNotFoundError):
                finder.find_inverter(advertisements=2, interval=0.01)

    def test_new_connection(self):
        """Tests if a new connection is returned."""
        with InverterFinder() as finder:
            sock1 = create_connection(('127.0.0.1', 1200))
            sock2, addr = finder.find_inverter()
        # Test if the 2 sockets are paired
        sock2.send(b"\x12")
        self.assertEqual(b"\x12", sock1.recv(1))
        sock1.close()
        sock2.close()

    def test_open_with_retries_exception(self):
        """Tests if OSError is thrown after all retries have failed."""
        port_blocker = InverterFinder()
        port_blocker.open()
        with self.assertRaises(OSError):
            finder = InverterFinder()
            finder.open_with_retries(retries=2, period=0.01)
        port_blocker.close()

    def test_open_with_retries(self):
        """Tests if a retry happens when port is bound."""
        # Bind port
        port_blocker = InverterFinder()
        port_blocker.open()

        # Try binding port using retry function in separate thread
        def try_bind(q: Queue):
            finder = InverterFinder()
            finder.open_with_retries(retries=10, period=0.01)
            finder.close()
            # If bind failed, an exception should've been thrown by now
            # I assume the bind has succeeded here
            q.put(True)

        queue = Queue()
        thread = Thread(target=try_bind, args=(queue,))
        thread.start()

        # Unbind port
        sleep(0.01)
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
        sleep(0.005)  # Wait before a keep-alive message will be sent
        self.inverter.send(b"\x01\x02\x03", b"")  # Send something arbitrary
        self.sock.recv(4096)  # Retrieve the sent message
        sleep(0.008)  # Wait until just before the next keep-alive is supposed to happen
        # Check that no message was sent
        self.sock.setblocking(False)
        with self.assertRaises(BlockingIOError):
            self.sock.recv(4096)

    def test_disconnect(self):
        """Tests if the keep-alive messages will stop cleanly."""
        self.inverter.disconnect()
        sleep(0.02)
