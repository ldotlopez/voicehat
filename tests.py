#!/usr/bin/env python3
# -*- encoding: utf-8 -*-


import unittest
import suzie


class SimplePlugin(suzie.Plugin):
    NAME = 'simple'
    TRIGGERS = [
        r'^x$'
    ]


class EchoPlugin(suzie.Plugin):
    NAME = 'echo'
    TRIGGERS = [
        r'^echo (.+)$'
    ]

    def reply(self, conv, text):
        conv.reply_and_close(text)


class EchoKeywordPlugin(suzie.Plugin):
    NAME = 'echo-keyword'
    TRIGGERS = [
        r'^echo (?P<t>.+)$'
    ]

    def reply(self, conv, t=''):
        conv.reply_and_close(t)


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

    def test_keyword_plugin_response(self):
        self.r.register(EchoKeywordPlugin())
        self.assertEqual(
            self.r.handle('echo bar'),
            'bar')


if __name__ == '__main__':
    unittest.main()
