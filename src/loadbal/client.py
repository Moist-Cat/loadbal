"""
Clients who interact and handle data from both TCP and HTTP servers


1. The client listens to the sentinel for a message
2. When the client reads the message it decides what to do depending on the command (first argument of the message)
3. It either yields an error, a chunk of data, or None if the command was merely administrative (adding/removing consumers or switching the server after it failed)

"""
from collections import deque
from functools import wraps
from io import BytesIO
import socket
import time
from threading import Thread
from typing import Tuple, List

import requests

from loadbal.__init__ import __version__ as version
from loadbal.log import logged
from loadbal import settings

PART_SIZE = 18  # in bytes
ENC = "latin1"


def check_errors(request):
    """
    VERSION: 1.0.1
    Properly handles HTTP and other comms related errors.
    """

    @wraps(request)
    def inner_func(cls, method, url, **kwargs):
        request_success = False
        retries = 0
        while not request_success:
            try:
                response = request(cls, method, url, **kwargs)
                response.raise_for_status()
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.SSLError,
            ) as exc:
                cls.logger_error.exception(exc)

                cls.logger.info("Network unstable. Retrying...")
                cls.logger_error.error(
                    "Server URL: %s, failed while trying to connect.", url
                )
                if retries > settings.RETRIES:
                    raise exc

            except requests.exceptions.HTTPError as exc:
                try:
                    payload = kwargs["data"]
                except KeyError:
                    payload = "none"
                error_message = f"""
                    Server URL: {response.url},
                    failed with status code ({response.status_code}).
                    Raw response: {response.content[:50]}
                    Request payload: {payload}
                """
                cls.logger.error(error_message)
                with open(settings.BASE_DIR / "logs/debug.html", "w+b") as file:
                    file.write(response.content)
                raise exc
            else:
                request_success = True
            time.sleep(1)
            retries += 1
        return response

    return inner_func


@logged
class Client(requests.Session):
    """
    HTTP/TCP client.
    """

    @check_errors
    def request(self, *args, **kwargs):
        return super().request(*args, **kwargs)

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
        """A consumer is down, remove it"""
        self.consumers.remove(consumer)

    def _add_consumer(self, consumer: str):
        self.consumers.append(consumer)

    def _switch_server(self, replacement: tuple):
        """Close the old connection to the server and listen to another one"""
        self.sock.close()
        self.sock.connect(replacement)

    def receive_message(self):
        """
        Waits for the signal from the sentinel and reads a message, forwarding it to the execute_command method
        """
        raw_msg = BytesIO()
        while True:
            chunk = self.sentinel.recv(1)
            if chunk == b"\n":
                break
            raw_msg.write(chunk)

        raw_msg.seek(0)
        msg = raw_msg.read().decode(ENC)
        fields = msg.split(",")
        command = fields.pop(0)

        assert command, "No command"

        return self.execute_cmd(command, fields)

    def execute_cmd(self, command: str, fields: list):
        """Parse arguments and execute actions"""
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
            yield  {"errors": f"Bad command {command}"}


    def _send_message(self, msg):
        bad_consumers = [] 
        for consumer in self.consumers:
            try:
                res = self.post(consumer, json=msg)
            except (
                requests.exceptions.HTTPError,
                requests.exceptions.ConnectionError,
                requests.exceptions.SSLError,
            ) as exc:
                if len(bad_consumers) == len(self.consumers) - 1:
                    self.logger.critical("!!! NO CONSUMERS AVAILABLE. !!!")
                    return False
                # bad consumer
                self.logger.warning(f"Removing bad consumer %s", consumer)
                bad_consumers.append(consumer)
                continue
            self.logger.info("%d %s %s", res.status_code, res.headers, msg)
        for consumer in bad_consumers:
            self.consumers.remove(consumer)
        return True


    def send_message(self):
        """Send data from the TCP server to an HTTP server via JSON"""
        for msg in self.receive_message():
            if "errors" not in msg:
                sent = False
                while not sent:
                    sent = self._send_message(msg)
            else:
                self.logger.error(msg["errors"])


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
