from uuid import uuid4
import socket
import socketserver
import json
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
import time

try:
    with open("data.txt", "r+b") as file:
        print("found data")
        data = file.read()
except FileNotFoundError:
    print("no data found")
    data = b"" 


class ReusableTCPServer(socketserver.TCPServer):
    """Extended TCP server made to avoid *ADDRESS IN USE* errors-"""

    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)


class TCPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        msg = data
        print(msg.decode("utf8"))
        return self.request.sendall(msg)


class SentinelHandler(socketserver.BaseRequestHandler):
    def handle(self):
        # !F, ID, size,
        # !C, url
        # !S, host, port
        self.request.sendall(b"F,uid,29000\n")


class HTTPHandler(BaseHTTPRequestHandler):
    """Fetch data from a file, put it on memory, and send
    one line every time on request"""

    data = data

    def read_data(self):
        """Read the data field from the client using the Content-Length header
        as a guide"""
        payload_len = int(self.headers.get("Content-Length"))
        return self.rfile.read(payload_len)

    def do_POST(self):
        """Put the buffer from the POST in a file"""
        buffer = self.read_data()

        with open("res/" + str(uuid4()) + ".json", "w+b") as file:
            file.write(buffer)
        self.send_response(HTTPStatus.CREATED)
        self.end_headers()


def _runserver(handler, host="localhost", port=9999):
    """
    :param handler: Handler object
    :param host: server ip-address/domain-name
    :param port: port

    :return: socket server object"""
    server = ReusableTCPServer((host, port), handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    return server


def runserver(handler, host, port):
    """Infinite looping for the server and secure closing. Mapping for handler classes."""
    handler_cls = {"TCP": TCPHandler, "HTTP": HTTPHandler, "SENTINEL": SentinelHandler}.get(handler)
    assert handler_cls

    server = _runserver(handler_cls, host, port)
    print(f"Running {handler} server on http://{host}:{port}")

    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("Shutdown")
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    import sys

    HOST, PORT = "localhost", sys.argv[1:][1]
    HANDLER = sys.argv[1:][0].upper()

    runserver(HANDLER, HOST, int(PORT))
