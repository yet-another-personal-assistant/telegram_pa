import unittest

from unittest.mock import Mock

from assistant.backend import BackendConnection


class BackendConnectionTest(unittest.TestCase):

    def test_create(self):
        reader = Mock()
        writer = Mock()
        session = Mock()
        
        backend = BackendConnection(reader, writer, session)
