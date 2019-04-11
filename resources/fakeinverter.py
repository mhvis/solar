from socket import socket, AF_INET, SOCK_STREAM

# Possible message payloads to send
model1 = b'1  4500V1.30River 4500TL-D\x00 SamilPower\x00     DW413B8080\x00\x00\x00\x00\x00\x00V1.30V1.302'
model2 = b'1  4500V1.30River 4500TL-D\x00 SamilPower\x00     DW413B8080\x00\x00\x00\x00\x00\x00V1.30V1.302'

def _construct(identifier, payload):
    start = b'\x55\xaa'
    payload_size = len(payload).to_bytes(2, byteorder='big')
    message = start + identifier + payload_size + payload
    checksum = sum(message).to_bytes(2, byteorder='big')
    return message + checksum



with socket(AF_INET, SOCK_STREAM) as s:
    s.connect(('127.0.0.1', 1200))

    while True:
        # Receive message
        message = s.recv(4096)
        identifier = message[2:4]
        # if identifier ==
    s.sendall()
