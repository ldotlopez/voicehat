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

    def test_single_match(self):
        sp = SimplePlugin()
        self.r.register(sp)

        handler = self.r.get_handler('x')
        self.assertEqual(handler.plugin, sp)

    def test_zero_matches(self):
        sp = SimplePlugin()
        self.r.register(sp)

        with self.assertRaises(suzie.TextNotMatched):
            self.r.get_handler('foo')

    def test_priority_match(self):
        sp1 = SimplePlugin()
        sp2 = SimplePlugin()
        sp2.WEIGHT = -1

        self.r.register(sp1)
        self.r.register(sp2)
        handlers = list(self.r.get_handlers('x'))

        self.assertEqual(len(handlers), 2)
        self.assertEqual(handlers[0].plugin, sp2)

    def test_no_plugins(self):
        with self.assertRaises(suzie.TextNotMatched):
            self.r.get_handler('x')

    def test_simple_response(self):
        self.r.register(EchoPlugin())
        self.assertEqual(
            self.r.handle('echo foo'),
            'foo')


if __name__ == '__main__':
    unittest.main()
