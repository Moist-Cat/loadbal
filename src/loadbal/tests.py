import unittest
import unittest.mock
from loadbal import client


class TestClient(unittest.TestCase):
    def setUp(self):
        # we will usually mock the message received to change the behaviour
        client.requests.Session.post = unittest.mock.Mock()
        self.posted = client.requests.Session.post
        client.socket.socket.recv = unittest.mock.Mock()
        client.socket.socket.connect = unittest.mock.Mock()
        self.connection = client.socket.socket.connect

        self.consumers = ("consumer1", "consumer2", "consumer3")
        self.sentinel = ("sentinel", "port")
        self.server = ("server", "port")
        self.test_args = (self.server, self.sentinel, self.consumers) 

        self.mock_client = client.Client(*self.test_args)

    def _res(self, res):
       """Client.execute_cmd returns an iterator. Here we return errors if any"""
       return next(res) if any(res) else ""

    def test_send_msg(self):
        cli = client.Client
        data = ("mock", "data", "msg")
        # mock
        cli.receive_message = unittest.mock.Mock(return_value=data)

        mock_client = cli(*self.test_args)
        res = mock_client.send_message()

        for consumer in reversed(self.consumers):
            for msg in data: 
                self.posted.assert_any_call(consumer, json=msg)

    def test_manage_consumer(self):
        res = self.mock_client.execute_cmd("C", ["drop", "consumer1"])

        self.assertNotIn("consumer1", self.mock_client.consumers, self._res(res))

        res = self.mock_client.execute_cmd("C", ["add", "consumer1"])
        self.assertIn("consumer1", self.mock_client.consumers, self._res(res))

    def test_switch_server(self):
        replacement = ["new_server", "port"]
        res = self.mock_client.execute_cmd("S", replacement)

        print(self._res(res))
        self.connection.assert_any_call(replacement)
