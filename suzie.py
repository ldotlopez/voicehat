#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import abc
import enum
import argparse
import collections
import re
import sys


class TextNotMatched(Exception):
    pass


class InternalError(Exception):
    pass


Handler = collections.namedtuple('Handler', [
    'plugin', 'args', 'kwargs'
])


class Conversation:
    def __init__(self, text):
        self._turn = Turn.AGENT
        self._log = [text]
        self._closed = False
        self._plugin = None
        self.data = {}

    @property
    def last(self):
        return self._log[-1]

    @property
    def turn(self):
        return self._turn

    @property
    def closed(self):
        return self._closed

    @property
    def plugin(self):
        return self._plugin

    @plugin.setter
    def plugin(self, plugin):
        if self._plugin is not None:
            raise ValueError(self, "Conversation already associated with a plugin")

        self._plugin = plugin

    def close(self):
        self._closed = True

    def reply(self, text):
        if self.closed:
            raise ValueError(self, 'Conversation is closed')

        if not text:
            raise ValueError(text, "text can't be empty")

        self._log.append(text)
        self._turn = Turn.USER if self._turn == Turn.USER else Turn.AGENT

    def reply_and_close(self, text):
        self.reply(text)
        self.close()

    def dump(self):
        for (idx, text) in enumerate(self._log):
            print("[{dir} {who}] {text}".format(
                dir='>' if not idx % 2 else '<',
                who='User ' if not idx % 2 else 'Agent',
                text=text
                ))


class Turn(enum.Enum):
    USER = 0
    AGENT = 1


class Plugin:
    TRIGGERS = []
    WEIGHT = 0

    def __init__(self):
        self.triggers = [
            re.compile(trigger, re.IGNORECASE)
            for trigger in self.__class__.TRIGGERS]

    def matches(self, text):
        for trigger in self.triggers:
            m = trigger.search(text)
            if not m:
                continue

            args = ()
            kwargs = m.groupdict()
            if not kwargs:
                args = m.groups()

            return args, kwargs

        raise TextNotMatched(text)

    @abc.abstractmethod
    def reply(self, conversation):
        raise NotImplementedError()


class Notes(Plugin):
    class Stage:
        NONE = 0
        ANNOTATING = 1

    NAME = 'notes'
    TRIGGERS = [
        r'^anota$',
        r'^anota (?P<item>.+)$'
    ]

    def reply(self, conv, item=None):
        if item:
            conv.reply_and_close('Got your note: ' + conv.last)
            return

        stage = conv.data.get('stage', self.Stage.NONE)

        if stage == self.Stage.NONE:
            conv.reply('ok, tellme what')
            conv.data['stage'] = self.Stage.ANNOTATING

        elif stage == self.Stage.ANNOTATING:
            conv.reply_and_close('Got your note: ' + conv.last)


class Weather(Plugin):
    NAME = 'weather'
    TRIGGERS = [
        r'^tiempo en (.+)$',
        r'^tiempo$'
    ]

    def reply(self, conversation, *args, **kwargs):
        conversation.reply('To be done :-)')


class Router:
    def __init__(self):
        self.registry = []
        self.plugin = None
        self.conversation = None

    @property
    def prompt(self):
        if self.plugin is None:
            return '> '
        else:
            return '[' + self.plugin.NAME + '] '

    @property
    def in_conversation(self):
        if not self.conversation:
            return False

        return not self.conversation.closed

    def register(self, plugin):
        self.conversation = None
        self.registry.append(plugin)

    def get_handlers(self, text):
        plugins = sorted(self.registry, key=lambda x: x.WEIGHT)

        for plugin in plugins:
            try:
                args, kwargs = plugin.matches(text)
            except TextNotMatched:
                continue

            yield Handler(plugin, args, kwargs)

    def get_handler(self, text):
        try:
            return next(self.get_handlers(text))
        except StopIteration:
            raise TextNotMatched(text)

    def handle(self, text):
        # Sanitize text
        text = re.sub(r'\s+', ' ', text.strip())

        if self.conversation is None:
            # Open a new conversation
            handler = self.get_handler(text)
            args, kwargs = handler.args, handler.kwargs
            self.conversation = Conversation(text)
            self.plugin = handler.plugin

        else:
            # User replied a previous opened conversation
            args, kwargs = (), {}
            self.conversation.reply(text)

        # Try to reply
        try:
            self.plugin.reply(self.conversation, *args, **kwargs)
        except SyntaxError:
            raise

        except Exception as e:
            ret = 'Error in plugin {plugin}: {e!r}'.format(
                plugin=self.plugin.NAME, e=e)
            self.conversation.close()
            self.conversation = None
            self.plugin = None
            return ret

        ret = self.conversation.last

        if self.conversation.closed:
            self.conversation = None
            self.plugin = None

        return ret


def main(args=None):
    if args is None:
        args = sys.argv[:1]

    r = Router()
    r.register(Notes())
    r.register(Weather())

    argparser = argparse.ArgumentParser()
    argparser.add_argument(dest='text', nargs='*')
    args = argparser.parse_args(args)

    text = ' '.join(args.text)
    if not text:
        text = input(r.prompt)

    running = True
    while running:
        if not r.in_conversation and text == 'bye':
            running = False
            continue

        try:
            resp = r.handle(text)
            print(resp)

        except TextNotMatched:
            print("[?] I don't how to handle that")
            continue

        except InternalError as e:
            print("[!] Internal error: {e!r}".format(e=e.args[0]))
            continue

        finally:
            text = input(r.prompt)


if __name__ == '__main__':
    main(sys.argv[1:])
