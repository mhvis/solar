from unittest import TestCase

from samil.inverter import calculate_checksum, construct_message, deconstruct_message


class MessageTestCase(TestCase):
    def test_checksum(self):
        message = bytes.fromhex("55 aa 01 89 00 00 04 55 0c 00 00")
        checksum = bytes.fromhex("01 ee")
        self.assertEqual(checksum, calculate_checksum(message))

    def test_construct(self):
        identifier = b'\x06\x01\x02'
        payload = b'\x10\x10'
        expect = bytes.fromhex("55 aa 06 01 02 00 02 10 10 01 2a")
        self.assertEqual(expect, construct_message(identifier, payload))

    def test_deconstruct(self):
        message = bytes.fromhex("55 aa 01 89 00 00 04 55 0c 00 00 01 ee")
        identifier, payload = deconstruct_message(message)
        self.assertEqual(b'\x01\x89\x00', identifier)
        self.assertEqual(b'\x55\x0c\x00\x00', payload)
