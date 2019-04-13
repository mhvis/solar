from socket import socket, AF_INET, SOCK_STREAM

# Fake inverter message payloads

# SolarRiver 4500 TL-D
river = {
    'model': b'1  4500V1.30River 4500TL-D\x00 SamilPower\x00     DW413B8080\x00\x00\x00\x00\x00\x00V1.30V1.302',
    'unkn1': b'\x00\x01\x02\x04\x05\x09\x0a\x0c\x11\x17\x18\x1b\x1c\x1d\x1e\x1f\x20\x21\x22\x27\x28\x31\x32\x33\x34\x35\x36',
    'state': bytes(
        [1, 119, 11, 159, 11, 246, 0, 21, 0, 20, 0, 0, 40, 64, 0, 1, 1, 218, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
         0, 0, 0, 0, 0, 0, 0, 0, 2, 136, 2, 111, 0, 55, 9, 20, 19, 134, 4, 238, 0, 1, 177, 204]),
    'unkn3': b'\x02' + 160 * b'\x00',
}

# SolarLake17K
lake = {
    'model': b'2 170002.11\x00SolarLake17K    SamilPower      T1712CC008\x00\x00\x00\x00\x00\x002.11\x002.11\x001',
    'unkn1': b'\x00\x01\x02\x04\x05\x07\x08\x09\x0a\x0b\x0c\x11\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x21\x22\x27\x28\x2f\x31\x32\x33\x51\x52\x53\x71\x72\x73',
    'state': bytes(
        [1, 94, 22, 233, 0, 67, 0, 48, 0, 1, 0, 0, 3, 2, 0, 0, 0, 45, 10, 29, 0, 1, 8, 72, 0, 0, 0, 0, 0, 0, 0, 0,
         0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 11, 6, 0, 0, 2, 18, 0, 36, 9, 122, 19, 137, 0, 37, 9, 141, 19, 137,
         0, 36, 9, 121, 19, 137]),
    'unkn3': b'\x02' + 160 * b'\x00',
}

# Which inverter to fake
inverter = lake


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


with socket(AF_INET, SOCK_STREAM) as s:
    s.connect(('127.0.0.1', 1200))

    while True:
        # Receive message
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
