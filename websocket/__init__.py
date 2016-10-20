from zashel.utils import search_win_drive, daemonize
from zashel.basehandler import BaseHandler
import base64
import http.client
import hashlib
import io
import re
import socket
import struct

DEFAULT_BUFFER = 4096
DEFAULT_LISTENING = 10

BUFFER = DEFAULT_BUFFER
LISTENING = DEFAULT_LISTENING

class WebSocket(object):
    def __init__(self, port, handler=BaseHandler()):
        self._socket = socket.socket()
        self.socket.bind(("",port))
        self.listen()
        self._connections = dict()
        #self.conn, self.addr = None, None
        self._port = port
        self._handler = handler

    @property
    def handler(self):
        return self._handler

    @property
    def socket(self):
        return self._socket

    @property
    def port(self):
        return self._port

    @daemonize
    def listen(self):
        self.socket.listen(LISTENING)
        while True:
            conn, addr = self.socket.accept()
            self._connections[addr] = conn
            response = conn.recv(1024)
            response = response.decode("utf-8").split("\r\n")
            self._send_accept(conn, response)
            self.get_answer(addr)
            
    @daemonize
    def get_answer(self, addr, buff=BUFFER):
        conn = self._connections[addr]
        while True:
            response = bytes()
            conn.settimeout(0.5)
            while True:
                try:
                    print(conn.recv(buff)) # Please, help, I always receive different information
                except socket.timeout:
                    break
            conn.settimeout(0.0)

    def _send_accept(self, conn, response):
        headers = dict()
        for line in response:
            data = re.findall("([\w\W]+): ([\w\W]+)", line)
            if data != list(): 
                headers[data[0][0]]=data[0][1]
        key = headers["Sec-WebSocket-Key"]
        key = "".join((key, "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"))
        key = hashlib.sha1(bytes(key, "utf-8"))
        key = base64.b64encode(key.digest()).decode("utf-8")
        accept = "HTTP/1.1 101 Switching Protocols\r\n"
        accept = "".join((accept, "Upgrade: websocket\r\n"))
        accept = "".join((accept, "Connection: Upgrade\r\n"))
        accept = "".join((accept, "Sec-WebSocket-Accept: {}\r\n\r\n".format(key)))
        self.send(accept, conn)
        print("Acepted")
        

    def send(self, data, conn, mask=False):
        try:
            print(data)
            output = io.BytesIO()
            # Prepare the header
            head1 = 0b10000000
            head1 |= 0x01
            head2 = 0b10000000 if mask else 0
            length = len(data)
            if length < 0x7e:
                output.write(struct.pack('!BB', head1, head2 | length))
            elif length < 0x10000:
                output.write(struct.pack('!BBH', head1, head2 | 126, length))
            else:
                output.write(struct.pack('!BBQ', head1, head2 | 127, length))
            if mask:
                mask_bits = struct.pack('!I', random.getrandbits(32))
                output.write(mask_bits)
            # Prepare the data
            if mask:
                data = bytes(b ^ mask_bits[i % 4] for i, b in enumerate(data))
            output.write(bytes(data, "utf-8"))
            conn.sendall(output.getvalue())
        except Exception:
            raise
