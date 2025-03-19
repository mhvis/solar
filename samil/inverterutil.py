#
# MIT License
#
# Copyright (c) 2016 Maarten Visscher
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
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
