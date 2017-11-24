#!/usr/bin/env python3
# -*- encoding: utf-8 -*-


import unittest
import suzie


class SimplePlugin(suzie.Plugin):
    TRIGGERS = [
        r'^x$'
    ]


class EchoPlugin(suzie.Plugin):
    TRIGGERS = [
        r'^echo (.+)$'
    ]

    def handle(self, arg):
        return arg


class TestSuzie(unittest.TestCase):
    def setUp(self):
        self.r = suzie.Router()

    def test_simple_match(self):
        sp = SimplePlugin()
        self.r.register(sp)

        responders = list(self.r.get_handlers('x'))
        self.assertEqual(responders[0].plugin, sp)

    def test_zero_matches(self):
        sp = SimplePlugin()
        self.r.register(sp)

        responders = list(self.r.get_handlers('foo'))
        self.assertEqual(responders, [])

    def test_priority_match(self):
        sp1 = SimplePlugin()
        sp2 = SimplePlugin()
        sp2.WEIGHT = -1

        self.r.register(sp1)
        self.r.register(sp2)
        responders = list(self.r.get_handlers('x'))

        self.assertEqual(len(responders), 2)
        self.assertEqual(responders[0].plugin, sp2)

    def test_simple_response(self):
        self.r.register(EchoPlugin())
        self.assertEqual(
            self.r.handle('echo foo'),
            'foo')


if __name__ == '__main__':
    unittest.main()
