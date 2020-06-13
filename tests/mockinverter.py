import socket
from threading import Thread


class MockInverter(Thread):
    default_model = b'2 170002.11\x00SolarLake17K    SamilPower      T1712CC008\x00\x00\x00\x00\x00\x002.11\x002.11\x001'
    default_status_format = b'\x00\x01\x02\x04\x05\x07\x08\x09\x0a\x0b\x0c\x11\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x21\x22\x27\x28\x2f\x31\x32\x33\x51\x52\x53\x71\x72\x73'
    default_status = bytes(
        [1, 94, 22, 233, 0, 67, 0, 48, 0, 1, 0, 0, 3, 2, 0, 0, 0, 45, 10, 29, 0, 1, 8, 72, 0, 0, 0, 0, 0, 0, 0, 0,
         0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 11, 6, 0, 0, 2, 18, 0, 36, 9, 122, 19, 137, 0, 37, 9, 141, 19, 137,
         0, 36, 9, 121, 19, 137])

    def __init__(self, model=default_model, status_format=default_status_format, status=default_status):
        super().__init__(args=(model, status_format, status))
        self.model = model
        self.status_format = status_format
        self.status = status

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def run(self, model, status_format, status):
        with socket.create_connection(('127.0.0.1', 1200), 5.0) as s:
            while True:
                message = s.recv(4096)
                print()
                print('received', message)
                print('in hex', ' '.join(['{:x}'.format(ch) for ch in message]))
                identifier = message[2:5]
                if identifier == b'\x01\x03\x02':
                    _send(s, _construct(b'\x01\x83\x00', inverter['model']))
                elif identifier == b'\x01\x00\x02':
                    _send(s, _construct(b'\x01\x80\x00', inverter['unkn1']))
                # elif identifier == b'\x01\x09\x02':
                #     pass
                elif identifier == b'\x01\x02\x02':
                    _send(s, _construct(b'\x01\x82\x00', inverter['state']))
                elif identifier == b'\x04\x00\x02':
                    _send(s, _construct(b'\x04\x80\x00', inverter['unkn3']))
                else:
                    print('unknown identifier')


def _construct(identifier, payload):
    start = b'\x55\xaa'
    payload_size = len(payload).to_bytes(2, byteorder='big')
    message = start + identifier + payload_size + payload
    checksum = sum(message).to_bytes(2, byteorder='big')
    return message + checksum


def _send(socket, message):
    print()
    print('sending', message)
    print('in hex', ' '.join(['{:x}'.format(ch) for ch in message]))
    socket.sendall(message)
