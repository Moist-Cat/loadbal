"""Clients who insteract and handle data from both TCP and HTTP servers"""
from collections import deque
from typing import Tuple, List
import socket

import requests

from loadbal.__init__ import __version__ as version

PART_SIZE = 18  # in bytes
PATH = "/"
ENC = "latin1"


class Client(requests.Session):
    """
    HTTP/TCP client.
    """

    def __init__(
        self,
        socket_server: Tuple[str],
        sentinel_server: Tuple[str],
        consumers: List[Tuple[str, int]],
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sentinel =  socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.sock.connect(socket_server)
        self.sentinel.connect(sentinel_server)

        # [(host, port), ]
        self.consumers = deque(
            consumers
        )  # it's a rotating list, so it better be double-ended

    def close(self):
        self.sock.close()
        self.sentinel.close()

    def _next_consumer(self):
        # algo for determining which consumer is feeded next (round robin, etc) goes here
        # NOTE Current algo is round robin
        last = self.consumers[0]
        self.consumers.rotate(1)
        return last

    def _receive_msg(self):
        """Receive message via TCP protocol"""
        raw_data = None
        while not raw_data:
            raw_data = self.sock.recv(PART_SIZE)

        data = raw_data.decode(ENC)
        return data

    def receive_msg(self):
        """Waits for the signal from the sentinel and reads a message"""
        raw_msg = None
        while not raw_msg:
            raw_msg = self.sentinel.recv(1024 * 1024)

        msgs = raw_msg.decode(ENC)
        for msg in msgs.split("\n"):
            _type, uid, size = msg.split(",")
            size = int(size)
            # this is just:
            # 1. divide in equal parts
            # 2. see if there is a remainder
            # 3. we do substract 1 if there is a remainder since the end is not included
            for partition in range(size // PART_SIZE + bool(size % PART_SIZE)):
                data = self._receive_msg()
                yield {"uid": uid, "data": data, "type": _type, "chunkid": partition}

    def send_message(self):
        """Send messages from queue"""
        for msg in self.receive_msg():
            cons_url = self._next_consumer()
            res = self.post(cons_url, json=msg)
            print(res.status_code, res.headers, msg)


if __name__ == "__main__":
    cli = Client(
        ("localhost", 8000),
        ("localhost", 5050),
        [
            ("http://localhost:8080"),
            ("http://localhost:8081"),
            ("http://localhost:8082"),
        ],
    )
    while True:
        try:
            cli.send_message()
        except KeyboardInterrupt:
            cli.close()
            break
