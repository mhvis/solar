from decimal import Decimal
from unittest import TestCase

from solar.samil import _checksum, _samil_request, _samil_response, _value_of, DecimalStatusType, _samil_string, \
    OperatingModeStatusType, OneOfStatusType


class MessageTestCase(TestCase):
    def test_checksum(self):
        message = bytes.fromhex("55 aa 01 89 00 00 04 55 0c 00 00")
        checksum = bytes.fromhex("01 ee")
        self.assertEqual(checksum, _checksum(message))

    def test_samil_request(self):
        identifier = b'\x06\x01\x02'
        payload = b'\x10\x10'
        expect = bytes.fromhex("55 aa 06 01 02 00 02 10 10 01 2a")
        self.assertEqual(expect, _samil_request(identifier, payload))

    def test_samil_response(self):
        message = bytes.fromhex("55 aa 01 89 00 00 04 55 0c 00 00 01 ee")
        identifier, payload = _samil_response(message)
        self.assertEqual(b'\x01\x89\x00', identifier)
        self.assertEqual(b'\x55\x0c\x00\x00', payload)


class DecimalStatusTypeTestCase(TestCase):
    status_format = bytes.fromhex("00 01 02 04 05 09 0a 0c 11 17 18 1b 1c 1d 1e 1f 20 21 22 27 28 31 32 33 34 35 36")
    status_message = bytes.fromhex("01 77 0b ac 0b e1 00 15 00 14 00 00 28 40 00 01 01 da 00 00 00 00 00 00 00 " +
                                   "00 00 00 00 00 00 00 00 00 00 00 00 00 02 8c 02 76 00 38 09 1b 13 86 04 fb " +
                                   "00 01 b1 cc")

    def test_value_of(self):
        self.assertEqual(b'\x28\x40', _value_of(0x0a, self.status_format, self.status_message))

    def test_get_value(self):
        status_type = DecimalStatusType(0x35, 0x36, scale=-1)
        self.assertEqual(Decimal('11105.2'), status_type.get_value(self.status_format, self.status_message))

    def test_get_value_none(self):
        status_type = DecimalStatusType(0x37)
        self.assertIsNone(status_type.get_value(self.status_format, self.status_message))


class StringDecodeTestCase(TestCase):
    def test_samil_string(self):
        expect = "V1"
        actual = _samil_string(b' V1 \x00 ')
        self.assertEqual(expect, actual)


class OperatingModeStatusTypeTestCase(TestCase):
    def test_status_type(self):
        status_format = bytes.fromhex("00 01 02 04 05 09 0a 0c 11 17 18 1b 1c 1d 1e 1f 20 21 22 27 28 31 32 33 34")
        status_payload = bytes.fromhex("01 77 0b ac 0b e1 00 15 00 14 00 00 28 40 00 01 01 da 00 00 00 00 00 00 00 " +
                                       "00 00 00 00 00 00 00 00 00 00 00 00 00 02 8c 02 76 00 38 09 1b 13 86 04 fb")
        om = OperatingModeStatusType()
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
