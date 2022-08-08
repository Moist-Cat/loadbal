import asyncio
from collections import deque
from http import HTTPStatus
from typing import Tuple, List
import os
import json
import urllib.parse

import socket

from __init__ import __version__ as version

PART_SIZE = 18 # in bytes
PATH = "/"

class HTTPClient:
    """
    Asynchronous HTTP client.
    """

    queue = asyncio.Queue()
    # put; get
    
    def __init__(self, host, port, consumers: List[Tuple[str, int]]):
        self.server_url = urllib.parse.urlsplit(f"http://{host}:{port}/")

        # [(host, port), ]
        self.consumers = deque(consumers) # it's a rotating list, so it better be double-ended

    def _next_consumer(self):
        # algo for determining which consumer is feeded next (round robin, etc) goes here
        # NOTE Current algo is round robin
        last = self.consumers[0]
        self.consumers.rotate(1)
        return last

    async def _receive_msg(self):
        """Receive message via TCP protocol"""
        reader, writer = await asyncio.open_connection(self._socket_host, self._socket_port)
        data = await reader.read(PART_SIZE)

        return data.decode("latin1")

    async def send_message(self):
        """Send messages from queue"""
        msg = await self._receive_msg()
        host, port = self._next_consumer()
        ssl = port in (443, 8443)

        reader, writer = await asyncio.open_connection(
            url, port, ssl=ssl)

        data = json.dumps(msg)
        query = (
            f"POST {PATH} HTTP/1.0\r\n"
            f"Host: {host}\r\n"
            f"User-Agent: python/filebal-{version}\r\n"
            f"Content-Length: {len(data)}\r\n"
            f"\r\n{data}\r\n"
        )

        writer.write(query.encode('latin1'))
        line = await reader.readline()
        line = line.decode('latin1').rstrip()

        # Ignore the body, close the socket
        writer.close()

        return HTTPStatus(int(line.split(" ")[1]))
