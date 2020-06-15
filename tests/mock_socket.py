
# Todo: use actual socket for testing! (So that Windows socket issues can also be detected)

# class MockSocket:
#     def __init__(self):
#         self.output = []
#         self.data = bytearray()
#
#     def queue_recv(self, data: bytes):
#         self.data += data
#
#     def recv(self, bufsize, flags=None) -> bytes:
#         bufsize = min(bufsize, len(self.data))
#         d = self.data[0:bufsize]
#         self.data = self.data[bufsize:len(self.data)]
#         return d
#
#     def makefile(self, mode='r', bufsize=-1):
#         handle = MockFile(self.lines)
#         return handle
#
#     def sendall(self, data, flags=None):
#         self.last = data
#         self.output.append(data)
#         return len(data)
#
#     def send(self, data, flags=None):
#         self.last = data
#         self.output.append(data)
#         return len(data)
#
#     def close(self):
#         pass
