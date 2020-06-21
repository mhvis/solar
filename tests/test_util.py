from queue import Queue
from threading import Thread
from time import sleep
from unittest import TestCase

from samil.inverter import InverterListener
from samil.util import create_inverter_listener


class CreateInverterListenerTestCase(TestCase):
    def test_exception(self):
        """Tests if OSError is thrown after all retries have failed."""
        port_blocker = InverterListener()
        with self.assertRaises(OSError):
            create_inverter_listener(retries=2, period=0.01)
        port_blocker.close()

    def test_retry(self):
        """Tests if a retry happens when port is bound."""
        # return
        # Bind port
        port_blocker = InverterListener()

        # Try binding port using retry function in separate thread
        def try_bind(q: Queue):
            listener = create_inverter_listener(retries=10, period=0.01)
            # If bind failed, an exception should've been thrown by now
            # I assume the bind has succeeded here
            q.put(True)
            listener.close()
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



