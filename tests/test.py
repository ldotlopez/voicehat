import unittest
import re

import suzie


class CommonAsserts:
    def assertConversation(self, conv_or_plugin, log, final=True):
        if isinstance(conv_or_plugin, suzie.Conversation):
            c = conv_or_plugin
        elif isinstance(conv_or_plugin, suzie.Plugin):
            c = suzie.Conversation(conv_or_plugin)
        else:
            raise TypeError(conv_or_plugin)

        is_multi_step = len(log) > 2 and final is True

        for idx in list(range(0, len(log), 2)):
            user = log[idx]
            agent = log[idx+1]

            reply = c.handle(user)
            if is_multi_step and idx < len(log) - 2:
                self.assertTrue(
                    isinstance(reply, suzie.InformationRequiredMessage))

            if agent:
                self.assertEqual(str(reply), agent)

        if final:
            self.assertTrue(
                isinstance(reply, suzie.ClosingMessage))
        else:
            self.assertTrue(
                isinstance(reply, suzie.InformationRequiredMessage))


class FooBarPlugin(suzie.Plugin):
    TRIGGERS = [r'.+']
    STATE_SLOTS = ['foo', 'bar']

    def extract(self, text):
        m = re.search(r'\bfoo as (.+?)\b', text)
        if m:
            yield 'foo', m.group(1)

        m = re.search(r'\bbar as (.+?)\b', text)
        if m:
            yield 'bar', m.group(1)

    def main(self, foo, bar):
        msg = "foo='{foo}', bar='{bar}'"
        msg = msg.format(foo=foo, bar=bar)
        return suzie.ClosingMessage(msg)


class TriggersAndKeywordsPlugin(suzie.Plugin):
    TRIGGERS = [
        r'^say$',
        r'^say (?P<what>.+)$',
    ]
    STATE_SLOTS = ['what']

    def extract(self, text):
        return {'what': text}

    def main(self, what):
        return suzie.ClosingMessage(''.join(reversed(what)))


class TestPlugin(unittest.TestCase):
    def test_full_predicate(self):
        plugin = FooBarPlugin()
        state = {}
        reply = plugin.handle('foo as 1 and bar as 2', state)

        self.assertTrue(isinstance(reply, suzie.ClosingMessage))

    def test_partial_predicate(self):
        plugin = FooBarPlugin()
        state = {}
        reply = plugin.handle('foo as 1', state)

        self.assertTrue(isinstance(reply, suzie.InformationRequiredMessage))
        self.assertEqual(reply.what, 'bar')
        self.assertEqual(state, {'foo': '1'})

    def test_multi_step_completion(self):
        plugin = FooBarPlugin()
        state = {}

        reply = plugin.handle('foo as 1', state)
        self.assertTrue(isinstance(reply, suzie.InformationRequiredMessage))

        reply = plugin.handle('bar as 2', state)
        self.assertTrue(isinstance(reply, suzie.ClosingMessage))


class TestConversation(unittest.TestCase, CommonAsserts):
    def test_quick_conv(self):
        self.assertConversation(
            FooBarPlugin(),
            ['set foo as 1 and bar as 2', None]
        )

    def test_multistep_conv(self):
        self.assertConversation(
            FooBarPlugin(),
            ['set foo as 1', None,
             'bar as 2', None]
        )

    def test_triggers_and_keywords_conv(self):
        msg = 'say abc'

        plugin = TriggersAndKeywordsPlugin()
        args, kwargs = plugin.matches(msg)

        conv = suzie.Conversation(plugin, state=kwargs)
        self.assertConversation(
            conv,
            [msg, None])


class TestRouter(unittest.TestCase, CommonAsserts):
    def test_quick_conv(self):
        router = suzie.Router(plugins=[FooBarPlugin()])
        resp = router.handle('set foo as 1 and bar as 2')

        self.assertTrue(isinstance(resp, suzie.ClosingMessage))

    def test_multistep_conv(self):
        router = suzie.Router(plugins=[FooBarPlugin()])

        resp = router.handle('set foo as 1')
        self.assertTrue(isinstance(resp, suzie.InformationRequiredMessage))

        resp = router.handle('set bar as 2')
        self.assertTrue(isinstance(resp, suzie.ClosingMessage))

    def test_triggers_and_keywords(self):
        router = suzie.Router(plugins=[TriggersAndKeywordsPlugin()])

        resp = router.handle('say abc')
        self.assertTrue(isinstance(resp, suzie.ClosingMessage))

    def test_assert(self):
        self.assertConversation(FooBarPlugin(), [
            'set foo as 1', None,
            'set bar as 2', None
        ])

    def test_assert_2(self):
        c = suzie.Conversation(FooBarPlugin())
        self.assertConversation(c, [
            'set foo as 1', None,
        ], final=False)

        self.assertTrue('foo' in c.state)
        self.assertTrue('bar' not in c.state)


if __name__ == '__main__':
    unittest.main()
