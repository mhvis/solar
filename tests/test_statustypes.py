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
from decimal import Decimal
from unittest import TestCase

from samil.inverter import decode_string
from samil.statustypes import DecimalStatusType, \
    OperationModeStatusType, OneOfStatusType, BytesStatusType, IfPresentStatusType


class BytesStatusTypeTestCase(TestCase):
    status_format = bytes.fromhex("00 01 02 04 05 09 0a 0c 11 17 18 1b 1c 1d 1e 1f 20 21 22 27 28 31 32 33 34 35 36")
    status_message = bytes.fromhex("01 77 0b ac 0b e1 00 15 00 14 00 00 28 40 00 01 01 da 00 00 00 00 00 00 00 " +
                                   "00 00 00 00 00 00 00 00 00 00 00 00 00 02 8c 02 76 00 38 09 1b 13 86 04 fb " +
                                   "00 01 b1 cc")

    def test_none(self):
        t = BytesStatusType(0x03, 0x04)
        self.assertIsNone(t.get_value(self.status_format, self.status_message))

    def test_one(self):
        t = BytesStatusType(0x01)
        self.assertEqual(b'\x0b\xac', t.get_value(self.status_format, self.status_message))

    def test_two_reverse(self):
        t = BytesStatusType(0x02, 0x01)
        self.assertEqual(b'\x0b\xe1\x0b\xac', t.get_value(self.status_format, self.status_message))


class DecimalStatusTypeTestCase(TestCase):
    status_format = bytes.fromhex("00 01 02 04 05 09 0a 0c 11 17 18 1b 1c 1d 1e 1f 20 21 22 27 28 31 32 33 34 35 36")
    status_message = bytes.fromhex("01 77 0b ac 0b e1 00 15 00 14 00 00 28 40 00 01 01 da 00 00 00 00 00 00 00 " +
                                   "00 00 00 00 00 00 00 00 00 00 00 00 00 02 8c 02 76 00 38 09 1b 13 86 04 fb " +
                                   "00 01 b1 cc")

    def test_get_value(self):
        status_type = DecimalStatusType(0x35, 0x36, scale=-1)
        self.assertEqual(Decimal('11105.2'), status_type.get_value(self.status_format, self.status_message))

    def test_get_value_none(self):
        status_type = DecimalStatusType(0x37)
        self.assertIsNone(status_type.get_value(self.status_format, self.status_message))


class StringDecodeTestCase(TestCase):
    def test_samil_string(self):
        expect = "V1"
        actual = decode_string(b' V1 \x00 ')
        self.assertEqual(expect, actual)


class OperationModeStatusTypeTestCase(TestCase):
    def test_status_type(self):
        status_format = bytes.fromhex("00 01 02 04 05 09 0a 0c 11 17 18 1b 1c 1d 1e 1f 20 21 22 27 28 31 32 33 34")
        status_payload = bytes.fromhex("01 77 0b ac 0b e1 00 15 00 14 00 00 28 40 00 01 01 da 00 00 00 00 00 00 00 " +
                                       "00 00 00 00 00 00 00 00 00 00 00 00 00 02 8c 02 76 00 38 09 1b 13 86 04 fb")
        om = OperationModeStatusType()
        self.assertEqual('Normal', om.get_value(status_format, status_payload))


class OneOfStatusTypeTestCase(TestCase):
    status_format = bytes.fromhex("00 01 02 04 05 09 0a 0c 11 17 18 1b 1c 1d 1e 1f 20 21 22 27 28 31 32 33 34")
    status_payload = bytes.fromhex("01 77 0b ac 0b e1 00 15 00 14 00 00 28 40 00 01 01 da 00 00 00 00 00 00 00 " +
                                   "00 00 00 00 00 00 00 00 00 00 00 00 00 02 8c 02 76 00 38 09 1b 13 86 04 fb")

    def test_none(self):
        status_type = OneOfStatusType(DecimalStatusType(0x03), DecimalStatusType(0x06))
        self.assertIsNone(status_type.get_value(self.status_format, self.status_payload))

    def test_one(self):
        status_type = OneOfStatusType(DecimalStatusType(0x03), DecimalStatusType(0x04))
        self.assertEqual(Decimal(21), status_type.get_value(self.status_format, self.status_payload))

    def test_two(self):
        status_type = OneOfStatusType(DecimalStatusType(0x04), DecimalStatusType(0x00))
        self.assertEqual(Decimal(21), status_type.get_value(self.status_format, self.status_payload))


class IfPresentStatusTypeTestCase(TestCase):
    def test_all(self):
        status_format = bytes.fromhex("00")
        status_payload = bytes.fromhex("12 34")
        status_type = BytesStatusType(0x00)

        # If present and actually present
        t = IfPresentStatusType(0x00, True, status_type)
        self.assertEqual(b'\x12\x34', t.get_value(status_format, status_payload))

        # If present while not actually present
        t = IfPresentStatusType(0x01, True, status_type)
        self.assertIsNone(t.get_value(status_format, status_payload))

        # If not present while actually present
        t = IfPresentStatusType(0x00, False, status_type)
        self.assertIsNone(t.get_value(status_format, status_payload))

        # If not present and actually not present
        t = IfPresentStatusType(0x01, False, status_type)
        self.assertEqual(b'\x12\x34', t.get_value(status_format, status_payload))
