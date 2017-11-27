#!/usr/bin/env python3
# -*- encoding: utf-8 -*-


import enum
import collections
import re


class TextNotMatched(Exception):
    pass


class InternalError(Exception):
    pass


Handler = collections.namedtuple('Handler', [
    'plugin', 'args', 'kwargs'
])


class Store(dict):
    def set(self, key, value):
        self[key] = value

    def delete(self, key):
        del(self[key])


class Conversation:
    def __init__(self, text):
        self._turn = Turn.AGENT
        self._log = [text]
        self._closed = False
        self._plugin = None
        self.data = Store()

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
            msg = "Conversation already associated with a plugin"
            raise ValueError(self, msg)

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
        except StopIteration as e:
            raise TextNotMatched(text) from e

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
