import unittest
import re

import suzie
import suzie.plugins


class SingleSlotPlugin(suzie.Plugin):
    TRIGGERS = [
        r'test with x as (\S+)',  # For quick execution
        r'test',                  # Generic trigger
    ]

    STATE_SLOTS = [
        'x'
    ]

    def extract(self, text):
        ret = {}

        m = re.search(r'\bset x as (\S+)\b', text)
        if m:
            ret['x'] = m.group(1)

        return ret

    def main(self, x):
        msg = "Got x={}".format(x)
        return suzie.ClosingMessage(msg)


class MultipleSlotPlugin(suzie.Plugin):
    TRIGGERS = [
        r'test with x as (?P<x>\S+)( and y as (?P<y>\S+))?',
        r'test with y as (?P<y>\S+)( and x as (?P<x>\S+))?',
        r'test'  # Generic trigger
    ]

    STATE_SLOTS = [
        'x',
        'y'
    ]

    def extract(self, text):
        ret = {}

        m = re.search(r'\bset x as (\S+)\b', text)
        if m:
            ret['x'] = m.group(1)

        m = re.search(r'\bset y as (\S+)\b', text)
        if m:
            ret['y'] = m.group(1)

        # Strip Nones
        ret = {k: v for (k, v) in ret.items() if v}
        return ret

    def main(self, x, y):
        msg = "Got x={!r}, y={!r}".format(x, y)
        return suzie.ClosingMessage(msg)


class EchoPlugin(suzie.Plugin):
    TRIGGERS = [
        'echo',
        'echo (?P<what>)'
    ]
    STATE_SLOTS = [
        'what'
    ]

    def extract(self, text):
        if text:
            return {'what': ''.join(reversed(text))}

    def main(self, what):
        return suzie.ClosingMessage(what)


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
                    isinstance(reply, suzie.RequestMessage))

            if agent:
                self.assertEqual(str(reply), agent)

        if final:
            self.assertTrue(
                isinstance(reply, suzie.ClosingMessage))
        else:
            self.assertTrue(
                isinstance(reply, suzie.RequestMessage))


class TestPlugin(unittest.TestCase):
    def test_full_predicate(self):
        plugin = MultipleSlotPlugin()
        reply = plugin.handle('set x as 1 and set y as 2', {})
        self.assertTrue(isinstance(reply, suzie.ClosingMessage))

    def test_partial_predicate(self):
        plugin = MultipleSlotPlugin()
        state = {}

        reply = plugin.handle('set x as 1', state)
        self.assertTrue(isinstance(reply, suzie.RequestMessage))
        self.assertEqual(reply.what, 'y')
        self.assertEqual(state, {'x': '1'})

    def test_multistep_predicate(self):
        plugin = MultipleSlotPlugin()
        state = {}

        reply = plugin.handle('set x as 1', state)
        self.assertTrue(isinstance(reply, suzie.RequestMessage))
        self.assertEqual(reply.what, 'y')
        self.assertEqual(state, {'x': '1'})

        reply = plugin.handle('set y as 2', state)
        self.assertTrue(isinstance(reply, suzie.ClosingMessage))
        self.assertEqual(state, {'x': '1', 'y': '2'})


class TestConversation(unittest.TestCase, CommonAsserts):
    def test_single_slot(self):
        conv = suzie.Conversation(SingleSlotPlugin())
        resp = conv.handle('set x as 1')
        self.assertTrue(isinstance(resp, suzie.ClosingMessage))

    def test_multiple_slot(self):
        self.assertConversation(
            MultipleSlotPlugin(),
            ['set x as 1', None,
             'set y as 2', None]
        )


class TestRouter(unittest.TestCase, CommonAsserts):
    def test_no_initial_state(self):
        router = suzie.Router(plugins=[MultipleSlotPlugin()])

        resp = router.handle('test')
        self.assertTrue(isinstance(resp, suzie.RequestMessage))

        resp = router.handle('set x as 1')
        self.assertTrue(isinstance(resp, suzie.RequestMessage))

        resp = router.handle('set y as 2')
        self.assertTrue(isinstance(resp, suzie.ClosingMessage))

    def test_quick_dialog(self):
        router = suzie.Router(plugins=[MultipleSlotPlugin()])

        resp = router.handle('test with x as 1 and y as 2')
        self.assertTrue(isinstance(resp, suzie.ClosingMessage))

    def test_echo(self):
        router = suzie.Router(plugins=[EchoPlugin()])

        resp = router.handle('echo')
        self.assertTrue(isinstance(resp, suzie.RequestMessage))

        resp = router.handle('123')
        self.assertTrue(isinstance(resp, suzie.ClosingMessage))
        self.assertTrue(str(resp), '321')

    # Partial dialog is not well supported
    # def test_partial_dialog(self):
    #     router = suzie.Router(plugins=[MultipleSlotPlugin()])

    #     resp = router.handle('test with y as 2')
    #     self.assertTrue(isinstance(resp, suzie.RequestMessage))

    #     resp = router.handle('set x as 1')
    #     self.assertTrue(isinstance(resp, suzie.ClosingMessage))


if __name__ == '__main__':
    unittest.main()
