#!/usr/bin/env python3
# -*- encoding: utf-8 -*-


import enum
import collections
import re


class Router:
    def __init__(self):
        self.registry = []
        self.plugin = None
        self.conversation = None

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
        message = UserMessage(text)

        # Create a new conversation or update the opened one
        if self.conversation is None:
            handler = self.get_handler(text)
            args, kwargs = handler.args, handler.kwargs

            self.conversation = Conversation(message)
            self.plugin = handler.plugin

        else:
            args, kwargs = (), {}

            self.conversation.reply(message)

        # Try to reply with active plugin
        try:
            response = self.plugin.reply(
                self.conversation.last, self.conversation.data,
                *args, **kwargs)

        except SyntaxError:
            raise

        except Exception as e:
            ret = 'Error in plugin {plugin}: {e!r}'.format(
                plugin=self.plugin.NAME, e=e)
            self.conversation.close()
            self.conversation = None
            self.plugin = None
            return ret

        # Add agent response to conversation
        self.conversation.reply(response)

        if self.conversation.closed:
            self.conversation = None
            self.plugin = None

        return response


Handler = collections.namedtuple('Handler', [
    'plugin', 'args', 'kwargs'
])


class Conversation:
    def __init__(self, message):
        if not isinstance(message, UserMessage):
            msg = "Only user can start conversations"
            raise ValueError(message, msg)

        self._log = [message]
        self._turn = Turn.AGENT
        self._closed = False
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

    def close(self):
        self._closed = True

    def reply(self, message):
        if self.closed:
            raise ValueError(self, 'Conversation is closed')

        if not isinstance(message, Message):
            raise TypeError(message)

        if not message:
            raise ValueError(message, "response can't be empty")

        if self._turn == Turn.USER and not isinstance(message, UserMessage):
            raise TypeError('Was user turn')

        if self._turn == Turn.AGENT and not isinstance(message, AgentMessage):
            raise TypeError('Was agent turn')

        self._log.append(message)
        self._turn = Turn.AGENT if self._turn == Turn.USER else Turn.USER

        if isinstance(message, FinalMessage):
            self.close()

    def dump(self):
        for (idx, message) in enumerate(self._log):
            print("[{dir} {who}] {msg}".format(
                dir='>' if not idx % 2 else '<',
                who='User ' if not idx % 2 else 'Agent',
                msg=message
                ))


class Turn(enum.Enum):
    USER = 0
    AGENT = 1


class Store(dict):
    def set(self, key, value):
        self[key] = value

    def delete(self, key):
        del(self[key])


class Message(str):
    pass


class UserMessage(Message):
    pass


class AgentMessage(Message):
    pass


class FinalMessage(AgentMessage):
    pass


class TextNotMatched(Exception):
    pass


class InternalError(Exception):
    pass
