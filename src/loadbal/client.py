"""Clients who insteract and handle data from both TCP and HTTP servers"""
from collections import deque
from typing import Tuple, List
import socket

import requests

from loadbal.__init__ import __version__ as version

PART_SIZE = 18  # in bytes
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
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sentinel = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.sock.connect(socket_server)
        self.sentinel.connect(sentinel_server)

        # [(host, port), ]
        self.consumers = deque(
            consumers
        )  # it's a rotating list, so it better be double-ended

    def close(self):
        self.sock.close()
        self.sentinel.close()

    def _receive_msg(self):
        """Receive message via TCP protocol"""
        raw_data = None
        while not raw_data:
            raw_data = self.sock.recv(PART_SIZE)

        data = raw_data.decode(ENC)
        return data

    def _drop_consumer(self, consumer: str):
        """A consumer is down"""
        self.consumers.remove(consumer)

    def _add_consumer(self, consumer: str):
        self.consumers.append(consumer)

    def _switch_server(self, replacement: tuple):
        self.sock.close()
        self.sock.connect(replacement)

    def receive_message(self):
        """Waits for the signal from the sentinel and reads a message"""
        raw_msg = ""
        while not raw_msg:
            chunk = self.sentinel.recv(1)
            if chunk == b"\n":
                break

        msg = raw_msg.decode(ENC)
        fields = msg.split(",")
        command = fields.pop(0)

        return self.execute_cmd(command, fields)

    def execute_cmd(self, command: str, fields: list):
        if command == "F":
            size = fields.pop()
            uid = fields.pop()

            size = int(size)

            # this is just:
            # 1. divide in equal parts
            # 2. see if there is a remainder
            # 3. we do substract 1 if there is a remainder since the end is not included
            for partition in range(size // PART_SIZE + bool(size % PART_SIZE)):
                data = self._receive_msg()
                yield {"uid": uid, "data": data, "chunkid": partition}
        elif command == "C":
            url = fields.pop()
            action = fields.pop()
            if action == "drop":
                self._drop_consumer(url)
            elif action == "add":
                self._add_consumer(url)
            else:
                yield {"errors": f"Bad action for command consumer (C) {action}"}
        elif command == "S":
            self._switch_server(fields)
        else:
            yield  {"errors": "Bad command {command}"}

    def send_message(self):
        """Send messages from queue"""
        for msg in self.receive_message():
            if "errors" not in msg:
                for consumer in self.consumers:
                    res = self.post(consumer, json=msg)
                    print(res.status_code, res.headers, msg)
            else:
                print(msg["erorrs"])


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
