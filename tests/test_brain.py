import unittest
from cmdbot_evented.core import Bot


class BrainTestCase(unittest.TestCase):

    def test_knows(self):
        b = Bot.brain()
        self.assertFalse(b.knows('stuff'))
        b.stuff = 'stuff'
        self.assertTrue(b.knows('stuff'))

    def test_knows_false(self):
        b = Bot.brain()
        b.stuff = ''
        self.assertFalse(b.knows('stuff'))
        self.assertTrue(b.knows('stuff', include_falses=True))
